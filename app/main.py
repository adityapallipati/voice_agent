from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import logging
import json

from app.db.session import get_db
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title="Voice Agent API",
    description="API for handling voice agent functionality",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Voice Agent API is running"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app_env": settings.APP_ENV,
        "prompt_templates_dir": settings.PROMPT_TEMPLATES_DIR,
        "prompt_files": os.listdir(settings.PROMPT_TEMPLATES_DIR) if os.path.exists(settings.PROMPT_TEMPLATES_DIR) else []
    }

# Process call endpoint
@app.post("/api/v1/calls/process")
def process_call(call_data: dict, db: Session = Depends(get_db)):
    logger.info(f"Processing call: {json.dumps(call_data, default=str)}")
    
    # For testing, just echo back with a static response
    return {
        "status": "success",
        "intent": "general_question",
        "response": "Thank you for calling. This is a test response from the Voice Agent API."
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
