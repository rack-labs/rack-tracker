from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Motion Analysis Backend is running."}
