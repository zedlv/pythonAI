from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"ok": True}

@router.get("/async-ping")
async def async_ping():
    return {"ok": True, "type": "async"}