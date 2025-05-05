from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


# ---------- Login ----------
class TelegramAuth(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: Optional[int] = None
    hash: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh: str