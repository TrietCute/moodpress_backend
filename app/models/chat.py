from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.models.journal import PyObjectId
from bson import ObjectId

class ChatMessage(BaseModel):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: str
    sender: str  
    message: str
    timestamp: datetime
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class ChatRequest(BaseModel):
    message: str
    history: list = []