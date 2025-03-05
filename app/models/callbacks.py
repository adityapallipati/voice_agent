from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class CallbackBase(BaseModel):
    """Base callback model with common fields."""
    customer_id: str = Field(..., description="Customer ID")
    phone_number: str = Field(..., description="Phone number to call")
    callback_time: datetime = Field(..., description="Scheduled callback time")
    purpose: str = Field(..., description="Purpose of the callback")
    
class CallbackCreate(CallbackBase):
    """Model for creating a callback."""
    call_script: Optional[str] = Field(None, description="Script to use for the call")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('callback_time')
    def validate_callback_time(cls, v):
        # Allow callbacks in the past for testing, but provide a warning
        if v < datetime.now():
            # Just return the value with a warning in logs
            import logging
            logging.getLogger(__name__).warning(f"Callback time {v} is in the past")
        return v

class CallbackUpdate(BaseModel):
    """Model for updating a callback."""
    phone_number: Optional[str] = Field(None, description="Phone number to call")
    callback_time: Optional[datetime] = Field(None, description="Scheduled callback time")
    purpose: Optional[str] = Field(None, description="Purpose of the callback")
    call_script: Optional[str] = Field(None, description="Script to use for the call")
    status: Optional[str] = Field(None, description="Callback status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('callback_time')
    def validate_callback_time(cls, v):
        if v is not None and v < datetime.now():
            # Just return the value with a warning in logs
            import logging
            logging.getLogger(__name__).warning(f"Updated callback time {v} is in the past")
        return v

class CallbackResponse(CallbackBase):
    """Model for callback response."""
    id: str
    status: str = Field(..., description="Callback status: scheduled, completed, failed, cancelled")
    call_script: Optional[str] = None
    result: Optional[str] = None
    call_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

class CallbackStatusUpdate(BaseModel):
    """Model for updating callback status."""
    status: str = Field(..., description="Callback status: in_progress, completed, failed, cancelled")
    call_id: Optional[str] = Field(None, description="ID of the call (if status is in_progress or completed)")
    result: Optional[str] = Field(None, description="Result of the callback (if status is completed or failed)")
    notes: Optional[str] = Field(None, description="Additional notes")

class CallbackBatchCreate(BaseModel):
    """Model for batch creating callbacks."""
    callbacks: List[CallbackCreate] = Field(..., description="List of callbacks to create")
    campaign_name: Optional[str] = Field(None, description="Name of the campaign")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class CallbackFilter(BaseModel):
    """Model for filtering callbacks."""
    status: Optional[str] = Field(None, description="Filter by status")
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    from_date: Optional[datetime] = Field(None, description="Filter callbacks from this date")
    to_date: Optional[datetime] = Field(None, description="Filter callbacks to this date")
    purpose: Optional[str] = Field(None, description="Filter by purpose")