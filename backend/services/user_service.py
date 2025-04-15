from uuid import uuid4
from datetime import datetime
from nostr_sdk import Keys
from database import mongodb
from bech32 import bech32_decode, convertbits
from services.nostr_service import nostr_service

class UserService:
    collection_name = "users"

    def generate_nostr_key_pair(self, prefix: str):
        """
        Generate a Nostr key pair repeatedly until the public key starts with the given prefix.
        Returns a tuple: (private_key, public_key).
        Both keys are nostr_sdk.Key objects; you can call .to_bech32() on them.
        """
        while True:
            keys = Keys.generate()
            private_key = keys.secret_key()
            public_key = keys.public_key()
            bech32_pub = public_key.to_bech32()
            if bech32_pub.startswith(prefix):
                return private_key, public_key

    def derive_raw_seed_from_private_key(self, private_key: str) -> str:
        """Extract raw seed bytes from a private key and return as hex string."""
        hrp, data = bech32_decode(private_key)
        if not data:
            raise ValueError("Invalid private key format")
        raw_seed_bytes = bytes(convertbits(data, 5, 8, False))
        return raw_seed_bytes.hex()

    async def register_user(self) -> dict:
        """
        Register a new user by generating a Nostr key pair using the forced prefix.
        Only the public key is stored in the database.
        Returns a dict containing user id, public key, private key, creation timestamp,
        and empty profile fields.
        """
        prefix = "npub1mrkt"
        private_key, public_key = self.generate_nostr_key_pair(prefix)
        private_key_bech32 = private_key.to_bech32()
        public_key_bech32 = public_key.to_bech32()

        user_id = uuid4()
        created_at = datetime.utcnow()
        raw_seed = self.derive_raw_seed_from_private_key(private_key_bech32)

        # No profile is created; we simply store empty strings for profile details.
        user_record = {
            "id": str(user_id),
            "nostr_public_key": public_key_bech32,
            "created_at": created_at,
            "raw_seed": raw_seed,
            "username": "",
            "display_name": "",
            "about": "",
            "picture": ""
        }
        user_record["_id"] = str(user_id)

        collection = mongodb.db[self.collection_name]
        await collection.insert_one(user_record)

        response = {
            "id": str(user_id),
            "nostr_public_key": public_key_bech32,
            "nostr_private_key": private_key_bech32,
            "raw_seed": raw_seed,
            "created_at": created_at,
            "username": "",
            "display_name": "",
            "about": "",
            "picture": ""
        }
        return response

    async def login_user(self, private_key: str) -> dict:
        """
        Log in a user based on their private key (nsec1...).
        Uses nostr-sdk to parse the provided private key (nsec1 string),
        derives the public key and checks that it starts with "npub1mrkt".
        If the user exists in the database, returns the user.
        Otherwise, creates a new user with empty profile fields.
        """
        try:
            keys = Keys.parse(private_key)
        except Exception as e:
            raise ValueError("Unable to parse private key. Ensure it is a valid nsec1 string.") from e

        derived_public_key = keys.public_key().to_bech32()
        prefix = "npub1mrkt"
        if not derived_public_key.startswith(prefix):
            raise ValueError("Derived public key does not meet required prefix (mrkt).")

        # Get the raw seed
        raw_seed = self.derive_raw_seed_from_private_key(private_key)

        collection = mongodb.db[self.collection_name]
        user = await collection.find_one({"nostr_public_key": derived_public_key})

        if user:
            # Update raw_seed if it is not present
            if not user.get("raw_seed"):
                await collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"raw_seed": raw_seed}}
                )
        else:
            # Create a new user with empty profile fields
            user_id = uuid4()
            created_at = datetime.utcnow()
            user_record = {
                "id": str(user_id),
                "nostr_public_key": derived_public_key,
                "created_at": created_at,
                "raw_seed": raw_seed,
                "username": "",
                "display_name": "",
                "about": "",
                "picture": ""
            }
            user_record["_id"] = str(user_id)
            await collection.insert_one(user_record)
            user = user_record

        return {
            "id": user["id"],
            "nostr_public_key": user["nostr_public_key"],
            "created_at": user["created_at"],
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "about": user.get("about", ""),
            "picture": user.get("picture", "")
        }

    async def get_user_by_public_key(self, public_key: str) -> dict:
        """Get user by their public key"""
        collection = mongodb.db[self.collection_name]
        user = await collection.find_one({"nostr_public_key": public_key})
        if not user:
            return None
        return user
    
    async def get_all_users(self) -> list:
        """Returns all users but only their pubkeys and ids"""
        collection = mongodb.db[self.collection_name]
        cursor = collection.find({})
        users = []
        async for user in cursor:
            user_data = {
                "id": str(user["_id"]),
                "nostr_public_key": user.get("nostr_public_key"),
                "created_at": user.get("created_at"),
                "username": user.get("username", ""),
                "display_name": user.get("display_name", ""),
                "about": user.get("about", "")
            }

            users.append(user_data)
        return users


user_service = UserService()