from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from app.db.session import get_db
from app.models.callbacks import (
    CallbackCreate, 
    CallbackUpdate, 
    CallbackResponse,
    CallbackStatusUpdate
)
from app.services.callback_service import CallbackService
from app.api.v1.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/schedule", response_model=CallbackResponse, status_code=status.HTTP_201_CREATED)
async def schedule_callback(
    callback: CallbackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule a new callback.
    """
    try:
        callback_service = CallbackService(db)
        result = await callback_service.create_callback(callback)
        return result
    except Exception as e:
        logger.exception(f"Error scheduling callback: {e}")
        raise HTTPException(status_code=500, detail=f"Error scheduling callback: {str(e)}")

@router.get("/{callback_id}", response_model=CallbackResponse)
async def get_callback(
    callback_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get callback details by ID.
    """
    callback_service = CallbackService(db)
    callback = await callback_service.get_callback(callback_id)
    if not callback:
        raise HTTPException(status_code=404, detail="Callback not found")
    return callback

@router.get("/", response_model=List[CallbackResponse])
async def list_callbacks(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List callbacks with filtering options.
    """
    callback_service = CallbackService(db)
    callbacks = await callback_service.list_callbacks(
        skip=skip, 
        limit=limit, 
        customer_id=customer_id, 
        status=status
    )
    return callbacks

@router.get("/pending", response_model=List[CallbackResponse])
async def get_pending_callbacks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get pending callbacks that need to be executed.
    Used by N8N to fetch callbacks that should be processed.
    """
    callback_service = CallbackService(db)
    callbacks = await callback_service.get_pending_callbacks(limit)
    return callbacks

@router.put("/{callback_id}", response_model=CallbackResponse)
async def update_callback(
    callback_id: str,
    callback: CallbackUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing callback.
    """
    callback_service = CallbackService(db)
    updated_callback = await callback_service.update_callback(callback_id, callback)
    if not updated_callback:
        raise HTTPException(status_code=404, detail="Callback not found")
    return updated_callback

@router.post("/{callback_id}/status", response_model=Dict[str, Any])
async def update_callback_status(
    callback_id: str,
    status_update: CallbackStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the status of a callback.
    Used by N8N to update the status after processing.
    """
    try:
        callback_service = CallbackService(db)
        await callback_service.update_callback_status(
            callback_id, 
            status_update.status,
            status_update.call_id
        )
        return {"status": "success", "callback_id": callback_id}
    except Exception as e:
        logger.exception(f"Error updating callback status: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating callback status: {str(e)}")

@router.delete("/{callback_id}", response_model=Dict[str, Any])
async def cancel_callback(
    callback_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a scheduled callback.
    """
    callback_service = CallbackService(db)
    await callback_service.cancel_callback(callback_id)
    return {"status": "success", "message": "Callback cancelled"}

@router.post("/batch", response_model=Dict[str, Any])
async def schedule_batch_callbacks(
    callbacks: List[CallbackCreate],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule multiple callbacks at once.
    Useful for marketing campaigns.
    """
    try:
        callback_service = CallbackService(db)
        
        # Process callbacks in the background to avoid timeout
        background_tasks.add_task(
            callback_service.create_batch_callbacks,
            callbacks
        )
        
        return {
            "status": "success", 
            "message": f"Scheduled {len(callbacks)} callbacks for processing in the background"
        }
    except Exception as e:
        logger.exception(f"Error scheduling batch callbacks: {e}")
        raise HTTPException(status_code=500, detail=f"Error scheduling batch callbacks: {str(e)}")

@router.get("/customer/{customer_id}", response_model=List[CallbackResponse])
async def get_customer_callbacks(
    customer_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all callbacks for a specific customer.
    """
    callback_service = CallbackService(db)
    callbacks = await callback_service.list_callbacks(
        customer_id=customer_id,
        status=status,
        limit=100
    )
    return callbacks

@router.post("/{callback_id}/generate-script", response_model=Dict[str, Any])
async def generate_callback_script(
    callback_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a call script for an existing callback.
    """
    callback_service = CallbackService(db)
    script = await callback_service.generate_callback_script(callback_id)
    return {"callback_id": callback_id, "script": script}