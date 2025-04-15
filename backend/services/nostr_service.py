import hashlib
import os
import secrets
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv
from nostr_sdk import Keys, Client, EventBuilder, NostrSigner, Tag, Kind, KindStandard
import json
import websocket
import bech32

load_dotenv()


async def npub_to_hex(npub):
    """
        Convert npub format to hex.
    """
    hrp, data = bech32.bech32_decode(npub)
    if hrp != "npub":
        raise ValueError("Invalid npub")
    # Convert 5-bit groups back to 8-bit bytes
    data_bytes = bech32.convertbits(data, 5, 8, False)
    return bytes(data_bytes).hex()


class NostrService:
    """
    A Nostr service for publishing various types of events
    to the Nostr network using the nostr-sdk library
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

    def _generate_unique_id(self):
        """Generate a unique ID for events."""
        timestamp = str(time.time())
        random_bytes = secrets.token_bytes(16)
        combined = timestamp.encode() + random_bytes
        unique_id = hashlib.sha256(combined).hexdigest()[:32]

        return unique_id

    async def connect(self, custom_private_key: str = None):
        """
        Connect to Nostr relays

        Args:
            custom_private_key: Optional private key to use instead of the default
        """
        if self.is_connected:
            return

        try:
            if custom_private_key:
                keys = Keys.parse(custom_private_key)
            else:
                keys = Keys.parse(self.private_key_hex)

            self.signer = NostrSigner.keys(keys)
            self.client = Client(self.signer)

            for relay in self.relays:
                await self.client.add_relay(relay)

            await self.client.connect()
            self.is_connected = True
        except Exception as e:
            self.is_connected = False
            raise e

    async def ensure_connected(self, custom_private_key: str = None):
        """
        Ensure we're connected to relays before operations

        Args:
            custom_private_key: Optional private key to use for this connection
        """
        if not self.is_connected or custom_private_key:
            await self.connect(custom_private_key)

    async def publish_event(self,
                            content: str,
                            tags: List[Tag] = None,
                            kind_value: int = None) -> Dict[str, str]:
        """
        Publish a generic event to Nostr relays with an automatically generated unique identifier.

        Args:
            content: Content of the event
            tags: List of Tag objects to include (optional)
            kind_value: Integer value of the Kind (optional)

        Returns:
            Dictionary with event_id and identifier
        """
        await self.ensure_connected()

        if not self.client or not self.signer:
            return {
                "event_id": "nostr-error-not-initialized",
                "identifier": ""
            }

        try:
            unique_id = self._generate_unique_id()
            if tags is None:
                tags = []

            identifier_tag = Tag.identifier(unique_id)
            tags.append(identifier_tag)

            if kind_value == 0 or kind_value == Kind.from_std(KindStandard.METADATA).as_u16():
                builder = EventBuilder.metadata(content) # not used in final release
            else:
                builder = EventBuilder.text_note(content)
            if kind_value is not None:
                builder = builder.kind(Kind(kind_value))
            for tag in tags:
                builder = builder.tags([tag])
            event = await builder.sign(self.signer)
            await self.client.send_event(event)
            event_id = event.id().to_hex()
            return {
                "event_id": event_id, #nostr event id
                "identifier": unique_id #our id
            }
        except Exception as e:
            return {
                "event_id": f"nostr-error-{str(e)}",
                "identifier": ""
            }

    
    async def publish_update(self,
                             content: str,
                             previous_event_id: str,
                             tags: List[Tag] = None) -> Dict[str, str]:
        """
        Publish an update to a previous Nostr event, referencing the original event.
        """
        await self.ensure_connected()

        if not self.client or not self.signer:
            return {
                "event_id": "nostr-error-not-initialized",
                "identifier": ""
            }

        try:
            # Generate a unique identifier
            unique_id = self._generate_unique_id()

            # Initialize tags list if none provided
            if tags is None:
                tags = []

            # Add identifier tag
            identifier_tag = Tag.identifier(unique_id)
            tags.append(identifier_tag)

            # Add reference to previous event
            tags.append(Tag.parse(["e", previous_event_id]))

            # Create the event builder
            builder = EventBuilder.text_note(content)

            # Add all tags - one at a time to avoid issues
            for tag in tags:
                builder = builder.tags([tag])

            # Sign and send the event
            event = await builder.sign(self.signer)
            await self.client.send_event(event)

            # Get the event ID in hex format
            event_id = event.id().to_hex()

            return {
                "event_id": event_id,
                "identifier": unique_id
            }
        except Exception as e:
            return {
                "event_id": f"nostr-error-{str(e)}",
                "identifier": ""
            }

    async def close(self):
        """Close connections to relays"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False



    async def get_nostr_profile(self,pubkey):
        """
                Return a nostr profile from the Primal Nostr relay
        """
        ws = websocket.create_connection("wss://relay.primal.net/")
        pubkey_hex = await npub_to_hex(pubkey)
        req = ["REQ", "find-ln", {"kinds": [0], "authors": [pubkey_hex]}]
        ws.send(json.dumps(req))
        print("Request:", req)
        while True:
            response = json.loads(ws.recv())
            print("Response:", response)
            if response[0] == "EVENT" and response[2]["kind"] == 0:
                metadata = json.loads(response[2]["content"])
                ws.close()
                return metadata
            if response[0] == "EOSE":
                break
        ws.close()
        return None


# load env variables
private_key_hex = os.getenv("NOSTR_PRIVATE_KEY")
relays = os.getenv("NOSTR_RELAYS", "ws://localhost:8080").split(",")

if not private_key_hex:
    raise ValueError("NOSTR_PRIVATE_KEY environment variable is not set")
if not relays:
    raise ValueError("NOSTR_RELAYS environment variable is not set")

# create instance
nostr_service = NostrService(
    private_key_hex=private_key_hex,
    relays=relays,
)