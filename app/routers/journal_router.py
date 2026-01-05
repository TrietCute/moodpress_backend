from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from app.db.database import get_journal_collection
from app.models.journal import (
    JournalEntryResponse, AnalyzeJournalRequest, AIAnalysis
)
from app.services.ai_service import analyze_journal_content
from app.routers.auth_dependency import get_current_user_id

ID_INVALID_MESSAGE = "ID không hợp lệ"

router = APIRouter(
    prefix="/journal",
    tags=["Journal"],
    dependencies=[Depends(get_current_user_id)]
)
    
@router.post("/new", response_model=JournalEntryResponse)
async def create_new_entry(
    content: str = Form(...),
    emotion: str = Form(...),
    timestamp: datetime = Form(...),
    image_urls: List[str] = Form(default=[]),
    user_id: str = Depends(get_current_user_id)
):

    # 2. Phân tích cảm xúc bằng AI
    analysis_result = await analyze_journal_content(content, emotion, [])
    
    # 3. Tạo dữ liệu lưu vào MongoDB
    new_entry_data = {
        "user_id": user_id,
        "timestamp": timestamp,
        "emotion_selected": emotion,
        "content": content,
        "image_urls": image_urls,
        "analysis": analysis_result.dict()
    }
    collection = get_journal_collection()
    
    result = collection.insert_one(new_entry_data)
    created_entry = collection.find_one({"_id": result.inserted_id})
    return created_entry

@router.get("/history", response_model=List[JournalEntryResponse])
async def get_journal_history(
    year: int = Query(..., description="Năm, ví dụ: 2025"),
    month: int = Query(..., description="Tháng, ví dụ: 11 (là tháng 11)"),
    user_id: str = Depends(get_current_user_id)
):
   
    start_date = datetime(year, month, 1)
    
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    collection = get_journal_collection()
    cursor = collection.find({
        "user_id": user_id,
        "timestamp": {
            "$gte": start_date,
            "$lt": end_date     
        }
    }).sort("timestamp", -1) # Sắp xếp mới nhất lên đầu
    
    return list(cursor)

@router.get("/first-date", response_model=dict)
async def get_first_journal_date(user_id: str = Depends(get_current_user_id)):
    collection = get_journal_collection()
    first_entry = collection.find_one(
        {"user_id": user_id},
        sort=[("timestamp", 1)] # Sắp xếp tăng dần (cũ nhất lên đầu)
    )
    
    if first_entry:
        return {"date": first_entry["timestamp"].date()}
    return {"date": None}

@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_single_entry(
    entry_id: str, 
    user_id: str = Depends(get_current_user_id)
):
    collection = get_journal_collection()
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail=ID_INVALID_MESSAGE)
        
    entry = collection.find_one({
        "_id": ObjectId(entry_id), 
        "user_id": user_id
    })
    
    if entry:
        return entry
    raise HTTPException(status_code=404, detail="Không tìm thấy nhật ký")

@router.put("/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(
    entry_id: str,
    content: Optional[str] = Form(None),
    emotion: Optional[str] = Form(None),
    timestamp: Optional[datetime] = Form(None),
    image_urls: List[str] = Form(default=[]),
    user_id: str = Depends(get_current_user_id)
):
    collection = get_journal_collection()
    
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail="ID không hợp lệ")

    update_data = {}

    if content is not None:
        update_data["content"] = content
        analysis_result = await analyze_journal_content(content, emotion or "Bình thường", [])
        update_data["analysis"] = analysis_result.model_dump()
        
    if emotion is not None:
        update_data["emotion_selected"] = emotion
        
    if timestamp is not None:
        update_data["timestamp"] = timestamp

    update_data["image_urls"] = image_urls

    if not update_data:
        raise HTTPException(status_code=400, detail="Không có thông tin cập nhật")

    updated_entry = collection.find_one_and_update(
        {"_id": ObjectId(entry_id), "user_id": user_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )
    
    if updated_entry:
        return updated_entry
        
    raise HTTPException(status_code=404, detail="Không tìm thấy nhật ký")

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str, 
    user_id: str = Depends(get_current_user_id)
):
    collection = get_journal_collection()
    
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=400, detail=ID_INVALID_MESSAGE)
        
    result = collection.delete_one({
        "_id": ObjectId(entry_id), 
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhật ký")
    
    return None

@router.post("/analyze", response_model=AIAnalysis)
async def analyze_journal_only(
    request: AnalyzeJournalRequest,
    user_id: str = Depends(get_current_user_id)
):
    analysis_result = await analyze_journal_content(
        request.content, 
        request.emotion, 
        []
    )
    
    return analysis_result
