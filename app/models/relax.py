from pydantic import BaseModel, Field
from typing import Optional

class RelaxSound(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    category: str           
    icon_url: str           
    audio_url: str          
    is_premium: bool = False
    is_active: bool = True  
    order_index: int = 0    

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Mưa Rào",
                "category": "NATURE",
                "icon_url": "https://example.com/rain.png",
                "audio_url": "https://example.com/rain.mp3",
                "is_premium": False
            }
        }