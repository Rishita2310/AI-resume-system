"""
AI Resume ATS System - Professional Backend API
===========================================

A comprehensive AI-powered Resume Analysis and Applicant Tracking System
that parses, normalizes, and matches resumes against job requirements.

Features:
- Resume parsing from text and file uploads
- Skills normalization and standardization
- Intelligent job-resume matching with scoring
- RESTful API with comprehensive documentation
- Production-ready logging and error handling
- CORS support for web applications
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.routes.api import router
from app.database.db import init_database, close_database
from app.config import settings


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log") if settings.LOG_TO_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    logger.info("🚀 Starting AI Resume ATS System...")

    # Initialize database connection
    try:
        await init_database()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    logger.info("🎯 AI Resume ATS System is ready to serve requests")

    yield

    # Shutdown cleanup
    logger.info("🛑 Shutting down AI Resume ATS System...")
    try:
        await close_database()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

    logger.info("👋 AI Resume ATS System shutdown complete")


# Create FastAPI application with professional configuration
app = FastAPI(
    title="AI Resume ATS System",
    description="""
    ## AI-Powered Resume Analysis & Applicant Tracking System

    This API provides comprehensive resume processing capabilities including:

    ### 🔍 **Resume Parsing**
    - Extract structured data from resume text
    - Parse personal information, skills, experience, and education
    - Support for multiple file formats (PDF, DOCX, TXT)

    ### 🏷️ **Skills Normalization**
    - Standardize skill names and categories
    - Remove duplicates and inconsistencies
    - Map to industry-standard terminology

    ### 🎯 **Job Matching**
    - Calculate match scores between resumes and job requirements
    - Identify matched and missing skills
    - Provide detailed evaluation metrics

    ### 📊 **Analytics & Insights**
    - Experience level assessment
    - Skills gap analysis
    - Confidence scoring for matches
    """,
    version="1.0.0",
    contact={
        "name": "AI Resume ATS Team",
        "email": "support@airesume-ats.com",
    },
    license_info={
        "name": "MIT License",
    },
    # lifespan=lifespan,  # Commented out to avoid import-time initialization
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Custom exception handler for better error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_exception"
            },
            "path": str(request.url),
            "method": request.method
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with logging."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "internal_error"
            },
            "path": str(request.url),
            "method": request.method
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"📨 {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"📤 {request.method} {request.url} - Status: {response.status_code}")
    return response


# CORS middleware with professional configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


# Root endpoint
@app.get("/", tags=["General"])
async def root():
    """
    Welcome to AI Resume ATS System

    A comprehensive AI-powered Resume Analysis and Applicant Tracking System.

    ## Available Endpoints:
    - `GET /` - This welcome page
    - `GET /health` - System health check
    - `GET /docs` - Interactive API documentation
    - `GET /redoc` - Alternative API documentation
    - `POST /api/v1/match` - Match resume against job requirements
    - `POST /api/v1/parse-file` - Parse resume from file upload

    ## Getting Started:
    1. Visit `/docs` for interactive API documentation
    2. Use `/health` to check system status
    3. Start with the resume matching endpoint
    """
    return {
        "message": "🚀 Welcome to AI Resume ATS System",
        "version": "1.0.0",
        "status": "operational",
        "description": "AI-powered Resume Analysis and Applicant Tracking System",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "api": {
                "match": "/api/v1/match",
                "parse_file": "/api/v1/parse-file"
            }
        },
        "documentation": "Visit /docs for interactive API documentation"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns system status and basic information.
    """
    return {
        "status": "healthy",
        "service": "AI Resume ATS System",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"  # Would be dynamic in production
    }


# Include API routes
app.include_router(
    router,
    prefix="/api/v1",
    tags=["Resume Processing"]
)


if __name__ == "__main__":
    logger.info("🎬 Starting server with uvicorn...")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )