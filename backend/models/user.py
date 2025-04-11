from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    password: str
    nonce: Optional[str] = None
    hash: Optional[str] = None
    active: bool = False

    def to_db(self):
        return {"username": self.username}