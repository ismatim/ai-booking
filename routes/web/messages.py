from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from models import AvailabilityCreate, ConsultantCreate, ConsultantUpdate
from services.supabase_service import SupabaseService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/web/messages", tags=["Messages"])
