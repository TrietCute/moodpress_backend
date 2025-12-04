from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

class GoogleLinkRequest(BaseModel):
    google_token: str

class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    birth: Optional[datetime] = None
    
class UserProfileResponse(BaseModel):
    id: str = Field(alias="_id")
    name: Optional[str] = None
    gender: Optional[str] = None
    birth: Optional[datetime] = None
    email: Optional[str] = None
    picture: Optional[str] = None
    
    class Config:
        validate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}