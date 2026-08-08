from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TodoCreate(BaseModel):
    title: str
    desc: Optional[str] = None
    done: bool = False


class TodoResponse(TodoCreate):
    id: str
    created_at: Optional[datetime] = None