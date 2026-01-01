from fastapi import APIRouter, HTTPException, status
from app.db.database import get_database
from app.models.relax import RelaxSound
from typing import List
from bson import ObjectId

router = APIRouter(
    prefix="/relax",
    tags=["Relax Sounds"]
)

@router.get("/sounds", response_model=List[RelaxSound])
async def get_all_sounds():
    try:
        db = get_database()
        collection = db["relax_sounds"]
        cursor = collection.find({"is_active": True}).sort("order_index", 1)
        
        sounds = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            sounds.append(doc)
            
        return sounds
    except Exception as e:
        print(f"Lỗi lấy danh sách nhạc: {e}")
        return []

@router.post("/admin/add", status_code=status.HTTP_201_CREATED)
async def add_sound(sound: RelaxSound):
    try:
        db = get_database()
        collection = db["relax_sounds"]
        sound_dict = sound.dict(exclude={"id"})
        
        result = collection.insert_one(sound_dict)
        
        return {
            "message": "Thêm âm thanh thành công",
            "id": str(result.inserted_id),
            "name": sound.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")