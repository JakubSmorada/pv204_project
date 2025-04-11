from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    username: str
    password: str
    nonce: str
    hash: str
    active: bool = False

    def to_db(self):
        return {"username": self.username}