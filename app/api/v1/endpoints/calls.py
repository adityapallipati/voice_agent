from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import logging

from app.db.session import get_db
from app.models.calls import CallCreate, CallUpdate, CallResponse, ProcessCallRequest
from app.services.call_service import CallService
from app.core.vapi import VAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def process_call(
    request: ProcessCallRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Process an incoming call from VAPI.
    This is the main webhook endpoint that VAPI will call when a call is received.
    """
    try:
        call_service = CallService(db)
        result = await call_service.process_call(request)
        
        # Log call processing in the background
        background_tasks.add_task(call_service.log_call, request.call_id, result)
        
        return result
    except Exception as e:
        logger.exception(f"Error processing call: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing call: {str(e)}")

@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get call details by call ID.
    """
    call_service = CallService(db)
    call = await call_service.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call

@router.get("/", response_model=List[CallResponse])
async def list_calls(
    skip: int = 0,
    limit: int = 100,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List calls with filtering options.
    """
    call_service = CallService(db)
    calls = await call_service.list_calls(skip=skip, limit=limit, direction=direction, status=status)
    return calls

@router.post("/outbound", response_model=Dict[str, Any])
async def initiate_outbound_call(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate an outbound call.
    """
    call_service = CallService(db)
    result = await call_service.initiate_outbound_call(request)
    return result

@router.post("/{call_id}/transfer", response_model=Dict[str, Any])
async def transfer_call(
    call_id: str,
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Transfer an ongoing call to another number.
    """
    call_service = CallService(db)
    result = await call_service.transfer_call(call_id, request.get("phone_number"))
    return result

@router.post("/{call_id}/hangup")
async def hangup_call(
    call_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Hang up an ongoing call.
    """
    call_service = CallService(db)
    await call_service.hangup_call(call_id)
    return {"status": "success", "message": "Call hangup initiated"}