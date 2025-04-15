from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any
from uuid import UUID, uuid4

from auth.dependencies import get_current_user
from models.listing import ListingCreate, ListingResponse, ListingUpdate
from services.listing_service import listing_service

router = APIRouter(
    prefix="/listings",
    tags=["listings"],
    responses={404: {"description": "Listing not found"}},
)

@router.post("/", response_model=ListingResponse)
async def create_listing(
    listing: ListingCreate,
):
    """
    Create a new listing with proof-of-work.
    Expects a valid session token (provided in the query parameter) and requires a nonce in the JSON body.
    """
    try:
        result = await listing_service.create_listing(listing)
        return result
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error creating listing: {str(e)}")


@router.get("/", response_model=List[ListingResponse])
async def get_all_listings():
    """
    Return all listings from MongoDB.
    """
    try:
        results = await listing_service.get_all_listings()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving listings: {str(e)}")

@router.get("/{public_key}", response_model=List[ListingResponse])
async def get_listings_by_pubkey(public_key: str):
    """
    Return all listings for a specific public key.
    """
    try:
        results = await listing_service.get_listings_by_pubkey(public_key)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving listings: {str(e)}")


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: str, background_tasks: BackgroundTasks):
    """
    Get a specific listing by ID
    """
    # Retrieve from MongoDB
    listing = await listing_service.get_listing(listing_id)

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Increment view count in background
    background_tasks.add_task(listing_service.increment_view_count, listing_id)

    return listing


@router.put("/{listing_id}", response_model=ListingResponse)
async def update_listing(listing_id: str, listing_update: ListingUpdate):
    """
    Update an existing listing
    """
    # Update in MongoDB and Nostr
    updated_listing = await listing_service.update_listing(listing_id, listing_update)

    if not updated_listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    return updated_listing


@router.delete("/{listing_id}", status_code=204)
async def delete_listing(listing_id: str):
    """
    Delete a listing
    """
    success = await listing_service.delete_listing(listing_id)

    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")

    return None


# @router.post("/{listing_id}/sync", status_code=200)
# async def sync_with_nostr(listing_id: str):
#     """
#     Force sync a listing with Nostr network
#     """
#     success = await listing_service.sync_with_nostr(listing_id)
#
#     if not success:
#         raise HTTPException(status_code=404, detail="Listing not found or sync failed")
#
#     return {"status": "success", "message": "Listing synced with Nostr network"}