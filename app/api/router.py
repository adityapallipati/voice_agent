from fastapi import APIRouter

from app.api.v1.endpoints import calls, appointments, callbacks, prompts, knowledge, customers

api_router = APIRouter()

# Include all API endpoint routers
api_router.include_router(calls.router, prefix="/v1/calls", tags=["calls"])
api_router.include_router(appointments.router, prefix="/v1/appointments", tags=["appointments"])
api_router.include_router(callbacks.router, prefix="/v1/callbacks", tags=["callbacks"])
api_router.include_router(prompts.router, prefix="/v1/prompts", tags=["prompts"])
api_router.include_router(knowledge.router, prefix="/v1/knowledge", tags=["knowledge"])
api_router.include_router(customers.router, prefix="/v1/customers", tags=["customers"])