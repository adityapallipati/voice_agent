import re
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, time, timedelta
import uuid
import phonenumbers

logger = logging.getLogger(__name__)

def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """Generate a short random ID."""
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:length]

def parse_iso_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parse an ISO format datetime string into a datetime object.
    Returns None if parsing fails.
    """
    try:
        return datetime.fromisoformat(datetime_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing datetime {datetime_str}: {e}")
        return None

def format_iso_datetime(dt: datetime) -> str:
    """Format a datetime object as an ISO format string."""
    return dt.isoformat()

def format_phone_number(phone_number: str, region: str = "US") -> str:
    """
    Format a phone number according to the E.164 standard.
    If parsing fails, returns the original string.
    """
    try:
        parsed_number = phonenumbers.parse(phone_number, region)
        if phonenumbers.is_valid_number(parsed_number):
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        return phone_number
    except Exception as e:
        logger.error(f"Error formatting phone number {phone_number}: {e}")
        return phone_number

def is_valid_phone_number(phone_number: str, region: str = "US") -> bool:
    """Check if a phone number is valid."""
    try:
        parsed_number = phonenumbers.parse(phone_number, region)
        return phonenumbers.is_valid_number(parsed_number)
    except Exception:
        return False

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from text that might have additional content.
    Returns None if no valid JSON is found.
    """
    # Try to find JSON pattern
    json_pattern = r'({[\s\S]*?})'
    matches = re.findall(json_pattern, text)
    
    if not matches:
        return None
    
    # Try each match
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries, with dict2 taking precedence.
    This is a deep merge that handles nested dictionaries.
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def time_slot_to_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """
    Convert a date string and time string to a datetime object.
    Example: '2023-04-15', '14:30' -> datetime(2023, 4, 15, 14, 30)
    """
    try:
        date_part = datetime.strptime(date_str, "%Y-%m-%d").date()
        time_parts = time_str.split(":")
        
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        return datetime.combine(date_part, time(hour, minute))
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting time slot {date_str} {time_str} to datetime: {e}")
        return None

def get_time_range_for_day(target_date: Union[str, datetime]) -> Tuple[datetime, datetime]:
    """
    Get the start and end datetime for a specific day.
    """
    if isinstance(target_date, str):
        date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    elif isinstance(target_date, datetime):
        date_obj = target_date.date()
    else:
        raise ValueError("target_date must be a string or datetime")
    
    start_of_day = datetime.combine(date_obj, time(0, 0, 0))
    end_of_day = datetime.combine(date_obj, time(23, 59, 59))
    
    return start_of_day, end_of_day

def get_date_range(start_date: Union[str, datetime], days: int) -> List[str]:
    """
    Get a list of date strings for a range of days.
    Example: '2023-04-15', 3 -> ['2023-04-15', '2023-04-16', '2023-04-17']
    """
    if isinstance(start_date, str):
        date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    elif isinstance(start_date, datetime):
        date_obj = start_date.date()
    else:
        raise ValueError("start_date must be a string or datetime")
    
    date_list = []
    for i in range(days):
        date_list.append((date_obj + timedelta(days=i)).isoformat())
    
    return date_list

def truncate_text(text: str, max_length: int = 100, ellipsis: str = "...") -> str:
    """
    Truncate text to a maximum length, adding ellipsis if needed.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(ellipsis)] + ellipsis

def parse_duration_string(duration_str: str) -> Optional[int]:
    """
    Parse a duration string into minutes.
    Examples: '1 hour', '30 minutes', '1.5 hours' -> 60, 30, 90
    """
    try:
        # Check for hours and minutes pattern
        hours_minutes_pattern = r'(\d+)\s*hour(?:s)?\s*(?:and)?\s*(\d+)\s*minute(?:s)?'
        match = re.match(hours_minutes_pattern, duration_str, re.IGNORECASE)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return hours * 60 + minutes
        
        # Check for decimal hours pattern
        decimal_hours_pattern = r'(\d+(?:\.\d+)?)\s*hour(?:s)?'
        match = re.match(decimal_hours_pattern, duration_str, re.IGNORECASE)
        if match:
            hours = float(match.group(1))
            return int(hours * 60)
        
        # Check for minutes pattern
        minutes_pattern = r'(\d+)\s*minute(?:s)?'
        match = re.match(minutes_pattern, duration_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Try parsing as just a number (assuming minutes)
        if duration_str.isdigit():
            return int(duration_str)
        
        return None
    except Exception as e:
        logger.error(f"Error parsing duration {duration_str}: {e}")
        return None

def sanitize_input(text: str) -> str:
    """
    Sanitize input text to prevent injection attacks.
    Removes HTML tags and other potentially dangerous content.
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove SQL injection patterns
    text = re.sub(r'(--|\bOR\b|\bAND\b|\bUNION\b|\bSELECT\b|\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b)', 
                  lambda match: match.group(0).lower(), text, flags=re.IGNORECASE)
    
    return text

def extract_entity_mentions(text: str, entity_type: str, values: List[str]) -> List[str]:
    """
    Extract mentions of entities from text.
    Example: extract_entity_mentions("I want to book a haircut", "service", ["haircut", "color", "styling"])
    -> ["haircut"]
    """
    found_entities = []
    text_lower = text.lower()
    
    for value in values:
        if value.lower() in text_lower:
            found_entities.append(value)
    
    return found_entities

def calculate_edit_distance(str1: str, str2: str) -> int:
    """
    Calculate the Levenshtein edit distance between two strings.
    Useful for fuzzy matching of entity values.
    """
    m, n = len(str1), len(str2)
    dp = [[0 for _ in range(n + 1)] for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    
    return dp[m][n]

def fuzzy_match(input_str: str, candidates: List[str], threshold: float = 0.8) -> Optional[str]:
    """
    Find the best fuzzy match from a list of candidates.
    Returns None if no match exceeds the threshold.
    """
    best_match = None
    best_score = 0
    
    input_lower = input_str.lower()
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        
        # Calculate similarity as 1 - (edit_distance / max_length)
        edit_dist = calculate_edit_distance(input_lower, candidate_lower)
        max_length = max(len(input_lower), len(candidate_lower))
        similarity = 1 - (edit_dist / max_length if max_length > 0 else 0)
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = candidate
    
    return best_match

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to ensure it's safe for filesystem operations.
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    # Ensure the filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    return sanitized

def mask_pii(text: str) -> str:
    """
    Mask personally identifiable information (PII) in text.
    This is a simplified implementation that masks common PII patterns.
    """
    # Mask email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL]', text)
    
    # Mask phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Mask credit card numbers
    text = re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[CREDIT_CARD]', text)
    
    # Mask SSNs
    text = re.sub(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', '[SSN]', text)
    
    return text