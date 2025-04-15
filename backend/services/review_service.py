from typing import Dict, Any, List, Optional
from models.review import ReviewCreate, ReviewResponse
from services.pop_service import proof_of_purchase_service
from database import mongodb

class ReviewService:
    async def create_review(self, review_data: ReviewCreate, buyer_pubkey: str) -> ReviewResponse:
        pop = await proof_of_purchase_service.get_proof_of_purchase(review_data.transaction_id)
        
        if not pop:
            raise ValueError("No PoP found for the transaction")
        
        if not await proof_of_purchase_service.verify_proof_of_purchase(pop):
            raise ValueError("Invalid PoP: seller signature verification failed")
        
        if pop.buyer_pubkey != buyer_pubkey:
            raise ValueError("Review author doesn't match the buyer in the proof of purchase")

        if review_data.rating < 1 or review_data.rating > 5:
            raise ValueError("Rating must be an integer between 1 and 5")
        
        review = {
            "transaction_id": review_data.transaction_id,
            "seller_pubkey": pop.seller_pubkey,
            "buyer_pubkey": buyer_pubkey,
            "rating": review_data.rating,
            "comment": review_data.comment,
            "verified": True 
        }
        
        result = await mongodb.reviews.insert_one(review)
        review["id"] = str(result.inserted_id)
        
        return ReviewResponse(**review)
    
    async def get_reviews_for_seller(self, seller_pubkey: str) -> List[ReviewResponse]:
        collection = mongodb.db["reviews"]
        cursor = collection.find({"seller_pubkey": seller_pubkey, "verified": True})

        reviews = await cursor.to_list(length=8)
        return [ReviewResponse(**review) for review in reviews]
    
    async def calculate_trust_score(self, seller_pubkey: str) -> float:
        """
        Calculate trust score for a seller based on verified reviews
        Trust score = sum of ratings / number of reviews
        """
        reviews = await self.get_reviews_for_seller(seller_pubkey)
        
        if not reviews:
            return 0.0
            
        total_stars = sum(review.rating for review in reviews)
        return total_stars / len(reviews)

review_service = ReviewService()