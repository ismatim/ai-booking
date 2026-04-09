from fastapi import HTTPException, status
from config import get_settings


def dev_only():
    settings = get_settings()
    if settings.env != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
