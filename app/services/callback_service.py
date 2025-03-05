import logging
from sqlalchemy import select, update, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from app.db.models import Callback, Customer, Call
from app.models.callbacks import CallbackCreate, CallbackUpdate
from app.core.crm import get_crm_client
from app.core.llm import LLMProcessor
from app.core.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class CallbackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.crm_client = get_crm_client()
        self.llm_processor = LLMProcessor()
        self.prompt_manager = PromptManager()
    
    async def create_callback(self, callback_data: CallbackCreate) -> Dict[str, Any]:
        """
        Create a new callback.
        """
        logger.info(f"Creating callback for customer {callback_data.customer_id}")
        
        # Validate customer exists
        customer_exists = await self._check_customer_exists(callback_data.customer_id)
        if not customer_exists:
            logger.error(f"Customer {callback_data.customer_id} not found")
            raise ValueError(f"Customer {callback_data.customer_id} not found")
        
        # Generate call script if not provided
        call_script = callback_data.call_script
        if not call_script:
            call_script = await self.generate_script_for_purpose(
                callback_data.customer_id,
                callback_data.purpose
            )
        
        # Create callback in database
        callback = Callback(
            id=str(uuid.uuid4()),
            customer_id=callback_data.customer_id,
            phone_number=callback_data.phone_number,
            callback_time=callback_data.callback_time,
            purpose=callback_data.purpose,
            call_script=call_script,
            status="scheduled",
            metadata=callback_data.metadata or {}
        )
        
        self.db.add(callback)
        await self.db.commit()
        await self.db.refresh(callback)
        
        # Create activity in CRM
        try:
            # Get customer info for the script
            customer_result = await self.db.execute(select(Customer).where(Customer.id == callback_data.customer_id))
            customer = customer_result.scalars().first()
            customer_name = customer.name if customer else "Customer"
            
            await self.crm_client.create_activity({
                "customer_id": callback_data.customer_id,
                "subject": f"Scheduled Callback: {callback_data.purpose}",
                "description": f"Callback scheduled for {callback_data.callback_time.isoformat()} regarding {callback_data.purpose}",
                "type": "Scheduled Call",
                "timestamp": datetime.now().timestamp() * 1000,
                "due_date": callback_data.callback_time.timestamp() * 1000
            })
        
        except Exception as e:
            logger.error(f"Error creating activity in CRM: {e}")
            # We continue even if CRM integration fails
        
        return self._callback_to_dict(callback)
    
    async def get_callback(self, callback_id: str) -> Optional[Dict[str, Any]]:
        """
        Get callback details by ID.
        """
        result = await self.db.execute(select(Callback).where(Callback.id == callback_id))
        callback = result.scalars().first()
        
        if not callback:
            return None
        
        return self._callback_to_dict(callback)
    
    async def list_callbacks(
        self, 
        skip: int = 0, 
        limit: int = 100,
        customer_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List callbacks with filtering options.
        """
        query = select(Callback).offset(skip).limit(limit)
        
        # Apply filters
        if customer_id:
            query = query.where(Callback.customer_id == customer_id)
        
        if status:
            query = query.where(Callback.status == status)
        
        # Order by callback time
        query = query.order_by(Callback.callback_time)
        
        result = await self.db.execute(query)
        callbacks = result.scalars().all()
        
        return [self._callback_to_dict(callback) for callback in callbacks]
    
    async def get_pending_callbacks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending callbacks that need to be executed.
        Used by N8N to fetch callbacks that should be processed.
        """
        now = datetime.now()
        
        # Find callbacks that are scheduled and due
        query = select(Callback).where(
            and_(
                Callback.status == "scheduled",
                Callback.callback_time <= now
            )
        ).order_by(Callback.callback_time).limit(limit)
        
        result = await self.db.execute(query)
        callbacks = result.scalars().all()
        
        # For each callback, get customer details
        enriched_callbacks = []
        for callback in callbacks:
            callback_dict = self._callback_to_dict(callback)
            
            # Get customer info
            customer_result = await self.db.execute(select(Customer).where(Customer.id == callback.customer_id))
            customer = customer_result.scalars().first()
            
            if customer:
                callback_dict["customer_name"] = customer.name
                callback_dict["customer_email"] = customer.email
            
            enriched_callbacks.append(callback_dict)
        
        return enriched_callbacks
    
    async def update_callback(self, callback_id: str, callback_data: CallbackUpdate) -> Optional[Dict[str, Any]]:
        """
        Update an existing callback.
        """
        # Get callback
        result = await self.db.execute(select(Callback).where(Callback.id == callback_id))
        callback = result.scalars().first()
        
        if not callback:
            logger.warning(f"Callback {callback_id} not found for update")
            return None
        
        # Update callback fields
        if callback_data.phone_number is not None:
            callback.phone_number = callback_data.phone_number
        
        if callback_data.callback_time is not None:
            callback.callback_time = callback_data.callback_time
        
        if callback_data.purpose is not None:
            callback.purpose = callback_data.purpose
        
        if callback_data.call_script is not None:
            callback.call_script = callback_data.call_script
        
        if callback_data.status is not None:
            callback.status = callback_data.status
        
        if callback_data.metadata is not None:
            callback.metadata = callback_data.metadata
        
        await self.db.commit()
        await self.db.refresh(callback)
        
        # Update activity in CRM
        try:
            # If we have a CRM activity ID, update it
            crm_activity_id = callback.metadata.get("crm_activity_id") if callback.metadata else None
            
            if crm_activity_id:
                await self.crm_client.update_activity(crm_activity_id, {
                    "description": f"Callback {callback.status} for {callback.callback_time.isoformat()} regarding {callback.purpose}",
                    "due_date": callback.callback_time.timestamp() * 1000
                })
        except Exception as e:
            logger.error(f"Error updating activity in CRM: {e}")
            # We continue even if CRM integration fails
        
        logger.info(f"Callback {callback_id} updated")
        return self._callback_to_dict(callback)
    
    async def update_callback_status(
        self, 
        callback_id: str, 
        status: str,
        call_id: Optional[str] = None
    ) -> None:
        """
        Update the status of a callback.
        """
        # Validate status
        valid_statuses = ["scheduled", "in_progress", "completed", "failed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        # Get callback
        result = await self.db.execute(select(Callback).where(Callback.id == callback_id))
        callback = result.scalars().first()
        
        if not callback:
            raise ValueError(f"Callback {callback_id} not found")
        
        # Update status
        callback.status = status
        
        # If call_id is provided, link it
        if call_id:
            callback.call_id = call_id
            
            # Get call info from database if possible
            call_result = await self.db.execute(select(Call).where(Call.call_id == call_id))
            call = call_result.scalars().first()
            
            if call and call.outcome:
                callback.result = call.outcome
        
        # Add status change to metadata
        if not callback.metadata:
            callback.metadata = {}
        
        if not callback.metadata.get("status_history"):
            callback.metadata["status_history"] = []
        
        callback.metadata["status_history"].append({
            "old_status": callback.status,
            "new_status": status,
            "timestamp": datetime.now().isoformat(),
            "call_id": call_id
        })
        
        await self.db.commit()
        
        # Update activity in CRM
        try:
            # If we have a CRM activity ID, update it
            crm_activity_id = callback.metadata.get("crm_activity_id") if callback.metadata else None
            
            if crm_activity_id:
                crm_status = "Completed" if status in ["completed", "failed"] else "In Progress"
                
                await self.crm_client.update_activity(crm_activity_id, {
                    "status": crm_status,
                    "description": f"Callback {status} for {callback.callback_time.isoformat()} regarding {callback.purpose}"
                })
        except Exception as e:
            logger.error(f"Error updating activity in CRM: {e}")
            # We continue even if CRM integration fails
        
        logger.info(f"Callback {callback_id} status updated to {status}")
    
    async def cancel_callback(self, callback_id: str) -> None:
        """
        Cancel a scheduled callback.
        """
        # Get callback
        result = await self.db.execute(select(Callback).where(Callback.id == callback_id))
        callback = result.scalars().first()
        
        if not callback:
            raise ValueError(f"Callback {callback_id} not found")
        
        # Update status to cancelled
        callback.status = "cancelled"
        
        # Add cancellation info to metadata
        if not callback.metadata:
            callback.metadata = {}
        
        callback.metadata["cancellation"] = {
            "timestamp": datetime.now().isoformat()
        }
        
        await self.db.commit()
        
        # Update activity in CRM
        try:
            # If we have a CRM activity ID, update it
            crm_activity_id = callback.metadata.get("crm_activity_id") if callback.metadata else None
            
            if crm_activity_id:
                await self.crm_client.update_activity(crm_activity_id, {
                    "status": "Cancelled",
                    "description": f"Callback cancelled for {callback.callback_time.isoformat()} regarding {callback.purpose}"
                })
        except Exception as e:
            logger.error(f"Error updating activity in CRM: {e}")
            # We continue even if CRM integration fails
        
        logger.info(f"Callback {callback_id} cancelled")
    
    async def create_batch_callbacks(self, callbacks: List[CallbackCreate]) -> List[Dict[str, Any]]:
        """
        Create multiple callbacks at once.
        """
        results = []
        
        for callback_data in callbacks:
            try:
                result = await self.create_callback(callback_data)
                results.append({"success": True, "data": result})
            except Exception as e:
                logger.error(f"Error creating callback: {e}")
                results.append({"success": False, "error": str(e)})
        
        return results
    
    async def generate_callback_script(self, callback_id: str) -> str:
        """
        Generate a call script for an existing callback.
        """
        # Get callback
        result = await self.db.execute(select(Callback).where(Callback.id == callback_id))
        callback = result.scalars().first()
        
        if not callback:
            raise ValueError(f"Callback {callback_id} not found")
        
        # Generate script
        script = await self.generate_script_for_purpose(
            callback.customer_id,
            callback.purpose
        )
        
        # Update callback with new script
        callback.call_script = script
        await self.db.commit()
        
        return script
    
    async def generate_script_for_purpose(self, customer_id: str, purpose: str) -> str:
        """
        Generate a call script based on purpose and customer information.
        """
        # Get customer info
        customer_result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = customer_result.scalars().first()
        
        customer_name = customer.name if customer else "valued customer"
        
        # Get the callback script template
        try:
            template = await self.prompt_manager.get_prompt("generate_callback_script")
        except Exception as e:
            logger.error(f"Error getting callback script template: {e}")
            template = """
            Generate a natural and conversational script for an outbound call to a customer.
            This script will be used by an AI voice agent to make the call.
            
            Customer name: {customer_name}
            Purpose of call: {purpose}
            
            The script should:
            1. Introduce the AI as a virtual assistant from the business
            2. Clearly state the purpose of the call
            3. Be conversational and natural
            4. Include appropriate pauses for customer responses
            5. Include handling for common responses
            6. Have a clear call-to-action
            7. End professionally
            
            Write a complete script that the AI can follow for the call.
            """
        
        # Generate script with LLM
        try:
            response = await self.llm_processor.process(
                template,
                {
                    "customer_name": customer_name,
                    "purpose": purpose
                },
                extract_json=False
            )
            
            script = response.get("text", "")
            
            if not script:
                # Fallback to default script
                script = self._generate_default_script(customer_name, purpose)
            
            return script
            
        except Exception as e:
            logger.error(f"Error generating callback script: {e}")
            return self._generate_default_script(customer_name, purpose)
    
    def _generate_default_script(self, customer_name: str, purpose: str) -> str:
        """
        Generate a default script if LLM processing fails.
        """
        return f"""
        Hello, this is the AI assistant from [Your Business]. Am I speaking with {customer_name}?
        
        Great! I'm calling regarding {purpose}. 
        
        [Wait for customer response]
        
        Thank you for your time. Is there anything else I can help you with today?
        
        [Wait for customer response]
        
        Thank you for your time. Have a great day!
        """
    
    async def _check_customer_exists(self, customer_id: str) -> bool:
        """
        Check if a customer exists.
        """
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        return result.scalars().first() is not None
    
    def _callback_to_dict(self, callback: Callback) -> Dict[str, Any]:
        """
        Convert Callback model to dictionary.
        """
        return {
            "id": callback.id,
            "customer_id": callback.customer_id,
            "phone_number": callback.phone_number,
            "callback_time": callback.callback_time,
            "purpose": callback.purpose,
            "call_script": callback.call_script,
            "status": callback.status,
            "result": callback.result,
            "call_id": callback.call_id,
            "metadata": callback.metadata,
            "created_at": callback.created_at,
            "updated_at": callback.updated_at
        }