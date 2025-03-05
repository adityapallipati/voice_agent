import logging
import os
import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json
import redis
from app.db.models import PromptTemplate
from app.db.session import async_session
from app.core.config import settings

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Service for managing and retrieving prompt templates.
    """
    def __init__(self):
        self.prompt_dir = settings.PROMPT_TEMPLATES_DIR
        self.redis = redis.from_url(settings.REDIS_URL)
        self.cache_ttl = 3600  # 1 hour
    
    async def get_prompt(self, name: str) -> str:
        """
        Get a prompt template by name.
        
        First checks Redis cache, then database, then fallback to filesystem.
        """
        # Check Redis cache first
        cache_key = f"prompt:{name}"
        cached_prompt = self.redis.get(cache_key)
        
        if cached_prompt:
            return cached_prompt.decode('utf-8')
        
        # Check database
        async with async_session() as db:
            try:
                prompt = await self._get_prompt_from_db(db, name)
                if prompt:
                    # Update cache
                    self.redis.setex(cache_key, self.cache_ttl, prompt)
                    return prompt
            except Exception as e:
                logger.warning(f"Error fetching prompt from database: {e}")
        
        # Fallback to filesystem
        prompt = await self._get_prompt_from_file(name)
        if prompt:
            # Update cache
            self.redis.setex(cache_key, self.cache_ttl, prompt)
            return prompt
        
        raise ValueError(f"Prompt template not found: {name}")
    
    async def create_prompt(self, name: str, content: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new prompt template.
        """
        async with async_session() as db:
            # Check if prompt already exists
            result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == name))
            existing = result.scalars().first()
            
            if existing:
                raise ValueError(f"Prompt template already exists: {name}")
            
            # Create new prompt
            prompt = PromptTemplate(
                name=name,
                content=content,
                description=description,
                version=1,
                is_active=True
            )
            
            db.add(prompt)
            await db.commit()
            await db.refresh(prompt)
            
            # Update cache
            cache_key = f"prompt:{name}"
            self.redis.setex(cache_key, self.cache_ttl, content)
            
            # Ensure directory exists
            os.makedirs(self.prompt_dir, exist_ok=True)
            
            # Write to file as backup
            file_path = os.path.join(self.prompt_dir, f"{name}.txt")
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)
            
            return {
                "id": prompt.id,
                "name": prompt.name,
                "version": prompt.version,
                "created_at": prompt.created_at.isoformat()
            }
    
    async def update_prompt(self, name: str, content: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing prompt template.
        """
        async with async_session() as db:
            # Get existing prompt
            result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == name))
            prompt = result.scalars().first()
            
            if not prompt:
                raise ValueError(f"Prompt template not found: {name}")
            
            # Update prompt
            prompt.content = content
            if description:
                prompt.description = description
            prompt.version += 1
            
            await db.commit()
            
            # Update cache
            cache_key = f"prompt:{name}"
            self.redis.setex(cache_key, self.cache_ttl, content)
            
            # Update file backup
            file_path = os.path.join(self.prompt_dir, f"{name}.txt")
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)
            
            return {
                "id": prompt.id,
                "name": prompt.name,
                "version": prompt.version,
                "updated_at": prompt.updated_at.isoformat()
            }
    
    async def delete_prompt(self, name: str) -> Dict[str, Any]:
        """
        Delete a prompt template.
        """
        async with async_session() as db:
            # Get existing prompt
            result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == name))
            prompt = result.scalars().first()
            
            if not prompt:
                raise ValueError(f"Prompt template not found: {name}")
            
            # Soft delete by marking inactive
            prompt.is_active = False
            await db.commit()
            
            # Remove from cache
            cache_key = f"prompt:{name}"
            self.redis.delete(cache_key)
            
            return {
                "name": name,
                "status": "deleted"
            }
    
    async def _get_prompt_from_db(self, db: AsyncSession, name: str) -> Optional[str]:
        """
        Get prompt from database.
        """
        result = await db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name)
            .where(PromptTemplate.is_active == True)
        )
        prompt = result.scalars().first()
        
        if prompt:
            return prompt.content
        
        return None
    
    async def _get_prompt_from_file(self, name: str) -> Optional[str]:
        """
        Get prompt from filesystem.
        """
        file_path = os.path.join(self.prompt_dir, f"{name}.txt")
        
        if os.path.exists(file_path):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    return await f.read()
            except Exception as e:
                logger.error(f"Error reading prompt file {file_path}: {e}")
        
        return None