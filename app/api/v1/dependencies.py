from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.db.session import get_db
from app.config import settings

# Security scheme for bearer token authentication
security = HTTPBearer()
logger = logging.getLogger(__name__)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get the current user based on the provided bearer token.
    
    This is a simplified authentication dependency that validates a JWT token.
    In a full implementation, you would likely check the token against a user database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify the token
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Extract user ID from payload
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Return the user information
        return {"id": user_id, "role": payload.get("role", "user")}
        
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception

async def get_optional_current_user(
    token: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """
    Get the current user if authenticated, otherwise return None.
    
    This is useful for endpoints that work both with authenticated and anonymous users.
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None

async def check_admin_privileges(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Check if the current user has admin privileges.
    
    Use this dependency for endpoints that require admin access.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user

# Rate limiting dependency (simplified example)
async def check_rate_limit(client_ip: str) -> None:
    """
    Check if the client has exceeded the rate limit.
    
    This is a simplified example. In a real implementation, you would use
    a library like slowapi or implement rate limiting with Redis.
    """
    # Implement actual rate limiting logic here
    pass