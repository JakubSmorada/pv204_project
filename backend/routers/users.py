import secrets
import bcrypt
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models.challenge import Challenge
from models.user import User
from database import mongodb
from utils.pow import ProofOfWork

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# Proof of Work difficulty level, e.g. how many leading zeros are required in the hash
POW_DIFFICULTY = 4
CHALLENGE_TIMEOUT = 360  # 6 mins for pow

@router.get("/challenge")
async def get_challenge():
    random_string = secrets.token_hex(16)
    token = secrets.token_hex(16)
    difficulty = POW_DIFFICULTY
    timestamp = datetime.utcnow() + timedelta(seconds=CHALLENGE_TIMEOUT)

    await mongodb.db.challenges.insert_one({
        "token": token,
        "challenge": random_string,
        "timeout_at": timestamp
    })

    return Challenge(
        token=token,
        challenge=random_string,
        difficulty=difficulty,
        target=ProofOfWork.get_target(difficulty)
    )

@router.post("/register", response_model=User)
async def create_user(user: User, token: str):
    try:
        challenge_doc = await mongodb.db.challenges.find_one({"token": token})
        if not challenge_doc:
            raise HTTPException(status_code=400, detail="Invalid token")

        challenge = challenge_doc["challenge"]
        created_at = challenge_doc["timeout_at"]
        current_time = datetime.utcnow()
        
        # todo: periodic cleanup could be useful
        if current_time > created_at:
            await mongodb.db.challenges.delete_one({"token": token})
            raise HTTPException(status_code=400, detail="Challenge has expired. Request a new challenge.")

        existing_user = await mongodb.db.users.find_one({"$or": [
            {"username": user.username}
        ]})

        if existing_user:
            raise HTTPException(status_code=400, detail="User already registered.")

        # start creating the user only if the PoW is valid
        user_dict = user.dict()
        if not ProofOfWork.verify_proof(user_dict, POW_DIFFICULTY, challenge):
            raise HTTPException(status_code=400, detail="Invalid proof of work. Got: " + str(user_dict))

        await mongodb.db.challenges.delete_one({"token": token})

        # removal of unnecessary data
        if "nonce" in user_dict:
            del user_dict["nonce"]
        if "hash" in user_dict:
            del user_dict["hash"]
        user_dict["active"] = True

        hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        user_dict["password"] = hashed_pw.decode('utf-8')

        result = await mongodb.db.users.insert_one(user_dict)

        # insertion successful or not
        if result.inserted_id:
            return user
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during registration: {str(e)}")


# Get all users endpoint
@router.get("/")
async def get_users():
    try:
        users = []
        cursor = mongodb.db.users.find({})
        async for document in cursor:
            # Convert MongoDB ObjectId to string for JSON serialization
            if "_id" in document:
                document["id"] = str(document["_id"])
                del document["_id"]

            # remove sensitive info
            if "verification_code" in document:
                del document["verification_code"]

            users.append(document)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
