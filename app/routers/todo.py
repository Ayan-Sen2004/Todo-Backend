from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.models.todo import todo_collection
from app.schemas.todo import TodoCreate
from app.utils.dependency import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/todo", tags=["Todo"])


@router.post("/create")
async def create_todo(
    todo: TodoCreate,
    current_user=Depends(get_current_user)
):
    # Temporary
    print(current_user)

    new_todo = todo.model_dump()

    # Save owner id
    new_todo["user_id"] = current_user["sub"]
    new_todo["created_at"] = datetime.now(timezone.utc)

    result = await todo_collection.insert_one(new_todo)

    return {
        "message": "Todo Created",
        "id": str(result.inserted_id)
    }

@router.get("/fetch")
async def get_todos(current_user=Depends(get_current_user)):

    todos = []

    async for todo in todo_collection.find(
        {"user_id": current_user["sub"]}
    ):

        todo["_id"] = str(todo["_id"])
        
        if "created_at" in todo and todo["created_at"]:
            if hasattr(todo["created_at"], "replace"):
                todo["created_at"] = todo["created_at"].replace(tzinfo=timezone.utc)

        todos.append(todo)

    return todos

@router.put("/update/{todo_id}")
async def update_todo(
    todo_id: str,
    todo: TodoCreate,
    current_user=Depends(get_current_user)
):

    result = await todo_collection.update_one(
        {
            "_id": ObjectId(todo_id),
            "user_id": current_user["sub"]
        },
        {
            "$set": todo.model_dump()
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return {
        "message": "Todo updated successfully"
    }

@router.delete("/delete/{todo_id}")
async def delete_todo(
    todo_id: str,
    current_user=Depends(get_current_user)
):

    result = await todo_collection.delete_one(
        {
            "_id": ObjectId(todo_id),
            "user_id": current_user["sub"]
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return {
        "message": "Todo deleted successfully"
    }