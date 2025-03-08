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
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Process an incoming call from VAPI via N8N.
    This is the main webhook endpoint that handles call transcripts and generates responses.
    """
    try:
        logger.info(f"Received call processing request: {request}")
        
        # Convert the request dict to a ProcessCallRequest model
        # This handles the case when N8N sends data in a different format
        call_request = ProcessCallRequest(
            call_id=request.get("call_id", "unknown"),
            transcript=request.get("transcript", ""),
            customer_id=request.get("customer_id"),
            phone_number=request.get("phone_number") or request.get("from"),
            audio_url=request.get("audio_url"),
            metadata=request.get("metadata", {})
        )
        
        # Process the call
        call_service = CallService(db)
        result = await call_service.process_call(call_request)
        
        # Log call processing in the background
        if call_request.call_id != "unknown":
            background_tasks.add_task(call_service.log_call, call_request.call_id, result)
        
        # Format the response for VAPI
        # This is critical - VAPI expects a specific response format
        response = {
            "status": "success",
            "intent": result.get("intent", "unknown"),
            "response": result.get("response", "I'm sorry, I couldn't process your request.")
        }
        
        logger.info(f"Processed call with intent: {response['intent']}")
        return response
        
    except Exception as e:
        logger.exception(f"Error processing call: {e}")
        # Return a fallback response that VAPI can handle
        return {
            "status": "error",
            "intent": "error",
            "response": "I'm sorry, I'm having trouble understanding. Could you try again?"
        }

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