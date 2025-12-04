import google.generativeai as genai
import os
import json
import httpx
from PIL import Image
import re
import io
from app.models.journal import AIAnalysis
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

system_instruction = """
    Bạn là MoodPress - một người bạn đồng hành tâm lý ấm áp, thấu hiểu và không phán xét.
    Nhiệm vụ của bạn:
    1. Luôn lắng nghe và xác nhận cảm xúc của người dùng trước khi đưa ra lời khuyên (Validation).
    2. Dùng giọng văn nhẹ nhàng, ân cần, xưng hô là "mình" và "bạn".
    3. Nếu người dùng có dấu hiệu trầm cảm nặng hoặc muốn làm hại bản thân, hãy khuyên họ tìm kiếm sự giúp đỡ chuyên nghiệp ngay lập tức một cách khéo léo.
    4. Câu trả lời ngắn gọn, súc tích, tránh viết quá dài dòng như một bài giảng.
    """
    
# Khởi tạo model
model_json = genai.GenerativeModel('models/gemini-2.5-flash', system_instruction=system_instruction, generation_config={"response_mime_type": "application/json"})
model_text = genai.GenerativeModel('models/gemini-2.5-flash', system_instruction=system_instruction)
def clean_json_string(json_str: str) -> str:
    # Tìm chuỗi bắt đầu bằng { và kết thúc bằng } (kể cả xuống dòng)
    match = re.search(r'\{.*\}', json_str, re.DOTALL)
    if match:
        return match.group(0)
    return json_str.strip()

def get_optimized_image_url(url: str) -> str:
    if "cloudinary.com" in url and "/upload/" in url:
        return url.replace("/upload/", "/upload/w_200/")
    return url

async def analyze_journal_content(content: str, selected_emotion: str, image_urls: list[str] = []) -> AIAnalysis:
    try:
        # Sửa Prompt
        prompt = f"""
        Bạn là một chuyên gia tâm lý. Phân tích nhật ký sau. Người dùng chọn cảm xúc: "{selected_emotion}".
        Nội dung: "{content}"
        
        Yêu cầu:
        1. detected_emotion: Cảm xúc thực sự (Rất tốt/Tốt/Bình thường/Tệ/Rất tệ).
        2. sentiment_score: -1.0 đến 1.0.
        3. is_match: true nếu detected_emotion tương đồng với "{selected_emotion}", ngược lại false.
        4. suggested_emotion: Đề xuất cảm xúc đúng nhất (nếu is_match=false).
        5. advice: Lời khuyên hoặc chia sẻ ngắn gọn (tối đa 1 câu).
        
        Trả về đúng cấu trúc JSON này.
        """
        
        input_parts = [prompt]

        if image_urls:
            async with httpx.AsyncClient() as client:
                for url in image_urls:
                    try:
                        optimized_url = get_optimized_image_url(url)
                        print(f"AI loading image: {optimized_url}")
                        resp = await client.get(optimized_url, timeout=10.0)
                        if resp.status_code == 200:
                            img = Image.open(io.BytesIO(resp.content))
                            input_parts.append(img)
                    except Exception as e:
                        print(f"Lỗi tải ảnh AI: {e}")

        response = model_json.generate_content(input_parts)
        
        raw_text = response.text
        cleaned_text = clean_json_string(raw_text)
        
        data = json.loads(cleaned_text)
        
        return AIAnalysis(
            sentiment_score=data.get("sentiment_score") or 0.0,
            detected_emotion=data.get("detected_emotion") or "Bình thường",
            advice=data.get("advice") or "",
            is_match=data.get("is_match") if data.get("is_match") is not None else True,
            suggested_emotion=data.get("suggested_emotion") or selected_emotion
        )

    except Exception as e:
        print(f"Lỗi AI: {e}")
        return AIAnalysis(sentiment_score=0.0, detected_emotion="Bình thường", advice="")

def chat_with_bot(user_message: str, history: list) -> str:
    try:
        chat = model_text.start_chat(history=history)
        
        system_instruction = (
            "Bạn là người bạn đồng hành thấu hiểu. Hãy trả lời ngắn gọn, ấm áp. "
            "1. Nếu người dùng buồn/tiêu cực: Gợi ý cụ thể tên bài hát (kèm ca sĩ) để xoa dịu. "
            "2. Nếu tiêu cực nặng (tuyệt vọng, hoảng loạn): Hướng dẫn cách bình ổn cảm xúc (như hít thở sâu) hoặc khuyên tìm kiếm chuyên gia tâm lý."
        )
        
        response = chat.send_message(f"{system_instruction}\nUser: {user_message}")
        return response.text
    except Exception:
        return "Xin lỗi, mình đang gặp chút khó khăn khi kết nối. Bạn thử lại sau nhé!"
    
    
