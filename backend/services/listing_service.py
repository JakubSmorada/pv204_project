import hashlib
import json
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
from uuid import UUID, uuid4

from nostr_sdk import Tag, TagKind

from models.listing import ListingCreate, ListingInDB, ListingUpdate
from database import mongodb
from services.nostr_service import nostr_service


class ListingService:
    """Service for handling listing operations with MongoDB and Nostr"""

    collection_name = "listings"

    @staticmethod
    def _serialize_listing(listing_dict: Dict[Any, Any]) -> Dict[Any, Any]:
        """Convert UUID, datetime, and Pydantic objects to strings for MongoDB"""
        result = {}
        for key, value in listing_dict.items():
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value
            elif isinstance(value, dict):
                result[key] = ListingService._serialize_listing(value)
            elif isinstance(value, list):
                result[key] = [
                    ListingService._serialize_listing(item) if isinstance(item, dict) else
                    str(item) if hasattr(item, '__str__') and not isinstance(item, (str, int, float, bool)) else item
                    for item in value
                ]
            elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool)):
                # Convert Pydantic types (like HttpUrl) to strings
                result[key] = str(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _deserialize_listing(db_listing: Dict[Any, Any]) -> Dict[Any, Any]:
        """Convert MongoDB document to a format compatible with Pydantic models"""
        if db_listing is None:
            return None

        # Handle ObjectId
        if "_id" in db_listing:
            db_listing["id"] = str(db_listing["_id"])
            del db_listing["_id"]

        return db_listing

    async def get_listing(self, listing_id: str) -> Optional[Dict[Any, Any]]:
        """
        Get a listing by ID from MongoDB

        Args:
            listing_id: ID of the listing

        Returns:
            Listing data or None if not found
        """
        collection = mongodb.db[self.collection_name]
        listing = await collection.find_one({"_id": listing_id})

        if not listing:
            return None

        return self._deserialize_listing(listing)

    async def get_all_listings(self) -> List[Dict[Any, Any]]:
        """
        Return all listings from MongoDB.
        """
        collection = mongodb.db[self.collection_name]
        cursor = collection.find({})
        listings = []
        async for listing in cursor:
            listings.append(self._deserialize_listing(listing))
        return listings

    async def get_listings_by_pubkey(self, pubkey: str) -> List[Dict[Any, Any]]:
        """
        Return all listings that were created by the specified public key.
        """
        print(pubkey)
        collection = mongodb.db[self.collection_name]
        cursor = collection.find({"pubkey": pubkey})
        listings = []
        async for listing in cursor:
            listings.append(self._deserialize_listing(listing))
        return listings

    async def create_listing(self, listing_data: ListingCreate) -> ListingInDB:
        """
        Create a new listing in MongoDB and publish to Nostr.
        Validates the proof-of-work nonce.
        """
        listing_dict = listing_data.dict()
        print(listing_dict)

        # Validate Proof-of-Work
        if "nonce" not in listing_dict:
            raise Exception("Nonce not provided for proof of work.")
        nonce = listing_dict["nonce"]
        is_valid, computed_hash = self.validate_proof_of_work(listing_dict, nonce, difficulty=4)
        if not is_valid:
            raise Exception(f"Invalid proof of work. Computed hash: {computed_hash} does not meet difficulty.")

        # Populate additional fields.
        listing_dict["id"] = str(uuid4())
        listing_dict["created_at"] = datetime.utcnow()
        listing_dict["updated_at"] = datetime.utcnow()
        listing_dict["status"] = "active"
        listing_dict["image"] = {"url": str(listing_dict["image"])}

        # Prepare the document for MongoDB insertion.
        mongo_listing = self._serialize_listing(listing_dict)
        mongo_listing["_id"] = str(listing_dict["id"])

        # Publish to Nostr
        try:
            title = listing_dict.get("title", "Untitled Listing")
            price = listing_dict.get("price", 0)
            condition = listing_dict.get("condition", "unknown")
            content = f"📦 {title}\nPrice: {price}\nCondition: {condition}\n\n{listing_dict.get('description', '')}"
            tags = [
                Tag.custom(cast(TagKind, TagKind.TITLE()), [title]),
                Tag.custom(cast(TagKind, TagKind.AMOUNT()), [str(price)]),
                Tag.custom(cast(TagKind, TagKind.DESCRIPTION()), [condition]),
            ]
            nostr_result = await nostr_service.publish_event(content, tags)
            mongo_listing["nostr_event_id"] = nostr_result["event_id"]
            listing_dict["nostr_event_id"] = nostr_result.get("event_id")
        except Exception as e:
            print(f"Error publishing to Nostr: {e}")
            # Continue even if Nostr publishing fails

        collection = mongodb.db[self.collection_name]
        await collection.insert_one(mongo_listing)
        return ListingInDB(**listing_dict)

    async def update_listing(self, listing_id: str, listing_update: ListingUpdate) -> Optional[Dict[Any, Any]]:
        # Get existing listing
        collection = mongodb.db[self.collection_name]
        existing = await collection.find_one({"_id": listing_id})

        if not existing:
            return None

        # Deserialize and apply updates
        existing = self._deserialize_listing(existing)
        update_data = listing_update.dict(exclude_unset=True)

        for key, value in update_data.items():
            existing[key] = value

        # Update timestamp
        existing["updated_at"] = datetime.utcnow()

        # Prepare for MongoDB update
        mongo_listing = self._serialize_listing(existing)

        # Initialize event history if it doesn't exist
        if "nostr_event_history" not in mongo_listing:
            mongo_listing["nostr_event_history"] = []
            print(f"Initializing nostr_event_history for listing {listing_id}")

        # Update in Nostr if we have a previous event ID
        if "nostr_event_id" in existing:
            try:
                print(f"Updating Nostr event, current history length: {len(mongo_listing['nostr_event_history'])}")

                # Save current event to history before updating
                previous_event = {
                    "event_id": existing.get("nostr_event_id", ""),
                    "identifier": existing.get("nostr_identifier", ""),
                    "timestamp": datetime.utcnow().isoformat()
                }
                # Add to history
                mongo_listing["nostr_event_history"].append(previous_event)
                print(f"Added previous event to history, new length: {len(mongo_listing['nostr_event_history'])}")

                # Format content for Nostr
                title = existing.get("title", "Untitled Listing")
                price = existing.get("price", 0)
                condition = existing.get("condition", "unknown")
                content = f"📦 {title} (Updated)\nPrice: ${price}\nCondition: {condition}\n\n{existing.get('description', '')}"

                # Create tags for updated listing
                tags = [
                    Tag.custom(cast(TagKind, TagKind.TITLE()), [title]),
                    Tag.custom(cast(TagKind, TagKind.AMOUNT()), [str(price)]),
                    Tag.custom(cast(TagKind, TagKind.DESCRIPTION()), [condition]),
                ]

                # Publish update to Nostr
                nostr_result = await nostr_service.publish_update(
                    content,
                    existing["nostr_event_id"],
                    tags
                )

                # Update MongoDB with new Nostr event ID
                mongo_listing["nostr_event_id"] = nostr_result["event_id"]
                mongo_listing["nostr_identifier"] = nostr_result["identifier"]

                # Update return object
                existing["nostr_event_id"] = mongo_listing["nostr_event_id"]
                existing["nostr_identifier"] = mongo_listing["nostr_identifier"]
                existing["nostr_event_history"] = mongo_listing["nostr_event_history"]

                print(f"Updated Nostr event, history now has {len(mongo_listing['nostr_event_history'])} entries")
            except Exception as e:
                print(f"Error updating in Nostr: {e}")

        # Update in MongoDB
        await collection.replace_one({"_id": listing_id}, mongo_listing)

        return existing

    def validate_proof_of_work(self, listing_data: dict, nonce: int, difficulty: int = 7) -> (bool, str):
        """
        Validates that the SHA-256 hash of the concatenation of the listing data (as a compact JSON)
        and nonce starts with a given number of zeros.

        :param listing_data: Dictionary of listing information (exclude nonce)
        :param nonce: The nonce provided by the frontend
        :param difficulty: Number of leading zeros required in the hash (default=7)
        :return: Tuple (is_valid: bool, computed_hash: str)
        """
        # Exclude "nonce" if it exists
        data_to_hash = {k: listing_data[k] for k in listing_data if k != "nonce"}
        # Use a compact JSON representation with sorted keys.
        base_str = json.dumps(data_to_hash, sort_keys=True, separators=(",", ":"))
        combined = base_str + str(nonce)
        computed_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        required_prefix = "0" * difficulty
        return computed_hash.startswith(required_prefix), computed_hash


# Create a service instance
listing_service = ListingService()