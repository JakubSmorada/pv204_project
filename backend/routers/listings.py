from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any
from uuid import UUID, uuid4

from auth.dependencies import get_current_user
from models.listing import ListingCreate, ListingResponse, ListingUpdate, ListingSearchParams
from services.listing_service import listing_service

router = APIRouter(
    prefix="/listings",
    tags=["listings"],
    responses={404: {"description": "Listing not found"}},
)

@router.post("/", response_model=ListingResponse)
async def create_listing(
    listing: ListingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new listing.
    This endpoint requires a valid Noise session token (provided in header 'x_noise-token') to prove that the
    user has been authenticated using their private key.
    """
    # Get the seller ID from the authenticated user
    seller_id = UUID(current_user["id"]) if "id" in current_user else uuid4()

    try:
        result = await listing_service.create_listing(listing, seller_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating listing: {str(e)}")

@router.get("/", response_model=List[ListingResponse])
async def search_listings(params: ListingSearchParams = Depends()):
    """
    Search for listings with various filters
    """
    # Create search parameters
    search_params = params.dict()

    try:
        results = await listing_service.search_listings(search_params)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching listings: {str(e)}")


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


@router.post("/{listing_id}/sync", status_code=200)
async def sync_with_nostr(listing_id: str):
    """
    Force sync a listing with Nostr network
    """
    success = await listing_service.sync_with_nostr(listing_id)

    if not success:
        raise HTTPException(status_code=404, detail="Listing not found or sync failed")

    return {"status": "success", "message": "Listing synced with Nostr network"}