from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.models.todo import todo_collection
from app.models.user import user_collection
from app.schemas.todo import TodoCreate
from app.utils.dependency import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/todo", tags=["Todo"])


@router.post("/create")
async def create_todo(
    todo: TodoCreate,
    current_user=Depends(get_current_user)
):
    # Check user role
    db_user = await user_collection.find_one({"_id": ObjectId(current_user["sub"])})
    is_admin = db_user and db_user.get("role") == "admin"

    new_todo = todo.model_dump()

    # Save owner id
    if is_admin and todo.assigned_to:
        new_todo["user_id"] = todo.assigned_to
    else:
        new_todo["user_id"] = current_user["sub"]
        
    new_todo["created_at"] = datetime.now(timezone.utc)

    # Save details of user/admin who assigned the task
    new_todo["assigned_by_id"] = current_user["sub"]
    admin_user = await user_collection.find_one({"_id": ObjectId(current_user["sub"])})
    if admin_user:
        new_todo["assigned_by_username"] = admin_user.get("username", "System")
        new_todo["assigned_by_email"] = admin_user.get("email", "System")

    result = await todo_collection.insert_one(new_todo)

    return {
        "message": "Todo Created",
        "id": str(result.inserted_id)
    }

@router.get("/fetch")
async def get_todos(current_user=Depends(get_current_user)):
    # Check user role
    db_user = await user_collection.find_one({"_id": ObjectId(current_user["sub"])})
    is_admin = db_user and db_user.get("role") == "admin"

    todos = []
    query = {} if is_admin else {"user_id": current_user["sub"]}

    async for todo in todo_collection.find(query):
        todo["_id"] = str(todo["_id"])
        
        # Populate username and email for admin view
        if is_admin:
            assigned_user = await user_collection.find_one({"_id": ObjectId(todo["user_id"])})
            if assigned_user:
                todo["assigned_to_username"] = assigned_user.get("username", "Unknown")
                todo["assigned_to_email"] = assigned_user.get("email", "Unknown")
            else:
                todo["assigned_to_username"] = "Unknown"
                todo["assigned_to_email"] = "Unknown"
        
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
    # Check user role
    db_user = await user_collection.find_one({"_id": ObjectId(current_user["sub"])})
    is_admin = db_user and db_user.get("role") == "admin"

    existing_todo = await todo_collection.find_one({"_id": ObjectId(todo_id)})
    if not existing_todo:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    # If it is already completed, it is permanently locked unless bypassed by admin with a reason
    if existing_todo.get("done"):
        if is_admin:
            if todo.done == False:
                if not todo.revert_reason or todo.revert_reason.strip() == "":
                    raise HTTPException(
                        status_code=400,
                        detail="Please provide a reason to revert this completed task to pending"
                    )
        else:
            raise HTTPException(
                status_code=400,
                detail="Task is completed and permanently locked"
            )

    query = {"_id": ObjectId(todo_id)}

    if is_admin:
        update_data = todo.model_dump()
        if todo.assigned_to:
            update_data["user_id"] = todo.assigned_to
    else:
        # User checks
        if existing_todo["user_id"] != current_user["sub"]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to edit this task"
            )
        
        # Users can only mark tasks as done (done=True) and cannot change other fields
        if not todo.done:
            raise HTTPException(
                status_code=400,
                detail="Users can only change status to completed"
            )
            
        update_data = {
            "done": True
        }

    result = await todo_collection.update_one(
        query,
        {
            "$set": update_data
        }
    )

    if result.matched_count == 0:
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
    # Check user role
    db_user = await user_collection.find_one({"_id": ObjectId(current_user["sub"])})
    is_admin = db_user and db_user.get("role") == "admin"

    # Only admins can delete tasks
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Only admins can delete tasks"
        )

    query = {"_id": ObjectId(todo_id)}
    result = await todo_collection.delete_one(query)

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Todo not found"
        )

    return {
        "message": "Todo deleted successfully"
    }

@router.get("/user/{user_id}")
async def get_user_todos(
    user_id: str,
    current_user=Depends(get_current_user)
):
    db_user = await user_collection.find_one({"_id": ObjectId(current_user["sub"])})
    if not db_user or db_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admins only"
        )

    todos = []
    async for todo in todo_collection.find({"user_id": user_id}):
        todo["_id"] = str(todo["_id"])
        
        if "created_at" in todo and todo["created_at"]:
            if hasattr(todo["created_at"], "replace"):
                todo["created_at"] = todo["created_at"].replace(tzinfo=timezone.utc)

        todos.append(todo)

    return todos

