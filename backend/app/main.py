from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.api.routes import router
from app.models.database import create_tables

# Ensure uploads folder exists
os.makedirs("uploads", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    print("✅ SmartScreen API started")
    # Note: local docs address remains for local dev, 
    # Render will provide its own production URL
    print("📖 Docs: http://localhost:8000/docs")
    yield
    # Shutdown (optional cleanup)
    print("🛑 SmartScreen API shutting down")


app = FastAPI(
    title="SmartScreen API",
    description="Intelligent Candidate Pre-Screening System",
    version="1.0.0",
    lifespan=lifespan
)

# --- UPDATED CORS SETTINGS ---
# Added your specific Vercel deployment URL from image_1159d0.png
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://smartscreen-git-main-hemanthkumarburadas-projects.vercel.app",
        "https://smartscreen-9lzujt06j-hemanthkumarburadas-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api")

# Root endpoint
@app.get("/")
def root():
    return {
        "status": "SmartScreen API running",
        "docs": "/docs"
    }