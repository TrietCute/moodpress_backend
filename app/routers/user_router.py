from http.client import HTTPException
import os
from fastapi import APIRouter, Depends
from app.db.database import get_user_collection, get_journal_collection
from app.models.user import UserProfileResponse, UserProfileUpdateRequest
from app.routers.auth_dependency import get_current_user_id
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

class GoogleLinkRequest(BaseModel):
    google_token: str
    
router = APIRouter(
    prefix="/user",
    tags=["User"],
    dependencies=[Depends(get_current_user_id)]
)

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str = Depends(get_current_user_id)):
    user_collection = get_user_collection()
    user = user_collection.find_one({"_id": user_id})
    if user:
        return user
    raise HTTPException(status_code=404, detail="Không tìm thấy user")

@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    request: UserProfileUpdateRequest, 
    user_id: str = Depends(get_current_user_id)
):
    user_collection = get_user_collection()
    update_data = request.dict(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Không có thông tin cập nhật")
    
    updated_user = user_collection.find_one_and_update(
        {"_id": user_id}, 
        {"$set": update_data}, 
        return_document=True 
    )
    
    if updated_user:
        return updated_user
    raise HTTPException(status_code=404, detail="Không tìm thấy user khi đang cập nhật")

@router.post("/link-google")
async def link_google_account(
    request: GoogleLinkRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    user_collection = get_user_collection()
    journal_collection = get_journal_collection()
    try:
        # 1. Xác thực Token với Google
        id_info = id_token.verify_oauth2_token(
            request.google_token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        # 2. Lấy thông tin từ Google
        google_user_id = id_info['sub']
        email = id_info.get('email')
        picture = id_info.get('picture')

        # Nếu ID không thay đổi (đã liên kết rồi), trả về luôn
        if google_user_id == current_user_id:
             return {"message": "Tài khoản đã được liên kết", "new_id": google_user_id}

        current_temp_user = user_collection.find_one({"_id": current_user_id})
        existing_google_user = user_collection.find_one({"_id": google_user_id})

        # 3. CHUYỂN DỮ LIỆU (MIGRATION)
        journal_collection.update_many(
            {"user_id": current_user_id},
            {"$set": {"user_id": google_user_id}}
        )

        # 4. XỬ LÝ USER DOCUMENT
        if existing_google_user:
            update_fields = {}
            
            if current_temp_user:
                if current_temp_user.get("name"):
                    update_fields["name"] = current_temp_user.get("name")
                
                if current_temp_user.get("gender"):
                    update_fields["gender"] = current_temp_user.get("gender")
                    
                if current_temp_user.get("birth"):
                    update_fields["birth"] = current_temp_user.get("birth")
                
                update_fields["picture"] = picture 
                update_fields["email"] = email
            
            user_collection.update_one(
                {"_id": google_user_id},
                {"$set": update_fields}
            )
            
            user_collection.delete_one({"_id": current_user_id})
            
        else:
            if current_temp_user:
                new_user_data = current_temp_user.copy()
                new_user_data["_id"] = google_user_id
                new_user_data["email"] = email
                new_user_data["picture"] = picture
                
                user_collection.insert_one(new_user_data)
                user_collection.delete_one({"_id": current_user_id})
            else:
                user_collection.insert_one({
                    "_id": google_user_id,
                    "email": email,
                    "picture": picture,
                    "name": id_info.get('name')
                })

        return {
            "message": "Liên kết thành công",
            "new_id": google_user_id,
            "email": email
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token Google không hợp lệ: {str(e)}")
    except Exception as e:
        print(f"Lỗi server: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi liên kết tài khoản")