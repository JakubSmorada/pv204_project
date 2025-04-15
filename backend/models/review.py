from pydantic import BaseModel

class ReviewCreate(BaseModel):
    transaction_id: str
    rating: int
    comment: str

class ReviewResponse(BaseModel):
    seller_pubkey: str
    rating: int
    comment: str
    transaction_id: str
    verified: bool