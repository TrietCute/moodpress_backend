from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Tuple

from app.db.database import get_journal_collection
from app.models.stat import WeeklyStatsResponse, MoodCountStat, DailyMoodData
from app.routers.auth_dependency import get_current_user_id

router = APIRouter(
    prefix="/stats",
    tags=["Statistics"],
    dependencies=[Depends(get_current_user_id)]
)


EMOTION_SCORES = {
    "Rất tốt": 5, 
    "Tốt": 4, 
    "Bình thường": 3, 
    "Tệ": 2, 
    "Rất tệ": 1
}

# ==========================================
# API ENDPOINTS
# ==========================================

@router.get("/weekly", response_model=WeeklyStatsResponse)
async def get_weekly_stats(
    start_date: date = Query(..., description="Ngày bắt đầu tuần (Thứ 2)"),
    timezone_offset: int = Query(0, description="Độ lệch múi giờ của client (phút)"),
    user_id: str = Depends(get_current_user_id)
):
    end_date = start_date + timedelta(days=6)
    
    query_start = datetime.combine(start_date - timedelta(days=1), datetime.min.time())
    query_end = datetime.combine(end_date + timedelta(days=1), datetime.max.time())

    collection = get_journal_collection()
    cursor = collection.find({
        "user_id": user_id,
        "timestamp": {"$gte": query_start, "$lte": query_end}
    }).sort("timestamp", 1) 
    
    raw_entries = list(cursor)

    # --- SỬA 1: Bỏ tham số timezone_offset ---
    mood_stats, active_days, daily_moods, valid_count = process_mood_data(
        raw_entries, start_date, end_date
    )

    total_entries = collection.count_documents({"user_id": user_id})
    
    # (Lưu ý: calculate_streaks VẪN CẦN timezone_offset để tính 'Hôm nay')
    current_streak, longest_streak = calculate_streaks(user_id, timezone_offset)

    return WeeklyStatsResponse(
        mood_counts=mood_stats,
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_entries=valid_count,
        all_time_total=total_entries, 
        active_days_in_week=active_days,
        daily_moods=daily_moods
    )

@router.get("/monthly", response_model=WeeklyStatsResponse)
async def get_monthly_stats(
    start_date: date = Query(..., description="Ngày bắt đầu"),
    end_date: date = Query(..., description="Ngày kết thúc"),
    timezone_offset: int = Query(0, description="Độ lệch phút"),
    user_id: str = Depends(get_current_user_id)
):
    query_start = datetime.combine(start_date - timedelta(days=1), datetime.min.time())
    query_end = datetime.combine(end_date + timedelta(days=1), datetime.max.time())

    collection = get_journal_collection()
    cursor = collection.find({
        "user_id": user_id,
        "timestamp": {"$gte": query_start, "$lte": query_end}
    }).sort("timestamp", 1)
    
    raw_entries = list(cursor)

    # --- SỬA 2: Bỏ tham số timezone_offset ---
    mood_stats, active_days, daily_moods, valid_count = process_mood_data(
        raw_entries, start_date, end_date
    )

    current_streak, longest_streak = calculate_streaks(user_id, timezone_offset)
    total_entries = collection.count_documents({"user_id": user_id})

    return WeeklyStatsResponse(
        mood_counts=mood_stats,
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_entries=valid_count,
        all_time_total=total_entries,
        active_days_in_week=active_days,
        daily_moods=daily_moods
    )


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def process_mood_data(
    entries: List[dict], 
    start_date: date, 
    end_date: date
    # --- SỬA 3: Xóa tham số timezone_offset khỏi đây ---
) -> Tuple[List[MoodCountStat], List[bool], List[DailyMoodData], int]:
    
    entries.sort(key=lambda x: x["timestamp"])

    total_days = (end_date - start_date).days + 1
    active_days = [False] * total_days
    daily_mood_map = {}
    mood_counter = {}
    
    valid_entries_count = 0

    for entry in entries:
        # Giữ nguyên logic lấy giờ UTC (không cộng offset)
        utc_ts = entry["timestamp"]
        local_date = utc_ts.date()
        
        delta_days = (local_date - start_date).days
        
        if 0 <= delta_days < total_days:
            valid_entries_count += 1
            emotion = entry.get("emotion_selected", "Bình thường")
            
            active_days[delta_days] = True
            
            daily_mood_map[delta_days] = {
                "date": local_date,
                "emotion": emotion,
                "score": EMOTION_SCORES.get(emotion, 3)
            }
            
            if emotion in mood_counter:
                mood_counter[emotion] += 1
            else:
                mood_counter[emotion] = 1

    daily_moods_list = []
    for i in range(total_days):
        if i in daily_mood_map:
            daily_moods_list.append(DailyMoodData(**daily_mood_map[i]))

    mood_stats = []
    if valid_entries_count > 0:
        for emotion, count in mood_counter.items():
            percentage = round((count / valid_entries_count) * 100, 1)
            mood_stats.append(MoodCountStat(
                emotion=emotion,
                count=count,
                percentage=percentage
            ))
    mood_stats.sort(key=lambda x: x.count, reverse=True)

    return mood_stats, active_days, daily_moods_list, valid_entries_count


def calculate_streaks(user_id: str, timezone_offset: int) -> Tuple[int, int]:
    # (Hàm này GIỮ NGUYÊN, vẫn cần timezone_offset để tính 'Hôm nay' là ngày mấy)
    collection = get_journal_collection()
    cursor = collection.find(
        {"user_id": user_id},
        {"timestamp": 1, "_id": 0}
    ).sort("timestamp", 1)

    local_dates_set = set()
    for doc in cursor:
        # Giữ nguyên logic không cộng giờ cho dữ liệu
        local_ts = doc["timestamp"]
        local_dates_set.add(local_ts.date())

    sorted_dates = sorted(local_dates_set)

    if not sorted_dates:
        return 0, 0

    # 1. Longest Streak
    longest_streak = 1
    current_run = 1
    for i in range(1, len(sorted_dates)):
        delta = (sorted_dates[i] - sorted_dates[i - 1]).days
        if delta == 1:
            current_run += 1
        else:
            if current_run > longest_streak:
                longest_streak = current_run
            current_run = 1
    if current_run > longest_streak:
        longest_streak = current_run

    # 2. Current Streak
    # Ở đây vẫn cần timezone_offset để biết giờ VN hiện tại
    user_now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=timezone_offset)
    user_today = user_now.date()
    user_yesterday = user_today - timedelta(days=1)

    current_streak = 0
    check_date = user_today

    if user_today not in local_dates_set:
        if user_yesterday in local_dates_set:
            check_date = user_yesterday
        else:
            return 0, longest_streak

    while check_date in local_dates_set:
        current_streak += 1
        check_date -= timedelta(days=1)

    return current_streak, longest_streak