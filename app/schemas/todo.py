from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TodoCreate(BaseModel):
    title: str
    desc: Optional[str] = None
    done: bool = False
    assigned_to: Optional[str] = None


class TodoResponse(TodoCreate):
    id: str
    created_at: Optional[datetime] = None