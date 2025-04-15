import time
from typing import Dict, Any, Optional
from uuid import UUID
import json
from models.pop import ProofOfPurchase
from database import mongodb
from ecdsa import SigningKey, VerifyingKey, BadSignatureError
from ecdsa.curves import SECP256k1
import hashlib
import base64

def create_signature(private_key: str, message: str) -> str:
    sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
    message_hash = hashlib.sha256(message.encode('utf-8')).digest()
    signature = sk.sign(message_hash)
    return base64.b64encode(signature).decode('utf-8')


def verify_signature(public_key: str, signature: str, message: str) -> bool:
    vk = VerifyingKey.from_string(bytes.fromhex(public_key), curve=SECP256k1)
    message_hash = hashlib.sha256(message.encode('utf-8')).digest()
    try:
        vk.verify(base64.b64decode(signature), message_hash)
        return True
    except BadSignatureError:
        return False

class PoPService:
    """Proof of purchase"""
    async def create_proof_of_purchase(
        self, 
        transaction_id: str,
        listing_id: str,
        buyer_pubkey: str,
        seller_pubkey: str,
        seller_private_key: str  # todo: handle it
    ) -> ProofOfPurchase:

        message = {
            "transaction_id": transaction_id,
            "listing_id": listing_id,
            "buyer_pubkey": buyer_pubkey,
            "seller_pubkey": seller_pubkey,
        }
        message_str = json.dumps(message, sort_keys=True)
        
        # sign the transaction with seller's priv. key
        seller_signature = create_signature(seller_private_key, message_str)
        
        pop = ProofOfPurchase(
            transaction_id=transaction_id,
            listing_id=listing_id,
            buyer_pubkey=buyer_pubkey,
            seller_pubkey=seller_pubkey,
            seller_signature=seller_signature,
        )
        
        try:
            await mongodb.proofs_of_purchase.insert_one(pop.dict())
        except Exception as e:
            raise ValueError(f"error storing PoP: {e}")

        return pop
    
    async def get_proof_of_purchase(self, transaction_id: str) -> Optional[ProofOfPurchase]:
        pop_data = await mongodb.proofs_of_purchase.find_one({"transaction_id": transaction_id})
        
        if not pop_data:
            return None

        return ProofOfPurchase(**pop_data)
    
    async def verify_proof_of_purchase(self, pop: ProofOfPurchase) -> bool:
        message = {
            "transaction_id": pop.transaction_id,
            "listing_id": pop.listing_id,
            "buyer_pubkey": pop.buyer_pubkey,
            "seller_pubkey": pop.seller_pubkey,
        }
        
        message_str = json.dumps(message, sort_keys=True)
        return verify_signature(pop.seller_pubkey, pop.seller_signature, message_str)


proof_of_purchase_service = PoPService()