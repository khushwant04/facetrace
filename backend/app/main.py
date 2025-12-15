# backend/app/main.py
"""
Student Face Recognition SaaS
- AWS Rekognition for face detection
- Neon PostgreSQL for data
- Auth0 Organizations for multi-tenancy
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.api.v1 import scan

app = FastAPI(
    title="Student Face Recognition SaaS",
    version="1.0.0",
    description="Face recognition system for educational institutions"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api/v1")

# WebSocket routes (at root level)
app.include_router(scan.router, tags=["Real-time Scanning"])


@app.get("/")
async def root():
    return {
        "name": "Student Face Recognition API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
