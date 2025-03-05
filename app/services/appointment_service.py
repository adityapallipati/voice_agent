import logging
from sqlalchemy import select, update, and_, or_, between
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, time
import uuid

from app.db.models import Appointment, Customer
from app.models.appointments import AppointmentCreate, AppointmentUpdate, AvailabilitySlot
from app.core.crm import get_crm_client

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.crm_client = get_crm_client()
    
    async def create_appointment(self, appointment_data: AppointmentCreate) -> Dict[str, Any]:
        """
        Create a new appointment.
        """
        logger.info(f"Creating appointment for customer {appointment_data.customer_id}")
        
        # Validate customer exists
        customer_exists = await self._check_customer_exists(appointment_data.customer_id)
        if not customer_exists:
            logger.error(f"Customer {appointment_data.customer_id} not found")
            raise ValueError(f"Customer {appointment_data.customer_id} not found")
        
        # Check for appointment conflicts
        conflicts = await self._check_appointment_conflicts(
            appointment_data.appointment_time,
            appointment_data.duration,
            None  # No appointment ID to exclude
        )
        
        if conflicts:
            logger.warning(f"Appointment conflicts detected: {conflicts}")
            raise ValueError("The requested appointment time conflicts with existing appointments")
        
        # Calculate end time
        appointment_end_time = appointment_data.appointment_time + timedelta(minutes=appointment_data.duration or 30)
        
        # Create appointment in database
        appointment = Appointment(
            id=str(uuid.uuid4()),
            customer_id=appointment_data.customer_id,
            service_type=appointment_data.service_type,
            appointment_time=appointment_data.appointment_time,
            duration=appointment_data.duration or 30,
            status="confirmed",
            notes=appointment_data.notes,
            created_by_call_id=appointment_data.created_by_call_id,
            metadata=appointment_data.metadata or {}
        )
        
        self.db.add(appointment)
        await self.db.commit()
        await self.db.refresh(appointment)
        
        # Create appointment in CRM
        try:
            crm_appointment = await self.crm_client.create_appointment({
                "customer_id": appointment_data.customer_id,
                "service_type": appointment_data.service_type,
                "appointment_time": appointment_data.appointment_time.isoformat(),
                "end_time": appointment_end_time.isoformat(),
                "notes": appointment_data.notes,
                "location": appointment_data.metadata.get("location") if appointment_data.metadata else None,
                "db_id": appointment.id
            })
            
            # Store CRM appointment ID in metadata
            if crm_appointment and crm_appointment.get("id"):
                appointment.metadata = appointment.metadata or {}
                appointment.metadata["crm_appointment_id"] = crm_appointment["id"]
                await self.db.commit()
        
        except Exception as e:
            logger.error(f"Error creating appointment in CRM: {e}")
            # We continue even if CRM integration fails
        
        return self._appointment_to_dict(appointment)
    
    async def get_appointment(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get appointment details by ID.
        """
        result = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalars().first()
        
        if not appointment:
            return None
        
        return self._appointment_to_dict(appointment)
    
    async def list_appointments(
        self, 
        skip: int = 0, 
        limit: int = 100,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List appointments with filtering options.
        """
        query = select(Appointment).offset(skip).limit(limit)
        
        # Apply filters
        if customer_id:
            query = query.where(Appointment.customer_id == customer_id)
        
        if status:
            query = query.where(Appointment.status == status)
        
        if from_date and to_date:
            try:
                from_datetime = datetime.fromisoformat(from_date)
                to_datetime = datetime.fromisoformat(to_date)
                query = query.where(between(Appointment.appointment_time, from_datetime, to_datetime))
            except ValueError as e:
                logger.error(f"Error parsing date filters: {e}")
        elif from_date:
            try:
                from_datetime = datetime.fromisoformat(from_date)
                query = query.where(Appointment.appointment_time >= from_datetime)
            except ValueError as e:
                logger.error(f"Error parsing from_date: {e}")
        elif to_date:
            try:
                to_datetime = datetime.fromisoformat(to_date)
                query = query.where(Appointment.appointment_time <= to_datetime)
            except ValueError as e:
                logger.error(f"Error parsing to_date: {e}")
        
        # Order by appointment time
        query = query.order_by(Appointment.appointment_time)
        
        result = await self.db.execute(query)
        appointments = result.scalars().all()
        
        return [self._appointment_to_dict(appointment) for appointment in appointments]
    
    async def update_appointment(self, appointment_id: str, appointment_data: AppointmentUpdate) -> Optional[Dict[str, Any]]:
        """
        Update an existing appointment.
        """
        # Get appointment
        result = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalars().first()
        
        if not appointment:
            logger.warning(f"Appointment {appointment_id} not found for update")
            return None
        
        # Check for conflicts if appointment time is changing
        if appointment_data.appointment_time and appointment_data.appointment_time != appointment.appointment_time:
            conflicts = await self._check_appointment_conflicts(
                appointment_data.appointment_time,
                appointment_data.duration or appointment.duration,
                appointment_id
            )
            
            if conflicts:
                logger.warning(f"Appointment conflicts detected: {conflicts}")
                raise ValueError("The requested appointment time conflicts with existing appointments")
        
        # Update appointment fields
        if appointment_data.service_type is not None:
            appointment.service_type = appointment_data.service_type
        
        if appointment_data.appointment_time is not None:
            appointment.appointment_time = appointment_data.appointment_time
        
        if appointment_data.duration is not None:
            appointment.duration = appointment_data.duration
        
        if appointment_data.notes is not None:
            appointment.notes = appointment_data.notes
        
        if appointment_data.status is not None:
            appointment.status = appointment_data.status
        
        if appointment_data.metadata is not None:
            appointment.metadata = appointment_data.metadata
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        # Update appointment in CRM
        try:
            # If we have a CRM appointment ID, update it
            crm_appointment_id = appointment.metadata.get("crm_appointment_id") if appointment.metadata else None
            
            if crm_appointment_id:
                # Calculate end time
                appointment_end_time = appointment.appointment_time + timedelta(minutes=appointment.duration)
                
                await self.crm_client.update_appointment(crm_appointment_id, {
                    "service_type": appointment.service_type,
                    "appointment_time": appointment.appointment_time.isoformat(),
                    "end_time": appointment_end_time.isoformat(),
                    "notes": appointment.notes,
                    "status": appointment.status,
                    "location": appointment.metadata.get("location") if appointment.metadata else None
                })
        except Exception as e:
            logger.error(f"Error updating appointment in CRM: {e}")
            # We continue even if CRM integration fails
        
        return self._appointment_to_dict(appointment)
    
    async def reschedule_appointment(
        self, 
        appointment_id: str, 
        new_appointment_time: datetime,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reschedule an existing appointment.
        """
        # Get appointment
        result = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalars().first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        # Check for conflicts
        conflicts = await self._check_appointment_conflicts(
            new_appointment_time,
            appointment.duration,
            appointment_id
        )
        
        if conflicts:
            logger.warning(f"Appointment conflicts detected: {conflicts}")
            raise ValueError("The requested appointment time conflicts with existing appointments")
        
        # Store old time for logging
        old_time = appointment.appointment_time
        
        # Update appointment
        appointment.appointment_time = new_appointment_time
        
        # Add reason to notes if provided
        if reason:
            if appointment.notes:
                appointment.notes += f"\n\nRescheduled from {old_time.isoformat()} to {new_appointment_time.isoformat()}. Reason: {reason}"
            else:
                appointment.notes = f"Rescheduled from {old_time.isoformat()} to {new_appointment_time.isoformat()}. Reason: {reason}"
        
        # Add reschedule info to metadata
        if not appointment.metadata:
            appointment.metadata = {}
        
        if not appointment.metadata.get("reschedule_history"):
            appointment.metadata["reschedule_history"] = []
        
        appointment.metadata["reschedule_history"].append({
            "old_time": old_time.isoformat(),
            "new_time": new_appointment_time.isoformat(),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        # Update appointment in CRM
        try:
            # If we have a CRM appointment ID, update it
            crm_appointment_id = appointment.metadata.get("crm_appointment_id") if appointment.metadata else None
            
            if crm_appointment_id:
                # Calculate end time
                appointment_end_time = appointment.appointment_time + timedelta(minutes=appointment.duration)
                
                await self.crm_client.update_appointment(crm_appointment_id, {
                    "appointment_time": appointment.appointment_time.isoformat(),
                    "end_time": appointment_end_time.isoformat(),
                    "notes": appointment.notes
                })
        except Exception as e:
            logger.error(f"Error updating appointment in CRM: {e}")
            # We continue even if CRM integration fails
        
        logger.info(f"Appointment {appointment_id} rescheduled from {old_time} to {new_appointment_time}")
        return self._appointment_to_dict(appointment)
    
    async def cancel_appointment(
        self, 
        appointment_id: str, 
        reason: Optional[str] = None,
        reschedule_later: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel an existing appointment.
        """
        # Get appointment
        result = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalars().first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        # Update appointment status
        appointment.status = "cancelled"
        
        # Add reason to notes if provided
        if reason:
            if appointment.notes:
                appointment.notes += f"\n\nCancelled: {reason}"
            else:
                appointment.notes = f"Cancelled: {reason}"
        
        # Add cancellation info to metadata
        if not appointment.metadata:
            appointment.metadata = {}
        
        appointment.metadata["cancellation"] = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "reschedule_later": reschedule_later
        }
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        # Update appointment in CRM
        try:
            # If we have a CRM appointment ID, update it
            crm_appointment_id = appointment.metadata.get("crm_appointment_id") if appointment.metadata else None
            
            if crm_appointment_id:
                await self.crm_client.update_appointment(crm_appointment_id, {
                    "status": "cancelled",
                    "notes": appointment.notes
                })
        except Exception as e:
            logger.error(f"Error updating appointment in CRM: {e}")
            # We continue even if CRM integration fails
        
        logger.info(f"Appointment {appointment_id} cancelled. Reschedule later: {reschedule_later}")
        return self._appointment_to_dict(appointment)
    
    async def update_appointment_status(self, appointment_id: str, status: str) -> Dict[str, Any]:
        """
        Update the status of an appointment.
        """
        # Validate status
        valid_statuses = ["confirmed", "cancelled", "completed", "no-show"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        # Get appointment
        result = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        appointment = result.scalars().first()
        
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")
        
        # Update status
        appointment.status = status
        
        # Add status change to metadata
        if not appointment.metadata:
            appointment.metadata = {}
        
        if not appointment.metadata.get("status_history"):
            appointment.metadata["status_history"] = []
        
        appointment.metadata["status_history"].append({
            "old_status": appointment.status,
            "new_status": status,
            "timestamp": datetime.now().isoformat()
        })
        
        await self.db.commit()
        await self.db.refresh(appointment)
        
        # Update appointment in CRM
        try:
            # If we have a CRM appointment ID, update it
            crm_appointment_id = appointment.metadata.get("crm_appointment_id") if appointment.metadata else None
            
            if crm_appointment_id:
                await self.crm_client.update_appointment(crm_appointment_id, {
                    "status": status
                })
        except Exception as e:
            logger.error(f"Error updating appointment in CRM: {e}")
            # We continue even if CRM integration fails
        
        logger.info(f"Appointment {appointment_id} status updated to {status}")
        return self._appointment_to_dict(appointment)
    
    async def get_availability(self, date_str: str, service_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get availability slots for a specific date.
        
        This is a simplified implementation that assumes:
        - Business hours are 9am to 5pm
        - Each appointment slot is 30 minutes
        - No breaks or lunch time
        """
        try:
            # Parse the date string
            target_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use ISO format (YYYY-MM-DD)")
        
        # Business hours
        business_start = time(9, 0)  # 9:00 AM
        business_end = time(17, 0)   # 5:00 PM
        
        # Default slot duration (30 minutes)
        slot_duration = timedelta(minutes=30)
        
        # Generate time slots
        slots = []
        current_time = datetime.combine(target_date, business_start)
        end_time = datetime.combine(target_date, business_end)
        
        while current_time < end_time:
            slot_end = current_time + slot_duration
            
            # Initialize as available
            is_available = True
            
            # Convert to dict for response
            slot = {
                "start_time": current_time.isoformat(),
                "end_time": slot_end.isoformat(),
                "available": is_available
            }
            
            slots.append(slot)
            current_time = slot_end
        
        # Now check existing appointments to mark unavailable slots
        start_of_day = datetime.combine(target_date, time(0, 0))
        end_of_day = datetime.combine(target_date, time(23, 59, 59))
        
        query = select(Appointment).where(
            and_(
                Appointment.appointment_time >= start_of_day,
                Appointment.appointment_time < end_of_day,
                Appointment.status != "cancelled"
            )
        )
        
        # Filter by service type if specified
        if service_type:
            query = query.where(Appointment.service_type == service_type)
        
        result = await self.db.execute(query)
        appointments = result.scalars().all()
        
        # Mark slots as unavailable based on existing appointments
        for appointment in appointments:
            appt_start = appointment.appointment_time
            appt_end = appt_start + timedelta(minutes=appointment.duration)
            
            # Mark all overlapping slots as unavailable
            for slot in slots:
                slot_start = datetime.fromisoformat(slot["start_time"])
                slot_end = datetime.fromisoformat(slot["end_time"])
                
                # Check for overlap
                if (appt_start < slot_end and appt_end > slot_start):
                    slot["available"] = False
        
        return slots
    
    async def _check_customer_exists(self, customer_id: str) -> bool:
        """
        Check if a customer exists.
        """
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        return result.scalars().first() is not None
    
    async def _check_appointment_conflicts(
        self, 
        appointment_time: datetime, 
        duration: int,
        exclude_appointment_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Check if the requested appointment time conflicts with existing appointments.
        """
        # Calculate appointment end time
        appointment_end = appointment_time + timedelta(minutes=duration)
        
        # Find overlapping appointments
        query = select(Appointment).where(
            and_(
                Appointment.status != "cancelled",
                or_(
                    # New appointment starts during an existing one
                    and_(
                        Appointment.appointment_time <= appointment_time,
                        Appointment.appointment_time + timedelta(minutes=Appointment.duration) > appointment_time
                    ),
                    # New appointment ends during an existing one
                    and_(
                        Appointment.appointment_time < appointment_end,
                        Appointment.appointment_time + timedelta(minutes=Appointment.duration) >= appointment_end
                    ),
                    # New appointment completely contains an existing one
                    and_(
                        Appointment.appointment_time >= appointment_time,
                        Appointment.appointment_time + timedelta(minutes=Appointment.duration) <= appointment_end
                    )
                )
            )
        )
        
        # Exclude the appointment being updated
        if exclude_appointment_id:
            query = query.where(Appointment.id != exclude_appointment_id)
        
        result = await self.db.execute(query)
        conflicts = result.scalars().all()
        
        return [self._appointment_to_dict(appointment) for appointment in conflicts]
    
    def _appointment_to_dict(self, appointment: Appointment) -> Dict[str, Any]:
        """
        Convert Appointment model to dictionary.
        """
        return {
            "id": appointment.id,
            "customer_id": appointment.customer_id,
            "service_type": appointment.service_type,
            "appointment_time": appointment.appointment_time,
            "duration": appointment.duration,
            "status": appointment.status,
            "notes": appointment.notes,
            "created_by_call_id": appointment.created_by_call_id,
            "metadata": appointment.metadata,
            "created_at": appointment.created_at,
            "updated_at": appointment.updated_at
        }