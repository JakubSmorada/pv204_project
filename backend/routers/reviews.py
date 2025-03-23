from bson import Binary
from fastapi import APIRouter, HTTPException
from typing import List
from uuid import UUID
from datetime import datetime

from database import mongodb
from models.review import ReviewCreate, ReviewInDB, ReviewBase

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.post("/")
async def create_review(review: ReviewCreate):
    """Create a new review (simplified version)"""
    try:
        #TODO: placeholder
        mock_buyer_id = UUID("00000000-0000-0000-0000-000000000001")
        
        #TODO: placeholder
        mock_seller_id = UUID("00000000-0000-0000-0000-000000000002")
        
        review_db = ReviewInDB(
            **review.dict(),
            buyer_id=mock_buyer_id,
            seller_id=mock_seller_id,
        )
        
        # convert
        review_dict = review_db.dict()
        review_dict["id"] = Binary.from_uuid(review_db.id)
        review_dict["buyer_id"] = Binary.from_uuid(review_db.buyer_id)
        review_dict["seller_id"] = Binary.from_uuid(review_db.seller_id)
        review_dict["listing_id"] = Binary.from_uuid(review_db.listing_id)

        
        result = await mongodb.db.reviews.insert_one(review_dict)
        
        if result.inserted_id:
            return {"message": "Review created successfully", "review_id": str(review_db.id)}
        else:
            raise HTTPException(status_code=500, detail="Failed to create review")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating review: {str(e)}")
