"""
後台管理 API — placeholder。
規劃: 餐點/分類 CRUD、訂單列表、系統參數 (Food_SystemConfig) 維護、桌位管理。
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
def dashboard() -> dict[str, str]:
    return {"detail": "TODO: 今日營收 / 在線桌數 / 待處理訂單"}


@router.get("/system-config")
def list_system_config() -> dict[str, str]:
    return {"detail": "TODO: list Food_SystemConfig (SERVICE_FEE_RATE 等)"}
