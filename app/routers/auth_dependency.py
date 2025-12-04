from fastapi import Header, HTTPException, status, Depends
from typing import Annotated

from app.db.database import get_user_collection


def get_current_user_id(x_user_id: Annotated[str, Header()]):

    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu X-User-ID header"
        )

    user_collection = get_user_collection()

    user_collection.find_one_and_update(
        {"_id": x_user_id},
        {"$setOnInsert": {"_id": x_user_id, "name": None, "gender": None, "birth": None}},
        upsert=True,
    )

    return x_user_id
