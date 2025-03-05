from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from app.db.session import get_db
from app.models.appointments import (
    AppointmentCreate, 
    AppointmentUpdate, 
    AppointmentResponse,
    AppointmentRescheduleRequest,
    AppointmentCancelRequest
)
from app.services.appointment_service import AppointmentService
from app.api.v1.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment: AppointmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new appointment.
    """
    try:
        appointment_service = AppointmentService(db)
        result = await appointment_service.create_appointment(appointment)
        return result
    except Exception as e:
        logger.exception(f"Error creating appointment: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating appointment: {str(e)}")

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get appointment details by ID.
    """
    appointment_service = AppointmentService(db)
    appointment = await appointment_service.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List appointments with filtering options.
    """
    appointment_service = AppointmentService(db)
    appointments = await appointment_service.list_appointments(
        skip=skip, 
        limit=limit, 
        customer_id=customer_id, 
        status=status,
        from_date=from_date,
        to_date=to_date
    )
    return appointments

@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    appointment: AppointmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing appointment.
    """
    appointment_service = AppointmentService(db)
    updated_appointment = await appointment_service.update_appointment(appointment_id, appointment)
    if not updated_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return updated_appointment

@router.post("/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    request: AppointmentRescheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reschedule an existing appointment.
    Endpoint for handling reschedule requests from calls.
    """
    try:
        appointment_service = AppointmentService(db)
        result = await appointment_service.reschedule_appointment(
            request.appointment_id, 
            request.new_appointment_time,
            request.reason
        )
        return result
    except Exception as e:
        logger.exception(f"Error rescheduling appointment: {e}")
        raise HTTPException(status_code=500, detail=f"Error rescheduling appointment: {str(e)}")

@router.post("/cancel", response_model=Dict[str, Any])
async def cancel_appointment(
    request: AppointmentCancelRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an existing appointment.
    Endpoint for handling cancellation requests from calls.
    """
    try:
        appointment_service = AppointmentService(db)
        result = await appointment_service.cancel_appointment(
            request.appointment_id,
            request.reason,
            request.reschedule_later
        )
        return {"status": "success", "appointment_id": request.appointment_id}
    except Exception as e:
        logger.exception(f"Error cancelling appointment: {e}")
        raise HTTPException(status_code=500, detail=f"Error cancelling appointment: {str(e)}")

@router.post("/{appointment_id}/confirm", response_model=Dict[str, Any])
async def confirm_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm an appointment.
    """
    appointment_service = AppointmentService(db)
    await appointment_service.update_appointment_status(appointment_id, "confirmed")
    return {"status": "success", "appointment_id": appointment_id}

@router.post("/{appointment_id}/complete", response_model=Dict[str, Any])
async def complete_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an appointment as completed.
    """
    appointment_service = AppointmentService(db)
    await appointment_service.update_appointment_status(appointment_id, "completed")
    return {"status": "success", "appointment_id": appointment_id}

@router.post("/{appointment_id}/no-show", response_model=Dict[str, Any])
async def no_show_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an appointment as no-show.
    """
    appointment_service = AppointmentService(db)
    await appointment_service.update_appointment_status(appointment_id, "no-show")
    return {"status": "success", "appointment_id": appointment_id}

@router.get("/customer/{customer_id}", response_model=List[AppointmentResponse])
async def get_customer_appointments(
    customer_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all appointments for a specific customer.
    """
    appointment_service = AppointmentService(db)
    appointments = await appointment_service.list_appointments(
        customer_id=customer_id,
        status=status,
        limit=100
    )
    return appointments

@router.get("/availability/{date}", response_model=Dict[str, Any])
async def get_availability(
    date: str,
    service_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get availability slots for a specific date.
    """
    appointment_service = AppointmentService(db)
    availability = await appointment_service.get_availability(date, service_type)
    return {"date": date, "available_slots": availability}