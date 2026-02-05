"""Viewership history schemas."""
from datetime import datetime
from typing import List

from pydantic import BaseModel


class ViewershipRecord(BaseModel):
    """Single viewership record."""
    
    timestamp: datetime
    viewcount: int
    
    model_config = {"from_attributes": True}


class ViewershipHistoryResponse(BaseModel):
    """Viewership history response."""
    
    livestream_id: int
    livestream_name: str
    records: List[ViewershipRecord]
    total_records: int
