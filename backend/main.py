from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import secrets 
import hashlib

from database import mongodb
from routers import listings
from services.nostr_service import nostr_service
from mail import send_verification_email, generate_verification_code_str

# Create a lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to the database and Nostr
    mongodb.connect_to_mongo()
    print("Connected to MongoDB")

    # Initialize Nostr connection
    try:
        print("Initializing Nostr connection...")
        await nostr_service.connect()
        if nostr_service.is_connected:
            print("✅ Successfully connected to Nostr network")
        else:
            print("⚠️ Nostr connection not established")
    except Exception as e:
        print(f"❌ Error connecting to Nostr relays: {e}")
        print("Continuing without Nostr integration")

    yield  # This is where FastAPI runs and serves requests

    # Shutdown: Close connections
    print("Shutting down...")
    try:
        await nostr_service.close()
        print("Nostr connections closed")
    except Exception as e:
        print(f"Error closing Nostr connection: {e}")

    mongodb.close_mongo_connection()
    print("All connections closed")

# Pass the lifespan to FastAPI
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router)

# Create a data model
class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    active: bool = False

class VerifyEmail(BaseModel):
    email: str
    code: str

class ResendVerificationRequest(BaseModel):
    email: str

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


# Create user endpoint
@app.post("/users/", response_model=User)
async def create_user(user: User):
    try:
        existing_user = await mongodb.db.users.find_one({"$or": [
            {"username": user.username},
            {"email": user.email}
        ]})

        if existing_user:
            raise HTTPException(status_code=400, detail="User already registered.")


        user_dict = user.dict()

        verification_code = generate_verification_code_str()
        user_dict["verification_code"] = verification_code

        # Insert the user into MongoDB
        result = await mongodb.db.users.insert_one(user_dict)

        # Check if the insertion was successful
        if result.inserted_id:
            email_sent = await send_verification_email(user.email, verification_code)

            if not email_sent or email_sent != "202":
                await mongodb.db.users.delete_one({"_id": result.inserted_id})
                raise HTTPException(status_code=500, detail="Failed to send verification email")

            # Return the created user
            return user
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Get all users endpoint
@app.get("/users/")
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

@app.post("/verify-email")
async def verify_email(response_model: VerifyEmail):
    try:
        user = await mongodb.db.users.find_one({"email": response_model.email})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if "verification_code" not in user or user["verification_code"] != response_model.code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        # remove the verification_code field
        await mongodb.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "active": True
            },
            "$unset": {
                "verification_code": ""
            }}
        )
        
        return {"message": "Email verified successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")

@app.post("/resend-verification")
async def resend_verification(response_model: ResendVerificationRequest):
    try:
        user = await mongodb.db.users.find_one({"email": response_model.email, "active": False})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found or already verified")
        
        # if not verified, let the app generate new code
        verification_code = generate_verification_code_str()
        
        email_sent = await send_verification_email(response_model.email, verification_code)
        
        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
        
        # after the email has been sent successfully, update it in the db
        await mongodb.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"verification_code": verification_code}}
        )
        
        return {"message": "Verification email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resending verification for {response_model.email}: {str(e)}")