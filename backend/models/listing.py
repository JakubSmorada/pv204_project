from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4

class ListingCondition(str, Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    VERY_GOOD = "very_good"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    FOR_PARTS = "for_parts"

class ListingStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"

class Image(BaseModel):
    url: HttpUrl

class ListingBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=80)
    description: str = Field(..., min_length=20, max_length=5000)
    condition: ListingCondition
    price: int = Field(gt=0)
    pubkey: str

class ListingCreate(ListingBase):
    image: HttpUrl
    nonce: Optional[int] = Field(..., description="Proof-of-work nonce")  # PoW nonce required

class ListingInDB(ListingBase):
    id: str
    image: Image
    created_at: datetime
    updated_at: datetime
    status: ListingStatus = ListingStatus.ACTIVE
    nostr_event_id: Optional[str] = None
    paid_by: Optional[str] = None

    class Config:
        orm_mode = True

class ListingResponse(ListingInDB):
    pass

class ListingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=80)
    description: Optional[str] = Field(None, min_length=20, max_length=5000)
    condition: Optional[ListingCondition] = None
    category_id: Optional[int] = None
    price: Optional[int] = Field(None, gt=0)  # Changed to int
    quantity: Optional[int] = Field(None, ge=1)
    status: Optional[ListingStatus] = None
    tags: Optional[List[str]] = None

    @validator('tags')
    def validate_tags(cls, v):
        if v is not None and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return v
