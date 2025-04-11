import secrets
import bcrypt
import time
import jwt
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models.challenge import Challenge
from models.user import User
from database import mongodb
from utils.pow import ProofOfWork
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from dotenv import load_dotenv

router = APIRouter(
    prefix="/users",
    tags=["users"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

load_dotenv()

# Proof of Work difficulty level, e.g. how many leading zeros are required in the hash
POW_DIFFICULTY = 4
CHALLENGE_TIMEOUT = 360  # 6 mins for pow

# authentication
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = await mongodb.db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    
    if "_id" in user:
        user["id"] = str(user["_id"])
        del user["_id"]
    
    return user


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


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await mongodb.db.users.find_one({"username": form_data.username})
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if not bcrypt.checkpw(form_data.password.encode('utf-8'), user["password"].encode('utf-8')):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not user.get("active", False):
        raise HTTPException(status_code=400, detail="User account is inactive")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

