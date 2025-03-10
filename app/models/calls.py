from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class CallBase(BaseModel):
    """Base call model with common fields."""
    call_id: str = Field(..., description="Unique call identifier")
    direction: str = Field(..., description="Call direction (inbound/outbound)")
    
class ProcessCallRequest(BaseModel):
    """Model for processing a call from VAPI webhook."""
    call_id: str = Field(..., description="Unique call identifier")
    transcript: str = Field(..., description="Call transcript")
    customer_id: Optional[str] = Field(None, description="Customer ID if known")
    phone_number: Optional[str] = Field(None, description="Caller phone number")
    audio_url: Optional[str] = Field(None, description="URL to audio recording")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        # Allow extra fields to be flexible with N8N payloads
        extra = "allow"

class CallCreate(CallBase):
    """Model for creating a call record."""
    customer_id: Optional[str] = None
    status: str = "in-progress"
    start_time: datetime = Field(default_factory=datetime.now)
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    intent: Optional[str] = None
    outcome: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('call_id', pre=True, always=True)
    def default_call_id(cls, v):
        return v or str(uuid.uuid4())

class CallUpdate(BaseModel):
    """Model for updating a call record."""
    status: Optional[str] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    intent: Optional[str] = None
    outcome: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CallResponse(CallBase):
    """Model for call response."""
    id: str
    customer_id: Optional[str] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    intent: Optional[str] = None
    outcome: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class OutboundCallRequest(BaseModel):
    """Model for creating an outbound call."""
    from_number: str = Field(..., description="Caller phone number")
    to_number: str = Field(..., description="Recipient phone number")
    prompt: str = Field(..., description="Initial prompt for the call")
    voice_id: Optional[str] = Field("default", description="Voice ID to use")
    customer_id: Optional[str] = Field(None, description="Customer ID if known")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for call events")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
class TransferCallRequest(BaseModel):
    """Model for transferring a call."""
    phone_number: str = Field(..., description="Phone number to transfer to")

class CallProcessingResponse(BaseModel):
    """Model for call processing response."""
    status: str = Field(..., description="Status of the call processing (success/error)")
    intent: str = Field(..., description="Detected intent from the call")
    response: str = Field(..., description="Response text to be sent back to the caller")
    call_id: Optional[str] = Field(None, description="Call ID if available")
    customer_id: Optional[str] = Field(None, description="Customer ID if available")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        # Make this model match the structure expected by VAPI
        schema_extra = {
            "example": {
                "status": "success",
                "intent": "book_appointment",
                "response": "I'd be happy to book your haircut for tomorrow at 3pm. Is that correct?"
            }
        }