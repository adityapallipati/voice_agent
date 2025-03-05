import httpx
import logging
from typing import Dict, Any, Optional, List
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseCRMClient(ABC):
    """
    Abstract base class for CRM client implementations.
    """
    
    @abstractmethod
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer details by customer ID."""
        pass
    
    @abstractmethod
    async def find_customer_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find a customer by phone number."""
        pass
    
    @abstractmethod
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer."""
        pass
    
    @abstractmethod
    async def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing customer."""
        pass
    
    @abstractmethod
    async def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new activity or interaction."""
        pass
    
    @abstractmethod
    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment."""
        pass
    
    @abstractmethod
    async def update_appointment(self, appointment_id: str, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing appointment."""
        pass
    
    @abstractmethod
    async def get_appointments(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a customer."""
        pass

class NoCRMClient(BaseCRMClient):
    """
    Null implementation of CRM client for when no CRM is configured.
    """
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"NoCRMClient: get_customer called with ID {customer_id}")
        return None
    
    async def find_customer_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"NoCRMClient: find_customer_by_phone called with number {phone_number}")
        return None
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"NoCRMClient: create_customer called with data {customer_data}")
        return {"id": "local-" + customer_data.get("phone_number", "unknown"), **customer_data}
    
    async def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"NoCRMClient: update_customer called for ID {customer_id}")
        return {"id": customer_id, **customer_data}
    
    async def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"NoCRMClient: create_activity called with data {activity_data}")
        return {"id": "local-activity", **activity_data}
    
    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"NoCRMClient: create_appointment called with data {appointment_data}")
        return {"id": "local-appointment", **appointment_data}
    
    async def update_appointment(self, appointment_id: str, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"NoCRMClient: update_appointment called for ID {appointment_id}")
        return {"id": appointment_id, **appointment_data}
    
    async def get_appointments(self, customer_id: str) -> List[Dict[str, Any]]:
        logger.debug(f"NoCRMClient: get_appointments called for customer ID {customer_id}")
        return []

class SalesforceCRMClient(BaseCRMClient):
    """
    Salesforce CRM client implementation.
    """
    
    def __init__(self):
        self.base_url = settings.CRM_API_URL
        self.api_key = settings.CRM_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError))
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the Salesforce API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(
                        url, 
                        headers=self.headers, 
                        params=params, 
                        timeout=30.0
                    )
                elif method.upper() == "POST":
                    response = await client.post(
                        url, 
                        headers=self.headers, 
                        json=data, 
                        params=params,
                        timeout=30.0
                    )
                elif method.upper() == "PATCH":
                    response = await client.patch(
                        url, 
                        headers=self.headers, 
                        json=data, 
                        params=params,
                        timeout=30.0
                    )
                elif method.upper() == "DELETE":
                    response = await client.delete(
                        url, 
                        headers=self.headers, 
                        params=params,
                        timeout=30.0
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Salesforce API HTTP error: {e}")
            try:
                error_data = e.response.json()
                logger.error(f"Salesforce error details: {error_data}")
            except ValueError:
                error_data = {"detail": str(e)}
            
            raise Exception(f"Salesforce API Error: {error_data}")
        except httpx.RequestError as e:
            logger.error(f"Salesforce API request error: {e}")
            raise Exception(f"Salesforce Request Error: {str(e)}")
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer details by customer ID."""
        try:
            return await self._make_request("GET", f"/services/data/v57.0/sobjects/Contact/{customer_id}")
        except Exception as e:
            logger.error(f"Error getting customer from Salesforce: {e}")
            return None
    
    async def find_customer_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find a customer by phone number."""
        try:
            # Use SOQL query to find contact by phone
            query = f"SELECT Id, FirstName, LastName, Phone, Email FROM Contact WHERE Phone = '{phone_number}' LIMIT 1"
            params = {"q": query}
            
            result = await self._make_request("GET", "/services/data/v57.0/query", params=params)
            
            if result.get("records") and len(result["records"]) > 0:
                return result["records"][0]
            return None
        except Exception as e:
            logger.error(f"Error finding customer by phone in Salesforce: {e}")
            return None
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer in Salesforce."""
        # Transform customer data to Salesforce Contact format
        contact_data = {
            "FirstName": customer_data.get("first_name", ""),
            "LastName": customer_data.get("last_name", "Unknown"),
            "Phone": customer_data.get("phone_number", ""),
            "Email": customer_data.get("email", ""),
            # Map other fields as needed
        }
        
        return await self._make_request("POST", "/services/data/v57.0/sobjects/Contact", data=contact_data)
    
    async def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing customer in Salesforce."""
        # Transform customer data to Salesforce Contact format
        contact_data = {
            "FirstName": customer_data.get("first_name"),
            "LastName": customer_data.get("last_name"),
            "Phone": customer_data.get("phone_number"),
            "Email": customer_data.get("email"),
            # Map other fields as needed
        }
        
        # Remove None values
        contact_data = {k: v for k, v in contact_data.items() if v is not None}
        
        await self._make_request("PATCH", f"/services/data/v57.0/sobjects/Contact/{customer_id}", data=contact_data)
        
        # Return the updated customer
        return await self.get_customer(customer_id)
    
    async def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new activity or interaction in Salesforce."""
        # Transform activity data to Salesforce Task format
        task_data = {
            "Subject": activity_data.get("subject", "Voice Agent Interaction"),
            "Description": activity_data.get("description", ""),
            "WhoId": activity_data.get("customer_id"),  # Contact ID
            "Status": "Completed",
            "Priority": "Normal",
            "Type": activity_data.get("type", "Call"),
            # Map other fields as needed
        }
        
        return await self._make_request("POST", "/services/data/v57.0/sobjects/Task", data=task_data)
    
    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment in Salesforce."""
        # Transform appointment data to Salesforce Event format
        event_data = {
            "Subject": appointment_data.get("service_type", "Appointment"),
            "Description": appointment_data.get("notes", ""),
            "WhoId": appointment_data.get("customer_id"),  # Contact ID
            "StartDateTime": appointment_data.get("appointment_time"),
            "EndDateTime": appointment_data.get("end_time"),  # Calculate based on duration
            "Location": appointment_data.get("location", ""),
            # Map other fields as needed
        }
        
        return await self._make_request("POST", "/services/data/v57.0/sobjects/Event", data=event_data)
    
    async def update_appointment(self, appointment_id: str, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing appointment in Salesforce."""
        # Transform appointment data to Salesforce Event format
        event_data = {
            "Subject": appointment_data.get("service_type"),
            "Description": appointment_data.get("notes"),
            "StartDateTime": appointment_data.get("appointment_time"),
            "EndDateTime": appointment_data.get("end_time"),
            "Location": appointment_data.get("location"),
            # Map other fields as needed
        }
        
        # Remove None values
        event_data = {k: v for k, v in event_data.items() if v is not None}
        
        await self._make_request("PATCH", f"/services/data/v57.0/sobjects/Event/{appointment_id}", data=event_data)
        
        # Get updated event
        try:
            return await self._make_request("GET", f"/services/data/v57.0/sobjects/Event/{appointment_id}")
        except Exception:
            return {"id": appointment_id, **appointment_data}
    
    async def get_appointments(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a customer from Salesforce."""
        try:
            # Use SOQL query to find events for the contact
            query = f"SELECT Id, Subject, StartDateTime, EndDateTime, Location, Description FROM Event WHERE WhoId = '{customer_id}'"
            params = {"q": query}
            
            result = await self._make_request("GET", "/services/data/v57.0/query", params=params)
            
            return result.get("records", [])
        except Exception as e:
            logger.error(f"Error getting appointments from Salesforce: {e}")
            return []

class HubspotCRMClient(BaseCRMClient):
    """
    HubSpot CRM client implementation.
    """
    
    def __init__(self):
        self.base_url = "https://api.hubapi.com"
        self.api_key = settings.CRM_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError))
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the HubSpot API."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(
                        url, 
                        headers=self.headers, 
                        params=params, 
                        timeout=30.0
                    )
                elif method.upper() == "POST":
                    response = await client.post(
                        url, 
                        headers=self.headers, 
                        json=data, 
                        params=params,
                        timeout=30.0
                    )
                elif method.upper() == "PATCH":
                    response = await client.patch(
                        url, 
                        headers=self.headers, 
                        json=data, 
                        params=params,
                        timeout=30.0
                    )
                elif method.upper() == "DELETE":
                    response = await client.delete(
                        url, 
                        headers=self.headers, 
                        params=params,
                        timeout=30.0
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot API HTTP error: {e}")
            try:
                error_data = e.response.json()
                logger.error(f"HubSpot error details: {error_data}")
            except ValueError:
                error_data = {"detail": str(e)}
            
            raise Exception(f"HubSpot API Error: {error_data}")
        except httpx.RequestError as e:
            logger.error(f"HubSpot API request error: {e}")
            raise Exception(f"HubSpot Request Error: {str(e)}")
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer details by customer ID from HubSpot."""
        try:
            return await self._make_request("GET", f"/crm/v3/objects/contacts/{customer_id}")
        except Exception as e:
            logger.error(f"Error getting customer from HubSpot: {e}")
            return None
    
    async def find_customer_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find a customer by phone number in HubSpot."""
        try:
            # Use HubSpot search API
            filter_data = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "phone",
                                "operator": "EQ",
                                "value": phone_number
                            }
                        ]
                    }
                ],
                "limit": 1
            }
            
            result = await self._make_request("POST", "/crm/v3/objects/contacts/search", data=filter_data)
            
            if result.get("results") and len(result["results"]) > 0:
                return result["results"][0]
            return None
        except Exception as e:
            logger.error(f"Error finding customer by phone in HubSpot: {e}")
            return None
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer in HubSpot."""
        # Transform customer data to HubSpot Contact format
        contact_data = {
            "properties": {
                "firstname": customer_data.get("first_name", ""),
                "lastname": customer_data.get("last_name", "Unknown"),
                "phone": customer_data.get("phone_number", ""),
                "email": customer_data.get("email", ""),
                # Map other fields as needed
            }
        }
        
        return await self._make_request("POST", "/crm/v3/objects/contacts", data=contact_data)
    
    async def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing customer in HubSpot."""
        # Transform customer data to HubSpot Contact format
        properties = {}
        if customer_data.get("first_name") is not None:
            properties["firstname"] = customer_data["first_name"]
        if customer_data.get("last_name") is not None:
            properties["lastname"] = customer_data["last_name"]
        if customer_data.get("phone_number") is not None:
            properties["phone"] = customer_data["phone_number"]
        if customer_data.get("email") is not None:
            properties["email"] = customer_data["email"]
        # Map other fields as needed
        
        contact_data = {"properties": properties}
        
        await self._make_request("PATCH", f"/crm/v3/objects/contacts/{customer_id}", data=contact_data)
        
        # Return the updated customer
        return await self.get_customer(customer_id)
    
    async def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new activity or interaction in HubSpot."""
        # In HubSpot, we'll use engagements (now called CRM activities)
        engagement_data = {
            "properties": {
                "hs_timestamp": str(int(activity_data.get("timestamp", 0))),
                "hs_call_title": activity_data.get("subject", "Voice Agent Interaction"),
                "hs_call_body": activity_data.get("description", ""),
                "hs_call_direction": "INBOUND",
                "hs_call_disposition": activity_data.get("outcome", ""),
                "hs_call_duration": str(activity_data.get("duration", 0)),
                # Map other fields as needed
            },
            "associations": [
                {
                    "to": {"id": activity_data.get("customer_id")},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 1}
                    ]
                }
            ]
        }
        
        return await self._make_request("POST", "/crm/v3/objects/calls", data=engagement_data)
    
    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment in HubSpot."""
        # In HubSpot, we'll use meetings
        meeting_data = {
            "properties": {
                "hs_timestamp": appointment_data.get("appointment_time"),
                "hs_meeting_title": appointment_data.get("service_type", "Appointment"),
                "hs_meeting_body": appointment_data.get("notes", ""),
                "hs_meeting_location": appointment_data.get("location", ""),
                "hs_meeting_end_time": appointment_data.get("end_time"),
                # Map other fields as needed
            },
            "associations": [
                {
                    "to": {"id": appointment_data.get("customer_id")},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 1}
                    ]
                }
            ]
        }
        
        return await self._make_request("POST", "/crm/v3/objects/meetings", data=meeting_data)
    
    async def update_appointment(self, appointment_id: str, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing appointment in HubSpot."""
        # Prepare the properties to update
        properties = {}
        if appointment_data.get("appointment_time") is not None:
            properties["hs_timestamp"] = appointment_data["appointment_time"]
        if appointment_data.get("service_type") is not None:
            properties["hs_meeting_title"] = appointment_data["service_type"]
        if appointment_data.get("notes") is not None:
            properties["hs_meeting_body"] = appointment_data["notes"]
        if appointment_data.get("location") is not None:
            properties["hs_meeting_location"] = appointment_data["location"]
        if appointment_data.get("end_time") is not None:
            properties["hs_meeting_end_time"] = appointment_data["end_time"]
        # Map other fields as needed
        
        meeting_data = {"properties": properties}
        
        await self._make_request("PATCH", f"/crm/v3/objects/meetings/{appointment_id}", data=meeting_data)
        
        # Return the updated meeting
        try:
            return await self._make_request("GET", f"/crm/v3/objects/meetings/{appointment_id}")
        except Exception:
            return {"id": appointment_id, **appointment_data}
    
    async def get_appointments(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get appointments for a customer from HubSpot."""
        try:
            # Use associations API to get meetings for the contact
            result = await self._make_request(
                "GET", 
                f"/crm/v3/objects/contacts/{customer_id}/associations/meetings",
            )
            
            meetings = []
            for association in result.get("results", []):
                meeting_id = association.get("id")
                if meeting_id:
                    try:
                        meeting = await self._make_request("GET", f"/crm/v3/objects/meetings/{meeting_id}")
                        meetings.append(meeting)
                    except Exception as e:
                        logger.error(f"Error getting meeting {meeting_id}: {e}")
            
            return meetings
        except Exception as e:
            logger.error(f"Error getting appointments from HubSpot: {e}")
            return []

# CRM factory to get the appropriate client based on configuration
def get_crm_client() -> BaseCRMClient:
    """
    Factory function to get the appropriate CRM client based on configuration.
    """
    crm_type = settings.CRM_TYPE.lower()
    
    if crm_type == "salesforce":
        return SalesforceCRMClient()
    elif crm_type == "hubspot":
        return HubspotCRMClient()
    else:
        return NoCRMClient()