from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    nonce: str
    hash: str
    active: bool = False