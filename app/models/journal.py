from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, GetCoreSchemaHandler, GetJsonSchemaHandler, ConfigDict
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing import Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        
        # Validator function
        def validate_object_id(v: Any) -> ObjectId:
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid objectid")
            return ObjectId(v)

        # Schema for validation
        from_input_schema = core_schema.no_info_plain_validator_function(validate_object_id)

        return core_schema.json_or_python_schema(
            json_schema=from_input_schema,
            python_schema=core_schema.is_instance_schema(ObjectId),
            serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {'type': 'string'}

# Model cho AI
class AIAnalysis(BaseModel):
    sentiment_score: float
    detected_emotion: str
    advice: str = ""
    is_match: bool = True
    suggested_emotion: str = ""
    
class AnalyzeJournalRequest(BaseModel):
    content: str
    emotion: str
    image_urls: List[str] = []

# Model cho dữ liệu TRẢ VỀ (Response)
class JournalEntryResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    timestamp: datetime
    emotion_selected: str
    content: str
    image_urls: List[str] = []
    analysis: Optional[AIAnalysis] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

# Model cho dữ liệu ĐẦU VÀO (Tạo mới)
class NewEntryRequest(BaseModel):
    content: str
    emotion: str
    timestamp: datetime

# Model cho dữ liệu ĐẦU VÀO (Cập nhật)
class UpdateEntryRequest(BaseModel):
    content: Optional[str] = None
    emotion: Optional[str] = None
    timestamp: Optional[datetime] = None