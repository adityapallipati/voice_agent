import logging
import os
import json
from typing import Dict, Any, List, Optional
import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis

from app.db.models import KnowledgeItem
from app.db.session import async_session
from app.core.config import settings
from app.core.llm import LLMProcessor

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """
    Service for managing and querying knowledge base.
    """
    def __init__(self):
        self.knowledge_dir = settings.KNOWLEDGE_BASE_DIR
        self.redis = redis.from_url(settings.REDIS_URL)
        self.cache_ttl = 3600  # 1 hour
        self.llm_processor = LLMProcessor()
    
    async def query(self, question: str, max_results: int = 3) -> Optional[str]:
        """
        Query the knowledge base for relevant information.
        
        For MVP, this implements a simple keyword-based search.
        In production, this should be replaced with a vector-based semantic search.
        """
        # Get all knowledge items
        items = await self._get_all_knowledge_items()
        
        if not items:
            return None
        
        # Simple ranking based on keyword matching (replace with vector search in production)
        ranked_items = []
        question_keywords = self._extract_keywords(question.lower())
        
        for item in items:
            item_text = f"{item.get('title', '')} {item.get('content', '')}"
            item_keywords = self._extract_keywords(item_text.lower())
            
            # Calculate simple overlap score
            overlap = len(set(question_keywords) & set(item_keywords))
            if overlap > 0:
                ranked_items.append((item, overlap))
        
        # Sort by score
        ranked_items.sort(key=lambda x: x[1], reverse=True)
        
        # Take top results
        top_items = [item for item, _ in ranked_items[:max_results]]
        
        if not top_items:
            return None
        
        # Format top results for context
        context = "\n\n".join([
            f"Title: {item.get('title')}\n{item.get('content')}"
            for item in top_items
        ])
        
        # Use LLM to synthesize an answer
        prompt_template = """
        You are a helpful assistant for a business. Answer the customer's question using the provided knowledge base information.
        If the information is not sufficient to answer the question, politely say you don't have enough information.
        
        Customer Question:
        {question}
        
        Knowledge Base Information:
        {context}
        
        Provide a concise, helpful response in a conversational tone.
        """
        
        response = await self.llm_processor.process(
            prompt_template,
            {"question": question, "context": context},
            extract_json=False
        )
        
        return response.get("text")
    
    async def add_item(
        self, 
        title: str, 
        content: str, 
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add a new knowledge item.
        """
        async with async_session() as db:
            # Create new item
            knowledge_item = KnowledgeItem(
                title=title,
                content=content,
                category=category,
                tags=tags or [],
                version=1,
                is_active=True
            )
            
            db.add(knowledge_item)
            await db.commit()
            await db.refresh(knowledge_item)
            
            # Ensure directory exists
            os.makedirs(self.knowledge_dir, exist_ok=True)
            
            # Write to file as backup
            file_path = os.path.join(self.knowledge_dir, f"{knowledge_item.id}.json")
            data = {
                "id": knowledge_item.id,
                "title": title,
                "content": content,
                "category": category,
                "tags": tags or [],
                "version": 1
            }
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))
            
            return {
                "id": knowledge_item.id,
                "title": knowledge_item.title,
                "category": knowledge_item.category,
                "created_at": knowledge_item.created_at.isoformat()
            }
    
    async def update_item(
        self, 
        item_id: str, 
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing knowledge item.
        """
        async with async_session() as db:
            # Get existing item
            result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
            item = result.scalars().first()
            
            if not item:
                raise ValueError(f"Knowledge item not found: {item_id}")
            
            # Update fields
            if title:
                item.title = title
            if content:
                item.content = content
            if category:
                item.category = category
            if tags is not None:
                item.tags = tags
            
            item.version += 1
            
            await db.commit()
            
            # Update file backup
            file_path = os.path.join(self.knowledge_dir, f"{item_id}.json")
            data = {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "tags": item.tags,
                "version": item.version
            }
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))
            
            return {
                "id": item.id,
                "title": item.title,
                "version": item.version,
                "updated_at": item.updated_at.isoformat()
            }
    
    async def delete_item(self, item_id: str) -> Dict[str, Any]:
        """
        Delete a knowledge item.
        """
        async with async_session() as db:
            # Get existing item
            result = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
            item = result.scalars().first()
            
            if not item:
                raise ValueError(f"Knowledge item not found: {item_id}")
            
            # Soft delete by marking inactive
            item.is_active = False
            await db.commit()
            
            return {
                "id": item_id,
                "status": "deleted"
            }
    
    async def _get_all_knowledge_items(self) -> List[Dict[str, Any]]:
        """
        Get all active knowledge items.
        """
        cache_key = "knowledge:all"
        cached_items = self.redis.get(cache_key)
        
        if cached_items:
            try:
                return json.loads(cached_items)
            except json.JSONDecodeError:
                pass
        
        items = []
        
        # Try to get from database
        async with async_session() as db:
            try:
                result = await db.execute(
                    select(KnowledgeItem)
                    .where(KnowledgeItem.is_active == True)
                )
                db_items = result.scalars().all()
                
                items = [
                    {
                        "id": item.id,
                        "title": item.title,
                        "content": item.content,
                        "category": item.category,
                        "tags": item.tags,
                        "version": item.version
                    }
                    for item in db_items
                ]
                
                # Cache results
                self.redis.setex(cache_key, self.cache_ttl, json.dumps(items))
                
                return items
            except Exception as e:
                logger.warning(f"Error fetching knowledge items from database: {e}")
        
        # Fallback to filesystem
        try:
            if os.path.exists(self.knowledge_dir):
                file_items = []
                for filename in os.listdir(self.knowledge_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(self.knowledge_dir, filename)
                        async with aiofiles.open(file_path, 'r') as f:
                            content = await f.read()
                            try:
                                item_data = json.loads(content)
                                file_items.append(item_data)
                            except json.JSONDecodeError:
                                pass
                
                # Cache results
                if file_items:
                    self.redis.setex(cache_key, self.cache_ttl, json.dumps(file_items))
                
                return file_items
        except Exception as e:
            logger.error(f"Error reading knowledge files: {e}")
        
        return items
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text.
        
        Simple implementation - in production use NLP for better keyword extraction.
        """
        # Remove punctuation and split by whitespace
        import re
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Remove stop words (very minimal list for MVP)
        stop_words = {'the', 'and', 'is', 'in', 'to', 'a', 'of', 'for', 'with', 'on', 'at'}
        keywords = [word for word in words if word.lower() not in stop_words and len(word) > 1]
        
        return keywords