from fastapi import FastAPI
from app.routers import journal_router
from app.routers import chat_router
from app.routers import user_router
from app.routers import stat_router

app = FastAPI(
    title="MyMoodApp Backend", description="Backend cho ứng dụng ghi nhận cảm xúc."
)

app.include_router(user_router.router)
app.include_router(journal_router.router)
app.include_router(chat_router.router)
app.include_router(stat_router.router)
