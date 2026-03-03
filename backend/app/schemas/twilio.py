"""
Pydantic schemas for Twilio webhook requests and responses.
"""
from typing import Optional
from pydantic import BaseModel, Field


class TwilioInboundCall(BaseModel):
    """Schema for Twilio inbound call webhook."""
    
    CallSid: str = Field(..., description="Unique identifier for the call")
    AccountSid: str = Field(..., description="Twilio account SID")
    From: str = Field(..., description="Caller's phone number")
    To: str = Field(..., description="Called phone number (your Twilio number)")
    CallStatus: str = Field(..., description="Status of the call")
    Direction: str = Field(..., description="Direction of the call (inbound/outbound)")
    FromCity: Optional[str] = Field(None, description="Caller's city")
    FromState: Optional[str] = Field(None, description="Caller's state")
    FromZip: Optional[str] = Field(None, description="Caller's ZIP code")
    FromCountry: Optional[str] = Field(None, description="Caller's country")
    
    class Config:
        json_schema_extra = {
            "example": {
                "CallSid": "CA1234567890abcdef1234567890abcdef",
                "AccountSid": "AC1234567890abcdef1234567890abcdef",
                "From": "+15551234567",
                "To": "+15559876543",
                "CallStatus": "ringing",
                "Direction": "inbound",
                "FromCity": "NEW YORK",
                "FromState": "NY",
                "FromZip": "10001",
                "FromCountry": "US"
            }
        }


class TwilioCallStatus(BaseModel):
    """Schema for Twilio call status callback."""
    
    CallSid: str = Field(..., description="Unique identifier for the call")
    CallStatus: str = Field(..., description="Current status of the call")
    CallDuration: Optional[str] = Field(None, description="Duration of the call in seconds")
    RecordingUrl: Optional[str] = Field(None, description="URL of the call recording")
    RecordingSid: Optional[str] = Field(None, description="SID of the recording")
    RecordingDuration: Optional[str] = Field(None, description="Duration of the recording")
    
    class Config:
        json_schema_extra = {
            "example": {
                "CallSid": "CA1234567890abcdef1234567890abcdef",
                "CallStatus": "completed",
                "CallDuration": "45",
                "RecordingUrl": "https://api.twilio.com/recordings/RE123",
                "RecordingSid": "RE1234567890abcdef1234567890abcdef",
                "RecordingDuration": "42"
            }
        }


class TwiMLResponse(BaseModel):
    """Schema for TwiML response."""
    
    twiml: str = Field(..., description="TwiML XML response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "twiml": '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Hello</Say></Response>'
            }
        }

