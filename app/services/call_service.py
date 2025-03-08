import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.db.models import Call, Customer
from app.models.calls import ProcessCallRequest
from app.core.vapi import VAPIClient
from app.core.llm import LLMProcessor
from app.core.prompt_manager import PromptManager
from app.core.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

class CallService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vapi_client = VAPIClient()
        self.llm_processor = LLMProcessor()
        self.prompt_manager = PromptManager()
        self.knowledge_base = KnowledgeBase()
    
    async def process_call(self, request: ProcessCallRequest) -> Dict[str, Any]:
        """
        Process an incoming call.
        Main business logic for handling calls.
        """
        logger.info(f"Processing call {request.call_id}")
        
        # Get or create customer
        customer = await self._get_or_create_customer(request.customer_id, request.phone_number)
        
        # Determine intent using LLM
        prompt_template = await self.prompt_manager.get_prompt("intent_classification")
        intent_response = await self.llm_processor.process(
            prompt_template,
            {"transcript": request.transcript}
        )
        
        # Parse intent
        intent = intent_response.get("intent", "unknown")
        logger.info(f"Detected intent: {intent}")
        
        # Process based on intent
        response_text = ""
        if intent == "book_appointment":
            appointment_response = await self._process_booking(request.transcript)
            response_text = appointment_response.get("response", "")
        elif intent == "reschedule":
            reschedule_response = await self._process_reschedule(request.transcript)
            response_text = reschedule_response.get("response", "")
        elif intent == "cancel":
            cancel_response = await self._process_cancellation(request.transcript)
            response_text = cancel_response.get("response", "")
        elif intent == "general_question":
            kb_response = await self.knowledge_base.query(request.transcript)
            response_text = kb_response or "I don't have that information. Would you like me to connect you with someone who can help?"
        elif intent == "human_agent":
            response_text = "I'll connect you with a customer service representative right away."
        elif intent == "callback":
            callback_response = await self._process_callback_request(request.transcript)
            response_text = callback_response.get("response", "")
        else:
            response_text = "I'm not sure I understood. Could you please rephrase your request?"
        
        # Generate response based on intent
        response_data = {
            "intent": intent,
            "kb_response": response_text if intent == "general_question" else None,
            "call_id": request.call_id,
            "customer_id": customer.id,
            "response": response_text
        }
        
        return response_data
    
    async def _process_booking(self, transcript: str) -> Dict[str, Any]:
        """Process an appointment booking request."""
        try:
            # Get the appointment details extraction template
            prompt_template = await self.prompt_manager.get_prompt("extract_appointment_details")
            
            # Extract appointment details
            details_response = await self.llm_processor.process(
                prompt_template,
                {"transcript": transcript}
            )
            
            # Construct a natural language response
            service_type = details_response.get("service_type", "appointment")
            appointment_time = details_response.get("appointment_time", "your requested time")
            
            # Format the response
            response = f"I'd be happy to book your {service_type} for {appointment_time}. "
            
            # Add customer name if available
            if details_response.get("customer_name"):
                response += f"I have you down as {details_response.get('customer_name')}. "
                
            response += "Is that correct?"
            
            return {
                "details": details_response,
                "response": response
            }
        except Exception as e:
            logger.error(f"Error processing booking: {e}")
            return {
                "details": {},
                "response": "I'm having trouble booking your appointment. Could you please try again with the date and time you'd like?"
            }
    
    async def _process_reschedule(self, transcript: str) -> Dict[str, Any]:
        """Process an appointment rescheduling request."""
        try:
            # Get the reschedule details extraction template
            prompt_template = await self.prompt_manager.get_prompt("extract_reschedule_details")
            
            # Extract reschedule details
            details_response = await self.llm_processor.process(
                prompt_template,
                {"transcript": transcript}
            )
            
            # Construct a natural language response
            old_time = details_response.get("old_time", "your current appointment")
            new_time = details_response.get("new_time", "the requested time")
            
            # Format the response
            response = f"I'll reschedule your appointment from {old_time} to {new_time}. "
            response += "Is that correct?"
            
            return {
                "details": details_response,
                "response": response
            }
        except Exception as e:
            logger.error(f"Error processing reschedule: {e}")
            return {
                "details": {},
                "response": "I'm having trouble rescheduling your appointment. Could you please confirm the current appointment time and your preferred new time?"
            }
    
    async def _process_cancellation(self, transcript: str) -> Dict[str, Any]:
        """Process an appointment cancellation request."""
        try:
            # Get the cancellation details extraction template
            prompt_template = await self.prompt_manager.get_prompt("extract_cancellation_details")
            
            # Extract cancellation details
            details_response = await self.llm_processor.process(
                prompt_template,
                {"transcript": transcript}
            )
            
            # Construct a natural language response
            appointment_time = details_response.get("appointment_time", "your appointment")
            reschedule_later = details_response.get("reschedule_later", False)
            
            # Format the response
            response = f"I've cancelled {appointment_time}. "
            
            if reschedule_later:
                response += "Would you like to reschedule for another time?"
            else:
                response += "Is there anything else I can help you with today?"
            
            return {
                "details": details_response,
                "response": response
            }
        except Exception as e:
            logger.error(f"Error processing cancellation: {e}")
            return {
                "details": {},
                "response": "I'm having trouble cancelling your appointment. Could you please confirm which appointment you'd like to cancel?"
            }
    
    async def _process_callback_request(self, transcript: str) -> Dict[str, Any]:
        """Process a callback request."""
        try:
            # Extract callback details using Claude
            # For simplicity, we'll just respond directly
            response = "I'll make sure someone calls you back. What's the best time to reach you?"
            
            return {
                "response": response
            }
        except Exception as e:
            logger.error(f"Error processing callback request: {e}")
            return {
                "response": "I'll arrange for someone to call you back. Is there a specific time that works best for you?"
            }
    
    async def log_call(self, call_id: str, result: Dict[str, Any]) -> None:
        """
        Log call information to database.
        """
        try:
            # Get call info from VAPI
            call_info = await self.vapi_client.get_call(call_id)
            
            call = Call(
                call_id=call_id,
                customer_id=result.get("customer_id"),
                direction=call_info.get("direction", "inbound"),
                status=call_info.get("status", "completed"),
                start_time=datetime.fromisoformat(call_info.get("start_time", datetime.now().isoformat())),
                end_time=datetime.fromisoformat(call_info.get("end_time", datetime.now().isoformat())) 
                    if call_info.get("end_time") else None,
                duration=call_info.get("duration"),
                from_number=call_info.get("from"),
                to_number=call_info.get("to"),
                transcript=call_info.get("transcript"),
                recording_url=call_info.get("recording_url"),
                intent=result.get("intent"),
                outcome=result.get("outcome"),
                metadata=call_info.get("metadata")
            )
            
            self.db.add(call)
            await self.db.commit()
            logger.info(f"Call {call_id} logged successfully")
        except Exception as e:
            logger.error(f"Error logging call {call_id}: {e}")
            await self.db.rollback()
    
    async def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Get call details by call ID.
        """
        result = await self.db.execute(select(Call).where(Call.call_id == call_id))
        call = result.scalars().first()
        
        if not call:
            return None
        
        return self._call_to_dict(call)
    
    async def list_calls(
        self, 
        skip: int = 0, 
        limit: int = 100,
        direction: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List calls with filtering options.
        """
        query = select(Call).offset(skip).limit(limit)
        
        if direction:
            query = query.where(Call.direction == direction)
        
        if status:
            query = query.where(Call.status == status)
        
        result = await self.db.execute(query)
        calls = result.scalars().all()
        
        return [self._call_to_dict(call) for call in calls]
    
    async def initiate_outbound_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiate an outbound call.
        """
        # Prepare call params
        call_params = {
            "from": request.get("from_number"),
            "to": request.get("to_number"),
            "prompt": request.get("prompt"),
            "voice_id": request.get("voice_id", "default"),
            "webhook_url": request.get("webhook_url")
        }
        
        # Make the call using VAPI
        call_result = await self.vapi_client.create_call(call_params)
        
        # Log the call
        customer_id = request.get("customer_id")
        if customer_id:
            await self.log_call(call_result.get("call_id"), {
                "customer_id": customer_id,
                "intent": "outbound",
                "outcome": "initiated"
            })
        
        return call_result
    
    async def transfer_call(self, call_id: str, phone_number: str) -> Dict[str, Any]:
        """
        Transfer an ongoing call to another number.
        """
        result = await self.vapi_client.transfer_call(call_id, phone_number)
        
        # Update call status
        await self.db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(status="transferred")
        )
        await self.db.commit()
        
        return result
    
    async def hangup_call(self, call_id: str) -> None:
        """
        Hang up an ongoing call.
        """
        await self.vapi_client.hangup_call(call_id)
        
        # Update call status
        await self.db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(status="completed")
        )
        await self.db.commit()
    
    async def _get_or_create_customer(self, customer_id: Optional[str], phone_number: Optional[str]) -> Customer:
        """
        Get existing customer or create a new one.
        """
        customer = None
        
        if customer_id:
            result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
            customer = result.scalars().first()
            
        if not customer and phone_number:
            result = await self.db.execute(select(Customer).where(Customer.phone_number == phone_number))
            customer = result.scalars().first()
        
        if not customer:
            # Create new customer
            customer = Customer(
                phone_number=phone_number,
                name=None,
                email=None,
                crm_id=None,
                metadata={}
            )
            self.db.add(customer)
            await self.db.commit()
            await self.db.refresh(customer)
        
        return customer
    
    def _call_to_dict(self, call: Call) -> Dict[str, Any]:
        """
        Convert Call model to dictionary.
        """
        return {
            "id": call.id,
            "call_id": call.call_id,
            "customer_id": call.customer_id,
            "direction": call.direction,
            "status": call.status,
            "start_time": call.start_time.isoformat() if call.start_time else None,
            "end_time": call.end_time.isoformat() if call.end_time else None,
            "duration": call.duration,
            "from_number": call.from_number,
            "to_number": call.to_number,
            "transcript": call.transcript,
            "recording_url": call.recording_url,
            "intent": call.intent,
            "outcome": call.outcome,
            "metadata": call.metadata,
            "created_at": call.created_at.isoformat() if call.created_at else None,
            "updated_at": call.updated_at.isoformat() if call.updated_at else None
        }