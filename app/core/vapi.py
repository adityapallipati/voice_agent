import httpx
import logging
from typing import Dict, Any, Optional, List
import json
from app.core.config import settings

logger = logging.getLogger(__name__)

class VAPIClient:
    """
    Client for interacting with the VAPI service.
    """
    def __init__(self):
        self.api_key = settings.VAPI_API_KEY
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the VAPI API.
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers, timeout=30.0)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=data, timeout=30.0)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=self.headers, json=data, timeout=30.0)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=self.headers, timeout=30.0)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            try:
                error_data = e.response.json()
                logger.error(f"VAPI error: {error_data}")
            except ValueError:
                error_data = {"detail": str(e)}
            
            raise Exception(f"VAPI API Error: {error_data}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"VAPI Request Error: {str(e)}")
    
    async def get_phone_numbers(self) -> List[Dict[str, Any]]:
        """
        Get all phone numbers associated with the account.
        """
        return await self._make_request("GET", "/v1/phone_numbers")
    
    async def provision_phone_number(self, country: str, area_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Provision a new phone number.
        """
        data = {"country": country}
        if area_code:
            data["area_code"] = area_code
            
        return await self._make_request("POST", "/v1/phone_numbers", data)
    
    async def configure_phone_number(self, phone_number_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure a phone number.
        """
        return await self._make_request("PUT", f"/v1/phone_numbers/{phone_number_id}", config)
    
    async def create_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an outbound call.
        """
        required_keys = ["from", "to", "prompt"]
        for key in required_keys:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key}")
        
        return await self._make_request("POST", "/v1/calls", params)
    
    async def get_call(self, call_id: str) -> Dict[str, Any]:
        """
        Get information about a specific call.
        """
        return await self._make_request("GET", f"/v1/calls/{call_id}")
    
    async def list_calls(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all calls.
        """
        # Add query parameters
        endpoint = f"/v1/calls?limit={limit}&offset={offset}"
        return await self._make_request("GET", endpoint)
    
    async def transfer_call(self, call_id: str, phone_number: str) -> Dict[str, Any]:
        """
        Transfer an ongoing call to another number.
        """
        data = {"phone_number": phone_number}
        return await self._make_request("POST", f"/v1/calls/{call_id}/transfer", data)
    
    async def hangup_call(self, call_id: str) -> Dict[str, Any]:
        """
        Hang up an ongoing call.
        """
        return await self._make_request("POST", f"/v1/calls/{call_id}/hangup")
    
    async def update_call_config(self, call_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the configuration of an ongoing call.
        """
        return await self._make_request("PUT", f"/v1/calls/{call_id}/config", config)