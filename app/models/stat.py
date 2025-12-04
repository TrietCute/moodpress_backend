from pydantic import BaseModel
from typing import List, Dict
from datetime import date

class DailyMoodData(BaseModel):
    date: date
    emotion: str
    score: int # 1 (Rất tệ) -> 5 (Rất tốt)

class MoodCountStat(BaseModel):
    emotion: str
    count: int
    percentage: float

class WeeklyStatsResponse(BaseModel):
    # 1. Khung đếm tâm trạng
    mood_counts: List[MoodCountStat]
    
    # 2. Khung chuỗi ngày (Streak)
    current_streak: int
    longest_streak: int
    total_entries: int
    all_time_total: int
    active_days_in_week: List[bool]
    
    # 3. Khung biểu đồ đường
    daily_moods: List[DailyMoodData]