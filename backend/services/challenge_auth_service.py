# services/challenge_auth_service.py
import uuid
from datetime import datetime, timedelta
from bech32 import bech32_decode, convertbits
import nacl.signing
import nacl.exceptions
import binascii
from database import mongodb

# Session lifetime in seconds (1 hour = 3600 seconds)
SESSION_LIFETIME_SECONDS = 3600  # 1 hour


def parse_public_key(npub: str) -> bytes:
    """
    Decodes a Nostr public key in bech32 format (npub...) into its raw 32-byte value.
    """
    try:
        hrp, data = bech32_decode(npub)
        if data is None:
            raise ValueError("bech32_decode returned None")
        raw_pubkey = bytes(convertbits(data, 5, 8, False))
        if len(raw_pubkey) != 32:
            raise ValueError(f"Invalid public key length: {len(raw_pubkey)} (expected 32 bytes)")
        return raw_pubkey
    except Exception as e:
        raise e


def get_public_key_from_seed(raw_seed_hex: str) -> bytes:
    """
    Generate the public key from a raw seed using the same method as TweetNaCl in the frontend.
    This helps us verify signatures created by TweetNaCl on the frontend.
    """
    try:
        raw_seed = binascii.unhexlify(raw_seed_hex)
        if len(raw_seed) != 32:
            raise ValueError(f"Invalid seed length: {len(raw_seed)} (expected 32 bytes)")

        # Create a signing key from the raw seed
        signing_key = nacl.signing.SigningKey(raw_seed)

        # Get the verify key (public key)
        verify_key = signing_key.verify_key

        # Get the raw bytes of the public key
        raw_pubkey = verify_key.encode()
        return raw_pubkey
    except Exception as e:
        raise e


class ChallengeAuthService:
    async def get_challenge(self, public_key: str) -> (str, str):
        session_id = str(uuid.uuid4())
        challenge = f"auth-challenge:{session_id}"
        expires_at = datetime.utcnow() + timedelta(seconds=SESSION_LIFETIME_SECONDS)

        # Store session in MongoDB
        session_data = {
            "session_id": session_id,
            "public_key": public_key,  # stored in bech32 format, e.g., "npub1..."
            "challenge": challenge,
            "expires_at": expires_at,
            "verified": False,
            "created_at": datetime.utcnow()
        }

        # Insert into sessions collection
        await mongodb.db.sessions.insert_one(session_data)

        # Create TTL index if it doesn't exist (only needs to be done once)
        # This will automatically delete expired sessions
        await mongodb.db.sessions.create_index("expires_at", expireAfterSeconds=0)

        return session_id, challenge

    async def verify_challenge_signature(self, session_id: str, signature: bytes) -> bool:
        # Get session from MongoDB
        session_data = await mongodb.db.sessions.find_one({"session_id": session_id})

        if not session_data:
            return False

        if datetime.utcnow() > session_data["expires_at"]:
            await mongodb.db.sessions.delete_one({"session_id": session_id})
            return False

        stored_pubkey_bech32 = session_data["public_key"]
        challenge_str = session_data["challenge"]

        try:
            # Decode the stored public key using our helper
            raw_pubkey = parse_public_key(stored_pubkey_bech32)

            # Encode the challenge
            challenge_bytes = challenge_str.encode()

            verify_key = nacl.signing.VerifyKey(raw_pubkey)
            # Attempt to verify the signature
            try:
                verify_key.verify(challenge_bytes, signature)
                # Update verification status in MongoDB
                await mongodb.db.sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"verified": True}}
                )
                return True
            except nacl.exceptions.BadSignatureError:
                # If verification fails with the bech32-derived key, try using the user's raw seed
                # This is a fallback to handle TweetNaCl's key derivation on the frontend
                user = await mongodb.db.users.find_one({"nostr_public_key": stored_pubkey_bech32})

                if user and "raw_seed" in user:
                    try:
                        # Generate the public key using TweetNaCl's method
                        tweetnacl_pubkey = get_public_key_from_seed(user["raw_seed"])

                        # Verify with the TweetNaCl-derived public key
                        tweetnacl_verify_key = nacl.signing.VerifyKey(tweetnacl_pubkey)
                        tweetnacl_verify_key.verify(challenge_bytes, signature)

                        # Update verification status in MongoDB
                        await mongodb.db.sessions.update_one(
                            {"session_id": session_id},
                            {"$set": {"verified": True}}
                        )
                        return True
                    except nacl.exceptions.BadSignatureError as bse:
                        return False
                    except Exception as e:
                        return False
                else:
                    return False
        except nacl.exceptions.BadSignatureError as bse:
            return False
        except Exception as e:
            return False

    async def is_session_valid(self, session_id: str) -> bool:
        session_data = await mongodb.db.sessions.find_one({"session_id": session_id})

        if not session_data:
            return False

        if datetime.utcnow() > session_data["expires_at"]:
            await mongodb.db.sessions.delete_one({"session_id": session_id})
            return False

        return session_data["verified"]

    async def get_public_key_for_session(self, session_id: str) -> str:
        session_data = await mongodb.db.sessions.find_one({"session_id": session_id})

        if not session_data:
            return None

        if datetime.utcnow() > session_data["expires_at"]:
            await mongodb.db.sessions.delete_one({"session_id": session_id})
            return None

        if not session_data["verified"]:
            return None

        return session_data["public_key"]


challenge_auth_service = ChallengeAuthService()