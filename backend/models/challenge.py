from pydantic import BaseModel


class Challenge(BaseModel):
    """PoW challenge model"""
    token: str  # as authentication of new user
    challenge: str  # should be a unique string
    difficulty: int  # amount of leading zeros required
    target: str