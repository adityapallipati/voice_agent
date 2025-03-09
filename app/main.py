from datetime import datetime, timedelta
import re
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
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
    
    transcript = call_data.get("transcript", "").lower()
    
    if "appointment" in transcript:
        intent = "book_appointment"
    elif "reschedule" in transcript:
        intent = "reschedule_appointment"
    elif "cancel" in transcript:
        intent = "cancel_appointment"
    elif "talk to a human" in transcript:
        intent = "transfer"
    else:
        intent = "general_question"

    return {
        "status": "success",
        "intent": intent,
        "response": f"Detected intent: {intent}"
    }

# Enhanced regex patterns with more patterns and next-day fallbacks
DATE_REGEX = r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)|(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b"
TIME_REGEX = r"\b(\d{1,2})(?::(\d{2}))?\s*(?:o'clock)?\s*(AM|PM|am|pm)?\b"

def get_next_weekday(weekday):
    """Get the date of the next occurrence of a weekday."""
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today = datetime.utcnow()
    days_ahead = (weekdays.index(weekday.lower()) - today.weekday()) % 7
    if days_ahead == 0:  # If today is the given weekday, schedule for next week
        days_ahead = 7
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime("%Y-%m-%d")

def get_this_weekday(weekday):
    """Get the date of this week's occurrence of a weekday."""
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today = datetime.utcnow()
    target_weekday = weekdays.index(weekday.lower())
    current_weekday = today.weekday()
    
    if target_weekday < current_weekday:  # If the day has already passed this week
        days_ahead = 7 - (current_weekday - target_weekday)  # Go to next week
    else:
        days_ahead = target_weekday - current_weekday
    
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime("%Y-%m-%d")

def get_next_business_day():
    """Get the next business day (Monday-Friday), skipping weekends."""
    today = datetime.utcnow()
    days_ahead = 1  # Start with tomorrow
    
    # If tomorrow is a weekend, move to Monday
    next_day = today + timedelta(days=days_ahead)
    if next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        days_ahead += (7 - next_day.weekday())
    
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

def contains_appointment_intent(transcript):
    """Detect if the transcript contains intention to book an appointment."""
    if not transcript:
        return False
        
    appointment_keywords = [
        "appointment", "schedule", "book", "reserve", "set up", "meeting", 
        "consultation", "session", "talk", "chat", "meet", "visit",
        "consult", "conversation", "discuss", "review", "call"
    ]
    
    lowercase_transcript = transcript.lower()
    return any(keyword in lowercase_transcript for keyword in appointment_keywords)

# Enhanced standardize_time function
def standardize_time(time_str: str) -> str:
    """Ensure time is in HH:MM AM/PM format and remove extra spaces."""
    if not time_str:
        return None
        
    time_str = time_str.strip().upper()  # Remove spaces and standardize case
    
    # Fix spaces between digits and colons
    time_str = re.sub(r'(\d+)\s*:\s*(\d+)', r'\1:\2', time_str)
    
    # Clean spaces between time and AM/PM
    time_str = re.sub(r'(\d+(?::\d+)?)\s+(AM|PM)', r'\1 \2', time_str)
    
    # If no colon (e.g., "3 PM"), add ":00"
    if ":" not in time_str and ("AM" in time_str or "PM" in time_str):
        time_str = re.sub(r'(\d+)\s*(AM|PM)', r'\1:00 \2', time_str)
    
    return time_str

def extract_datetime(transcript):
    """Robust function to extract appointment date and time from a transcript with GUARANTEED fallbacks."""
    # Log the incoming transcript
    logger.info(f"[EXTRACT] Transcript: '{transcript}'")
    
    # Check for missing transcript
    if not transcript:
        logger.error("[EXTRACT] Empty transcript provided")
        # Even with empty transcript, provide fallbacks for appointment booking
        tomorrow = get_next_business_day()
        return tomorrow, "10:00 AM"
    
    # Step 1: Try to find an explicit date
    date_match = re.search(DATE_REGEX, transcript, re.IGNORECASE)
    time_match = re.search(TIME_REGEX, transcript, re.IGNORECASE)
    
    logger.info(f"[EXTRACT] Date match: {date_match.group(0) if date_match else 'NONE'}")
    logger.info(f"[EXTRACT] Time match: {time_match.group(0) if time_match else 'NONE'}")
    
    # Extract date with fallback
    extracted_date = None
    has_explicit_date = False
    
    if date_match:
        has_explicit_date = True
        extracted_date_text = date_match.group(0).lower()
        try:
            # Handle "next [weekday]"
            next_day_match = re.search(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", extracted_date_text, re.IGNORECASE)
            this_day_match = re.search(r"this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", extracted_date_text, re.IGNORECASE)
            
            if next_day_match:
                weekday = next_day_match.group(1).lower()
                extracted_date = get_next_weekday(weekday)
                logger.info(f"[EXTRACT] Found 'next {weekday}', calculated as {extracted_date}")
            elif this_day_match:
                weekday = this_day_match.group(1).lower()
                extracted_date = get_this_weekday(weekday)
                logger.info(f"[EXTRACT] Found 'this {weekday}', calculated as {extracted_date}")
            # Handle plain weekday names
            elif extracted_date_text in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                extracted_date = get_next_weekday(extracted_date_text)
                logger.info(f"[EXTRACT] Found weekday '{extracted_date_text}', calculated as {extracted_date}")
            # Handle tomorrow/today
            elif extracted_date_text == "tomorrow":
                extracted_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
                logger.info(f"[EXTRACT] Found 'tomorrow', calculated as {extracted_date}")
            elif extracted_date_text == "today":
                extracted_date = datetime.utcnow().strftime("%Y-%m-%d")
                logger.info(f"[EXTRACT] Found 'today', calculated as {extracted_date}")
            # Handle standard date format YYYY-MM-DD
            elif re.match(r'\d{4}-\d{2}-\d{2}', extracted_date_text):
                extracted_date = extracted_date_text
                logger.info(f"[EXTRACT] Found ISO date format: {extracted_date}")
            # Handle month/day patterns
            else:
                # Try to match various date formats
                month_pattern = r"(january|february|march|april|may|june|july|august|september|october|november|december)"
                day_pattern = r"(\d{1,2})(?:st|nd|rd|th)?"
                
                # "March 12" or "March 12th"
                month_day_match = re.search(f"{month_pattern}\\s+{day_pattern}", extracted_date_text, re.IGNORECASE)
                # "12 March" or "12th of March"
                day_month_match = re.search(f"{day_pattern}(?:\\s+of)?\\s+{month_pattern}", extracted_date_text, re.IGNORECASE)
                
                if month_day_match:
                    month, day = month_day_match.groups()
                    month_num = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].index(month.lower()) + 1
                    current_year = datetime.utcnow().year
                    extracted_date = f"{current_year}-{month_num:02d}-{int(day):02d}"
                    logger.info(f"[EXTRACT] Found '{month} {day}' format, calculated as {extracted_date}")
                elif day_month_match:
                    day, month = day_month_match.groups()
                    month_num = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].index(month.lower()) + 1
                    current_year = datetime.utcnow().year
                    extracted_date = f"{current_year}-{month_num:02d}-{int(day):02d}"
                    logger.info(f"[EXTRACT] Found '{day} {month}' format, calculated as {extracted_date}")
                # Handle MM/DD or MM/DD/YYYY format
                elif "/" in extracted_date_text:
                    parts = extracted_date_text.split("/")
                    if len(parts) == 2:
                        month, day = parts
                        current_year = datetime.utcnow().year
                        extracted_date = f"{current_year}-{int(month):02d}-{int(day):02d}"
                        logger.info(f"[EXTRACT] Found MM/DD format, calculated as {extracted_date}")
                    elif len(parts) == 3:
                        month, day, year = parts
                        if len(year) == 2:
                            year = f"20{year}"
                        extracted_date = f"{year}-{int(month):02d}-{int(day):02d}"
                        logger.info(f"[EXTRACT] Found MM/DD/YYYY format, calculated as {extracted_date}")
        except Exception as e:
            logger.error(f"[EXTRACT] Failed to parse date format '{extracted_date_text}': {e}")
            extracted_date = None
    
    # Special handling for vague date references not caught by the regex
    if not extracted_date:
        # Check for "next week", "this week" phrases
        next_week_match = re.search(r"\b(?:next|this)\s+week\b", transcript, re.IGNORECASE)
        few_days_match = re.search(r"\bin\s+(?:a\s+)?(?:few|couple|[2-5])\s+days\b", transcript, re.IGNORECASE)
        
        if next_week_match:
            # Default to Monday of next week
            today = datetime.utcnow()
            days_ahead = 7 - today.weekday()
            if days_ahead <= 0:  # If today is already Monday
                days_ahead += 7
            extracted_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            logger.info(f"[EXTRACT] Found 'next week' reference, defaulting to next Monday: {extracted_date}")
            has_explicit_date = True
        elif few_days_match:
            # Default to 2 days from now
            extracted_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
            logger.info(f"[EXTRACT] Found 'in a few days' reference, defaulting to: {extracted_date}")
            has_explicit_date = True
    
    # Time extraction with fallbacks
    extracted_time = None
    has_explicit_time = False
    
    if time_match:
        has_explicit_time = True
        hour = time_match.group(1)
        minutes = time_match.group(2) or "00"  # Default to 00 if no minutes
        am_pm = time_match.group(3)
        
        # Default to PM for business hours if not specified
        if not am_pm:
            if int(hour) < 12 and int(hour) >= 1:
                # Business hours assumption - times between 1-6 default to PM, otherwise AM
                am_pm = "PM" if 1 <= int(hour) <= 6 else "AM"
                logger.info(f"[EXTRACT] No AM/PM specified, defaulting to {am_pm} for hour {hour}")
            else:
                am_pm = "AM" if int(hour) < 1 else "PM"
        
        extracted_time = f"{hour}:{minutes} {am_pm or 'PM'}"
        extracted_time = standardize_time(extracted_time)
        logger.info(f"[EXTRACT] Extracted time: {extracted_time}")
    
    # Check for time of day references if no specific time
    if not extracted_time:
        morning_match = re.search(r"\b(?:morning|early|am)\b", transcript, re.IGNORECASE)
        afternoon_match = re.search(r"\b(?:afternoon|lunch|noon)\b", transcript, re.IGNORECASE)
        evening_match = re.search(r"\b(?:evening|night|late)\b", transcript, re.IGNORECASE)
        
        if morning_match:
            extracted_time = "10:00 AM"
            logger.info(f"[EXTRACT] Found 'morning' reference, defaulting to {extracted_time}")
            has_explicit_time = True
        elif afternoon_match:
            extracted_time = "2:00 PM"
            logger.info(f"[EXTRACT] Found 'afternoon' reference, defaulting to {extracted_time}")
            has_explicit_time = True
        elif evening_match:
            extracted_time = "5:00 PM"
            logger.info(f"[EXTRACT] Found 'evening' reference, defaulting to {extracted_time}")
            has_explicit_time = True
    
    # IMPORTANT: Implement fallbacks for missing date/time
    # If we have time specified but no date, default to tomorrow
    if has_explicit_time and not has_explicit_date:
        extracted_date = get_next_business_day()
        logger.info(f"[EXTRACT] No date specified but time found, defaulting to next business day: {extracted_date}")
    
    # If we have a date but no time, default to business hours
    if has_explicit_date and not has_explicit_time:
        extracted_time = "10:00 AM"  # Default to mid-morning
        logger.info(f"[EXTRACT] No time specified but date found, defaulting to business hours: {extracted_time}")
    
    # Last resort: Both date and time missing but transcript suggests appointment OR default to next business day
    if not extracted_date or not extracted_time:
        # Always provide default date and time - CRITICAL FIX
        # The key fix is to make the fallback unconditional if either date OR time is missing
        if not extracted_date:
            extracted_date = get_next_business_day()
            logger.info(f"[EXTRACT] FALLBACK: Using default next business day: {extracted_date}")
            
        if not extracted_time:
            extracted_time = "10:00 AM"
            logger.info(f"[EXTRACT] FALLBACK: Using default business hour: {extracted_time}")
        
        if contains_appointment_intent(transcript):
            logger.info("[EXTRACT] Appointment intent detected, using provided fallbacks")
        else:
            logger.info("[EXTRACT] No clear appointment intent, but still providing date/time defaults")
    
    # Unconditional final verification - CRITICAL FIX
    # If either value is still missing after all fallbacks, force defaults
    if not extracted_date:
        extracted_date = get_next_business_day()
        logger.warning("[EXTRACT] Date still null after fallbacks! Using emergency default.")
        
    if not extracted_time:
        extracted_time = "10:00 AM"
        logger.warning("[EXTRACT] Time still null after fallbacks! Using emergency default.")
    
    logger.info(f"[EXTRACT] Final guaranteed date: {extracted_date}, time: {extracted_time}")
    return extracted_date, extracted_time

def extract_and_validate_appointment_datetime(transcript):
    """Extract, validate and format appointment date and time with guaranteed fallbacks."""
    # Extract date & time with guaranteed fallbacks
    appointment_date, appointment_time = extract_datetime(transcript)
    
    # Double-check we have values (we should always have them with the new extraction function)
    if not appointment_date or not appointment_time:
        logger.error("[VALIDATE] Critical fallback failure! Emergency fallback needed.")
        appointment_date = get_next_business_day()
        appointment_time = "10:00 AM"
    
    # Format date and time for calendar
    try:
        datetime_str = f"{appointment_date} {appointment_time}"
        logger.info(f"[VALIDATE] Parsing datetime: {datetime_str}")
        
        # Try to parse the datetime string
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %I:%M %p")
        formatted_start = dt.strftime("%Y-%m-%dT%H:%M:%S-06:00")  # CST Timezone
        formatted_end = (dt + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S-06:00")
        
        logger.info(f"[VALIDATE] Successfully formatted: {formatted_start} to {formatted_end}")
        return formatted_start, formatted_end, None  # Return formatted times and no error
    except Exception as e:
        # If there's still an error, use hardcoded datetime values
        logger.error(f"[VALIDATE] Date formatting failed: {e}")
        
        # Emergency date/time fallback (tomorrow at 10 AM)
        tomorrow = datetime.utcnow() + timedelta(days=1)
        if tomorrow.weekday() >= 5:  # Weekend, go to Monday
            tomorrow = tomorrow + timedelta(days=(7 - tomorrow.weekday()))
            
        formatted_start = tomorrow.replace(hour=10, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S-06:00")
        formatted_end = tomorrow.replace(hour=10, minute=30, second=0).strftime("%Y-%m-%dT%H:%M:%S-06:00")
        
        logger.info(f"[VALIDATE] Using emergency datetime: {formatted_start} to {formatted_end}")
        return formatted_start, formatted_end, None

@app.post("/api/v1/appointments")
def book_appointment(call_data: dict, db: Session = Depends(get_db)):
    transcript = call_data.get("transcript", "")
    caller = call_data.get("from", "Unknown")
    customer_name = call_data.get("customer_name", "Client")
    
    # Use the enhanced extraction and validation function with guaranteed fallbacks
    formatted_start, formatted_end, error_message = extract_and_validate_appointment_datetime(transcript)
    
    # This should never happen now, but just in case
    if error_message:
        logger.error(f"[BOOK] Unexpected error: {error_message}")
        # Force default values instead of returning error
        tomorrow = datetime.utcnow() + timedelta(days=1)
        if tomorrow.weekday() >= 5:  # Weekend, go to Monday
            tomorrow = tomorrow + timedelta(days=(7 - tomorrow.weekday()))
            
        formatted_start = tomorrow.replace(hour=10, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S-06:00")
        formatted_end = tomorrow.replace(hour=10, minute=30, second=0).strftime("%Y-%m-%dT%H:%M:%S-06:00")
    
    # ULTRA-MINIMAL EVENT FORMAT - The absolute minimum required by Google Calendar API
    return {
        "summary": f"Appointment - {customer_name}",
        "start": {
            "dateTime": formatted_start,
            "timeZone": "America/Chicago"  # Try UTC instead of America/Chicago
        },
        "end": {
            "dateTime": formatted_end,
            "timeZone": "America/Chicago"  # Try UTC instead of America/Chicago
        }
    }
# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)