from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Customer(BaseModel):
    __tablename__ = "customers"
    
    name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True)
    crm_id = Column(String, nullable=True, index=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    calls = relationship("Call", back_populates="customer")
    appointments = relationship("Appointment", back_populates="customer")
    callbacks = relationship("Callback", back_populates="customer")

class Call(BaseModel):
    __tablename__ = "calls"
    
    call_id = Column(String, nullable=False, index=True, unique=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)
    direction = Column(String, nullable=False)  # inbound, outbound
    status = Column(String, nullable=False)  # in-progress, completed, failed
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    from_number = Column(String, nullable=True)
    to_number = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    recording_url = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="calls")

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    service_type = Column(String, nullable=False)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    duration = Column(Integer, nullable=True)  # in minutes
    status = Column(String, nullable=False)  # confirmed, cancelled, completed, no-show
    notes = Column(Text, nullable=True)
    created_by_call_id = Column(String, ForeignKey("calls.call_id"), nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="appointments")

class Callback(BaseModel):
    __tablename__ = "callbacks"
    
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    phone_number = Column(String, nullable=False)
    callback_time = Column(DateTime(timezone=True), nullable=False)
    purpose = Column(String, nullable=False)
    call_script = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # scheduled, completed, failed, cancelled
    result = Column(String, nullable=True)
    call_id = Column(String, ForeignKey("calls.call_id"), nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="callbacks")

class PromptTemplate(BaseModel):
    __tablename__ = "prompt_templates"
    
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    
class KnowledgeItem(BaseModel):
    __tablename__ = "knowledge_items"
    
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)