from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

class AppointmentBase(BaseModel):
    """Base appointment model with common fields."""
    customer_id: str = Field(..., description="Customer ID")
    service_type: str = Field(..., description="Type of service")
    appointment_time: datetime = Field(..., description="Appointment date and time")
    duration: Optional[int] = Field(30, description="Duration in minutes")
    notes: Optional[str] = Field(None, description="Additional notes")
    
class AppointmentCreate(AppointmentBase):
    """Model for creating an appointment."""
    created_by_call_id: Optional[str] = Field(None, description="Call ID that created this appointment")
    location: Optional[str] = Field(None, description="Appointment location")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('appointment_time')
    def validate_appointment_time(cls, v):
        # Ensure appointment is in the future
        if v < datetime.now():
            raise ValueError("Appointment time must be in the future")
        return v

class AppointmentUpdate(BaseModel):
    """Model for updating an appointment."""
    service_type: Optional[str] = Field(None, description="Type of service")
    appointment_time: Optional[datetime] = Field(None, description="Appointment date and time")
    duration: Optional[int] = Field(None, description="Duration in minutes")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: Optional[str] = Field(None, description="Appointment status")
    location: Optional[str] = Field(None, description="Appointment location")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('appointment_time')
    def validate_appointment_time(cls, v):
        if v is not None and v < datetime.now():
            raise ValueError("Appointment time must be in the future")
        return v

class AppointmentResponse(AppointmentBase):
    """Model for appointment response."""
    id: str
    status: str = Field(..., description="Appointment status: confirmed, cancelled, completed, no-show")
    created_by_call_id: Optional[str] = None
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def end_time(self) -> datetime:
        """Calculate the end time based on duration."""
        return self.appointment_time + timedelta(minutes=self.duration)
    
    class Config:
        orm_mode = True

class AppointmentRescheduleRequest(BaseModel):
    """Request model for rescheduling an appointment."""
    appointment_id: str = Field(..., description="Appointment ID to reschedule")
    new_appointment_time: datetime = Field(..., description="New appointment date and time")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")
    call_data: Optional[Dict[str, Any]] = Field(None, description="Call data if coming from a call")
    
    @validator('new_appointment_time')
    def validate_appointment_time(cls, v):
        if v < datetime.now():
            raise ValueError("New appointment time must be in the future")
        return v

class AppointmentCancelRequest(BaseModel):
    """Request model for cancelling an appointment."""
    appointment_id: str = Field(..., description="Appointment ID to cancel")
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    reschedule_later: bool = Field(False, description="Whether customer wants to reschedule later")
    call_data: Optional[Dict[str, Any]] = Field(None, description="Call data if coming from a call")

class AvailabilitySlot(BaseModel):
    """Model for an availability slot."""
    start_time: datetime
    end_time: datetime
    available: bool = True
    service_type: Optional[str] = None

class DailyAvailability(BaseModel):
    """Model for daily availability."""
    date: str
    slots: List[AvailabilitySlot]