from fastapi import APIRouter
from app.services.health_service import check_db_connection

router = APIRouter()

@router.get("/health/db")
async def health_db():
    return await check_db_connection()
