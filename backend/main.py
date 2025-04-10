from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import secrets 
import hashlib

from database import mongodb
from routers import listings, users
from services.nostr_service import nostr_service

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
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}