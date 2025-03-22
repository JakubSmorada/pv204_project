import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from nostr_sdk import Keys, Client, EventBuilder, NostrSigner, Tag

load_dotenv()


class NostrService:
    """
    Nostr service for publishing listings to the Nostr network
    using the nostr-sdk library
    """

    def __init__(self, private_key_hex: str = None, relays: List[str] = None):
        """
        Initialize the Nostr service

        Args:
            private_key_hex: Hex string of private key
            relays: List of relay URLs
        """
        self.private_key_hex = private_key_hex
        self.relays = relays if relays else ["ws://localhost:8080"]
        self.client = None
        self.signer = None
        self.is_connected = False

    async def connect(self):
        """Connect to Nostr relays"""
        if self.is_connected:
            return

        try:
            # Parse keys from hex
            keys = Keys.parse(self.private_key_hex)
            print(f'Using Nostr key: {keys.public_key().to_bech32()}')

            # Create signer and client
            self.signer = NostrSigner.keys(keys)
            self.client = Client(self.signer)

            # Add relays
            for relay in self.relays:
                await self.client.add_relay(relay)

            # Connect to relays
            await self.client.connect()
            self.is_connected = True
            print(f"Connected to {len(self.relays)} Nostr relay(s)")
        except Exception as e:
            print(f"Error connecting to Nostr relays: {e}")
            self.is_connected = False

    async def ensure_connected(self):
        """Ensure we're connected to relays before operations"""
        if not self.is_connected:
            await self.connect()

    async def publish_listing(self, listing_data: Dict[Any, Any]) -> str:
        """
        Publish a listing to Nostr relays.

        Args:
            listing_data: Dictionary containing listing information

        Returns:
            Event ID of the published listing
        """
        await self.ensure_connected()

        if not self.client or not self.signer:
            print("Nostr client not initialized properly")
            return f"nostr-error-{listing_data.get('id', 'unknown')}"

        try:
            # Create content - basic description of the listing
            title = listing_data.get("title", "Untitled Listing")
            price = listing_data.get("price", 0)
            condition = listing_data.get("condition", "unknown")

            content = f"📦 {title}\nPrice: ${price}\nCondition: {condition}\n\n{listing_data.get('description', '')}"

            # Create tags for better discoverability
            tags = []

            # Standard tags for marketplace listings
            tags.append(Tag.parse(["marketplace", "listing"]))
            tags.append(Tag.parse(["title", title]))
            tags.append(Tag.parse(["price", str(price)]))
            tags.append(Tag.parse(["condition", str(condition)]))

            product_tag = Tag.hashtag("")


            # Add category if available
            if "category_id" in listing_data:
                tags.append(Tag.parse(["category", str(listing_data["category_id"])]))

            # Add listing tags
            for tag in listing_data.get("tags", []):
                tags.append(Tag.parse(["t", tag]))

            # Add images if available
            for image in listing_data.get("images", []):
                if isinstance(image, dict) and "url" in image:
                    tags.append(Tag.parse(["image", str(image["url"])]))
                elif isinstance(image, str):
                    tags.append(Tag.parse(["image", image]))

            # Create the event builder
            builder = EventBuilder.text_note(content)


            builder = builder.tags([tags])

            # Sign and send the event
            event = await builder.sign(self.signer)
            result = await self.client.send_event(event)

            # Get the event ID
            event_id = result.id.to_bech32()
            print(f"Published listing to Nostr: {event_id}")

            return event_id
        except Exception as e:
            print(f"Error publishing to Nostr: {e}")
            return f"nostr-error-{listing_data.get('id', 'unknown')}"

    async def update_listing(self, event_id: str, listing_data: Dict[Any, Any]) -> str:
        """
        Update a listing by creating a new event that references the old one.

        Args:
            event_id: ID of the event to update
            listing_data: New listing data

        Returns:
            Event ID of the updated listing
        """
        await self.ensure_connected()

        if not self.client or not self.signer:
            print("Nostr client not initialized properly")
            return f"nostr-error-{listing_data.get('id', 'unknown')}"

        try:
            # Create content - basic description of the listing
            title = listing_data.get("title", "Untitled Listing")
            price = listing_data.get("price", 0)
            condition = listing_data.get("condition", "unknown")

            content = f"📦 {title} (Updated)\nPrice: ${price}\nCondition: {condition}\n\n{listing_data.get('description', '')}"

            # Create tags for better discoverability
            tags = []

            # Standard tags for marketplace listings
            tags.append(Tag.parse(["marketplace", "listing"]))
            tags.append(Tag.parse(["title", title]))
            tags.append(Tag.parse(["price", str(price)]))
            tags.append(Tag.parse(["condition", str(condition)]))

            # Add category if available
            if "category_id" in listing_data:
                tags.append(Tag.parse(["category", str(listing_data["category_id"])]))

            # Add listing tags
            for tag in listing_data.get("tags", []):
                tags.append(Tag.parse(["t", tag]))

            # Add images if available
            for image in listing_data.get("images", []):
                if isinstance(image, dict) and "url" in image:
                    tags.append(Tag.parse(["image", str(image["url"])]))
                elif isinstance(image, str):
                    tags.append(Tag.parse(["image", image]))

            # Reference the previous event - need to convert from bech32 to raw id
            try:
                # If it's a valid bech32 string, use it directly
                tags.append(Tag.event(event_id))
            except Exception:
                # If it's not a valid bech32 string, it might be a raw ID
                print(f"Warning: event_id '{event_id}' is not in bech32 format")
                tags.append(Tag.parse(["e", event_id, "reply"]))

            # Create the event builder
            builder = EventBuilder.text_note(content)

            # Add tags
            for tag in tags:
                builder = builder.tag(tag)

            # Sign and send the event
            event = await builder.sign(self.signer)
            result = await self.client.send_event(event)

            # Get the event ID
            new_event_id = result.id.to_bech32()
            print(f"Updated listing on Nostr: {new_event_id}")

            return new_event_id
        except Exception as e:
            print(f"Error updating on Nostr: {e}")
            return f"nostr-error-{listing_data.get('id', 'unknown')}"

    async def close(self):
        """Close connections to relays"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            print("Disconnected from Nostr relays")

# load env variables
private_key_hex = os.getenv("NOSTR_PRIVATE_KEY")
relays = os.getenv("NOSTR_RELAYS", "ws://localhost:8080").split(",")

if not private_key_hex:
    raise ValueError("NOSTR_PRIVATE_KEY environment variable is not set")
if not relays:
    raise ValueError("NOSTR_RELAYS environment variable is not set")

# Create a singleton instance
nostr_service = NostrService(
    private_key_hex=private_key_hex,
    relays=relays,
)