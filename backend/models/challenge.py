from pydantic import BaseModel


class Challenge(BaseModel):
    """PoW challenge model"""
    challenge: str  # should be a unique string
    difficulty: int  # amount of leading zeros required
    target: str