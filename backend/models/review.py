from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from enum import IntEnum

class ReviewRating(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

class ReviewBase(BaseModel):
    listing_id: UUID
    rating: ReviewRating
    comment: Optional[str] = Field(None, max_length=1000)
    
class ReviewCreate(ReviewBase):
    pass

class ReviewInDB(ReviewBase):
    id: UUID = Field(default_factory=uuid4)
    buyer_id: UUID
    seller_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False