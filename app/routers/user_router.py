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
        name = id_info.get('name')
        picture = id_info.get('picture')

        # Nếu ID không thay đổi (đã liên kết rồi), trả về luôn
        if google_user_id == current_user_id:
             return {"message": "Tài khoản đã được liên kết", "new_id": google_user_id}

        # 3. CHUYỂN DỮ LIỆU (MIGRATION)
        # Cập nhật tất cả nhật ký: đổi user_id từ UUID -> Google ID
        journal_collection.update_many(
            {"user_id": current_user_id},
            {"$set": {"user_id": google_user_id}}
        )

        # 4. XỬ LÝ USER DOCUMENT
        # Kiểm tra xem tài khoản Google này đã tồn tại trong DB chưa
        existing_google_user = user_collection.find_one({"_id": google_user_id})

        if existing_google_user:
            # A. Nếu đã có tài khoản Google:
            # Ta chỉ cần cập nhật thêm thông tin mới (nếu thiếu)
            # và xóa tài khoản UUID tạm thời đi.
            user_collection.delete_one({"_id": current_user_id})
            
            # (Tùy chọn: Cập nhật avatar/email mới nhất từ Google)
            user_collection.update_one(
                {"_id": google_user_id},
                {"$set": {"email": email, "picture": picture}}
            )
            
        else:
            # B. Nếu chưa có tài khoản Google:
            # Lấy thông tin từ tài khoản UUID cũ
            old_user_data = user_collection.find_one({"_id": current_user_id})
            
            if old_user_data:
                # Tạo document mới với _id là Google ID
                new_user_data = old_user_data.copy()
                new_user_data["_id"] = google_user_id
                new_user_data["email"] = email
                new_user_data["picture"] = picture
                # Ưu tiên tên từ Google nếu chưa đặt tên
                if not new_user_data.get("name"):
                    new_user_data["name"] = name
                
                # Lưu user mới và xóa user cũ
                user_collection.insert_one(new_user_data)
                user_collection.delete_one({"_id": current_user_id})
            else:
                # Trường hợp hiếm: UUID không tồn tại (lỗi), tạo mới luôn
                user_collection.insert_one({
                    "_id": google_user_id,
                    "email": email,
                    "name": name,
                    "picture": picture
                })

        # 5. Trả về ID mới cho Client để lưu vào SessionManager
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