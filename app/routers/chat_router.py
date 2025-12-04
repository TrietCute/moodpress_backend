from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime
from app.db.database import get_database
from app.models.chat import ChatMessage, ChatRequest
from app.routers.auth_dependency import get_current_user_id
from app.services.ai_service import chat_with_bot

router = APIRouter(
    prefix="/chat",
    tags=["Chatbot"],
    dependencies=[Depends(get_current_user_id)]
)

# Lấy collection chat_messages


@router.post("/send", response_model=ChatMessage)
async def send_message(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    chat_collection = get_database()["chat_messages"]
    cursor = chat_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(10)
    history_docs = list(cursor)[::-1] 

    history_gemini = []
    for doc in history_docs:
        role = "user" if doc["sender"] == "user" else "model"
        msg_content = doc.get("message") or "" 
        if msg_content:
            history_gemini.append({"role": role, "parts": [msg_content]})

    try:
        bot_reply_text = chat_with_bot(request.message, history_gemini)
    except Exception as e:
        print(f"Lỗi gọi AI: {e}")

        bot_reply_text = "Xin lỗi, hệ thống đang bận. Bạn thử lại sau nhé!"

    user_msg = ChatMessage(
        user_id=user_id, 
        sender="user", 
        message=request.message, 
        timestamp=datetime.now()
    )
    chat_collection.insert_one(user_msg.dict(by_alias=True, exclude={"id"}))

    bot_msg = ChatMessage(
        user_id=user_id, 
        sender="bot", 
        message=bot_reply_text, 
        timestamp=datetime.now()
    )
    result = chat_collection.insert_one(bot_msg.dict(by_alias=True, exclude={"id"}))
    
    bot_msg.id = result.inserted_id
    return bot_msg

@router.delete("/history")
async def clear_chat_history(user_id: str = Depends(get_current_user_id)):
    chat_collection = get_database()["chat_messages"]
    try:
        result = chat_collection.delete_many({"user_id": user_id})
        return {
            "message": "Đã xóa lịch sử chat thành công", 
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        print(f"Lỗi xóa history: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi xóa lịch sử chat")