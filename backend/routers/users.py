from typing import Optional, Any, Dict

from fastapi import APIRouter, HTTPException, status, Query, Depends
from nostr_sdk import Keys

from auth.dependencies import get_current_user
from models.user import UserResponse, UserProfileResponse
from services.user_service import user_service
from services.nostr_service import nostr_service
from services.nostr_websocket_finder import websocket_finder
from pydantic import BaseModel
from typing import List



router = APIRouter(
    prefix="/users",
    tags=["users"],
)


class NostrProfileResponse(BaseModel):
    """Response model for Nostr profile data"""
    pubkey: str
    event_id: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    about: Optional[str] = None
    picture: Optional[str] = None
    lightning: Optional[str] = None
    created_at: Optional[int] = None
    nip05: Optional[str] = None
    lud16: Optional[str] = None
    other_fields: Optional[Dict[str, Any]] = None
    found: bool = False
    source: str = "unknown"  # "network", "database", or "unknown"

    class Config:
        schema_extra = {
            "example": {
                "pubkey": "npub1mrkt...",
                "event_id": "abcdef1234567890...",
                "name": "username",
                "display_name": "User's Display Name",
                "about": "About me text",
                "picture": "https://example.com/avatar.jpg",
                "lightning": "user@lightning.address",
                "created_at": 1642478347,
                "nip05": "user@domain.com",
                "lud16": "user@domain.com",
                "other_fields": {"website": "https://example.com"},
                "found": True,
                "source": "network"
            }
        }


@router.get("/", response_model=List)
async def get_users():
    try:
        users = await user_service.get_all_users()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting users: {e}"
        )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user():
    """
    Register a new user and create a Nostr profile
    """
    try:
        new_user = await user_service.register_user()
        return new_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {e}"
        )


class LoginRequest(BaseModel):
    private_key: str


@router.post("/login", response_model=UserResponse)
async def login_user(request: LoginRequest):
    """
    Login with a private key and retrieve user data
    """
    try:
        user = await user_service.login_user(private_key=request.private_key)

        # Extract the raw seed from the private key
        try:
            raw_seed = user_service.derive_raw_seed_from_private_key(request.private_key)
        except Exception as e:
            print(f"Error extracting raw seed: {e}")
            raw_seed = None

        return {
            "id": user["id"],
            "nostr_public_key": user["nostr_public_key"],
            "lightning_address": user.get("lightning_address", ""),
            "created_at": user["created_at"],
            "nostr_private_key": request.private_key,
            "raw_seed": raw_seed,
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "about": user.get("about", ""),
            "picture": user.get("picture", "")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {e}"
        )


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(user: dict = Depends(get_current_user)):
    """
    Returns the profile of the authenticated user
    """
    return user


@router.get("/nostr-profile/{public_key}")
async def get_nostr_profile(public_key: str):
    """
    Find and retrieve a Nostr profile (kind:0 event) for a given public key

    - **public_key**: Nostr public key in npub format
    """
    try:
        return await nostr_service.get_nostr_profile(public_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Nostr profile: {str(e)}")

@router.get("/my-nostr-profile", response_model=NostrProfileResponse)
async def get_my_nostr_profile(user: dict = Depends(get_current_user)):
    """
    Get the authenticated user's Nostr profile
    """
    if not user or "nostr_public_key" not in user:
        raise HTTPException(status_code=401, detail="Authentication required")

    public_key = user["nostr_public_key"]
    return await get_nostr_profile(public_key)


@router.post("/verify-profile-creation", status_code=status.HTTP_200_OK)
async def verify_profile_creation(request: LoginRequest):
    """
    Verify if a profile was created for a given private key

    This endpoint is useful for testing and debugging Nostr profile creation
    """
    try:
        # Parse the private key
        keys = Keys.parse(request.private_key)
        public_key = keys.public_key().to_bech32()

        # Try first with WebSocket finder - use correct parameter name
        profile = await websocket_finder.find_profile(public_key, timeout=5)

        # If that fails, try with nostr_service
        if not profile:
            profile = await nostr_service.find_profile(public_key, timeout_secs=5)

        if profile:
            # Profile found on network
            return {
                "success": True,
                "message": "Profile found on Nostr network",
                "public_key": public_key,
                "profile": profile,
                "event_id": profile.get("_event_id"),
                "event_kind": "0 (METADATA)",
                "source": "network"
            }

        # Check if we have the user in our database
        user = await user_service.get_user_by_public_key(public_key)
        if user and user.get("nostr_profile_event_id"):
            return {
                "success": True,
                "message": "Profile created but not found on network",
                "public_key": public_key,
                "event_id": user.get("nostr_profile_event_id"),
                "database_profile": {
                    "username": user.get("username"),
                    "display_name": user.get("display_name"),
                    "about": user.get("about"),
                    "picture": user.get("picture"),
                    "lightning": user.get("lightning_address")
                },
                "source": "database"
            }

        # No profile found
        return {
            "success": False,
            "message": "No profile found for this key",
            "public_key": public_key,
            "source": "unknown"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error verifying profile: {str(e)}"
        )