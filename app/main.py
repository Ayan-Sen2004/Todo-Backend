from fastapi import FastAPI
from mangum import Mangum

from app.routers.auth import router as auth_router
from app.routers.todo import router as todo_router


app = FastAPI()


app.include_router(auth_router)
app.include_router(todo_router)


@app.get("/")
async def home():
    return {
        "message": "Todo API is running"
    }


# AWS Lambda handler
handler = Mangum(app)