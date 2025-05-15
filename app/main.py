from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, users, sessions, learn, grow, analytics
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Psychological Thriller Game API",
    description="API for Learn & Grow psychological thriller game modules",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(learn.router)
app.include_router(grow.router)
app.include_router(analytics.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Psychological Thriller Game API",
        "version": "1.0.0",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)