"""
API Routes for AI Resume ATS System
===================================

Professional REST API endpoints for resume processing, analysis,
and job matching operations.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from app.agents.parser_agent import ParserAgent
from app.agents.normalization_agent import NormalizationAgent
from app.agents.matcher_agent import MatcherAgent
from app.orchestrator import Orchestrator
from app.database.db import save_candidate_data, save_processing_history

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic Models for Request/Response validation
class PersonalInfo(BaseModel):
    """Personal information model."""
    name: str = Field(..., description="Candidate's full name")
    email: str = Field("", description="Email address")
    phone: str = Field("", description="Phone number")
    location: str = Field("", description="Location/City")
    linkedin: str = Field("", description="LinkedIn profile URL")


class SkillsInfo(BaseModel):
    """Skills information model."""
    technical: List[str] = Field(default_factory=list, description="Technical skills")
    soft: List[str] = Field(default_factory=list, description="Soft skills")
    certifications: List[str] = Field(default_factory=list, description="Certifications")


class ExperienceInfo(BaseModel):
    """Experience information model."""
    company: str = Field("", description="Company name")
    position: str = Field("", description="Job position")
    duration: str = Field("", description="Duration of employment")
    description: str = Field("", description="Job description")


class EducationInfo(BaseModel):
    """Education information model."""
    institution: str = Field("", description="Institution name")
    degree: str = Field("", description="Degree obtained")
    year: str = Field("", description="Graduation year")


class ParsedResumeResponse(BaseModel):
    """Response model for parsed resume data."""
    personal: PersonalInfo
    skills: SkillsInfo
    experience: List[ExperienceInfo] = Field(default_factory=list)
    education: List[EducationInfo] = Field(default_factory=list)
    normalized_skills: List[str] = Field(default_factory=list)
    total_experience_years: float = Field(0.0, description="Total years of experience")
    summary: str = Field("", description="Resume summary")


class MatchRequest(BaseModel):
    """Request model for job-resume matching."""
    resume_text: str = Field(..., min_length=10, description="Resume text content")
    job_skills: List[str] = Field(..., min_items=1, description="Required job skills")

    @validator('job_skills')
    def validate_job_skills(cls, v):
        """Validate that job skills are not empty strings."""
        if any(not skill.strip() for skill in v):
            raise ValueError("Job skills cannot be empty strings")
        return [skill.strip() for skill in v]


class MatchResult(BaseModel):
    """Job matching result model."""
    overall_score: float = Field(..., ge=0, le=100, description="Overall match percentage")
    matched_skills: List[str] = Field(default_factory=list, description="Skills that match")
    missing_skills: List[str] = Field(default_factory=list, description="Skills that are missing")
    evaluation: Dict[str, Any] = Field(default_factory=dict, description="Detailed evaluation")


class ProcessingResponse(BaseModel):
    """Complete processing response model."""
    parsed: ParsedResumeResponse
    normalized: Dict[str, Any]
    match: MatchResult
    processing_time: float = Field(..., description="Processing time in seconds")
    candidate_id: Optional[int] = Field(None, description="Database candidate ID")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# API Endpoints
@router.get("/", tags=["General"])
async def home():
    """
    Root endpoint providing API information and health status.

    Returns basic API information and available endpoints.
    """
    return {
        "message": "🚀 AI Resume ATS System API is operational",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "match": "/api/v1/match",
            "parse_file": "/api/v1/parse-file"
        }
    }


@router.post(
    "/match",
    response_model=ProcessingResponse,
    tags=["Resume Processing"],
    summary="Match Resume Against Job Requirements",
    description="""
    Analyze a resume against job requirements and calculate match scores.

    This endpoint:
    - Parses the resume text
    - Normalizes and standardizes skills
    - Matches against provided job skills
    - Returns detailed matching analysis
    """
)
async def match_resume(
    request: MatchRequest,
    background_tasks: BackgroundTasks
) -> ProcessingResponse:
    """
    Match resume text against job requirements.

    Performs complete resume analysis pipeline including parsing,
    normalization, and matching with performance tracking.
    """
    start_time = time.time()

    try:
        logger.info(f"🔍 Processing resume match request for {len(request.resume_text)} characters")

        # Initialize orchestrator
        orchestrator = Orchestrator()

        # Process the resume
        result = orchestrator.process(
            request.resume_text,
            request.job_skills
        )

        processing_time = round(time.time() - start_time, 2)
        result["processing_time"] = processing_time

        # Validate result structure
        if "error" in result:
            raise HTTPException(
                status_code=422,
                detail=f"Processing failed: {result['error']}"
            )

        # Add latency information
        result["processing_time"] = processing_time

        # Save to database in background (optional)
        if "parsed" in result and result["parsed"].get("personal", {}).get("name"):
            background_tasks.add_task(
                _save_processing_result,
                result,
                "match",
                processing_time
            )

        logger.info(f"✅ Resume match completed in {processing_time}s")
        return result

    except HTTPException:
        raise
    except Exception as e:
        processing_time = round(time.time() - start_time, 2)
        logger.error(f"❌ Resume match failed after {processing_time}s: {str(e)}")

        # Save error to database
        background_tasks.add_task(
            _save_processing_error,
            "match",
            str(e),
            processing_time
        )

        raise HTTPException(
            status_code=500,
            detail=f"Internal processing error: {str(e)}"
        )


@router.post(
    "/parse-file",
    response_model=ParsedResumeResponse,
    tags=["Resume Processing"],
    summary="Parse Resume from File Upload",
    description="""
    Extract and parse resume data from uploaded file.

    Supported formats: PDF, DOCX, TXT
    Maximum file size: 10MB
    """
)
async def parse_file(
    file: UploadFile = File(..., description="Resume file to parse"),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> ParsedResumeResponse:
    """
    Parse resume from uploaded file.

    Extracts text from various file formats and parses structured resume data.
    """
    start_time = time.time()

    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt", ".doc"}
    file_extension = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate file size (10MB limit)
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    if file_size_mb > 10:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum: 10MB"
        )

    try:
        logger.info(f"📄 Processing file: {file.filename} ({file_size_mb:.1f}MB)")

        # Extract text from file
        parser = ParserAgent()
        text = parser.extract_text(file_content, file.filename)

        if not text or len(text.strip()) < 50:
            raise HTTPException(
                status_code=422,
                detail="Could not extract sufficient text from file. Please check file format and content."
            )

        # Parse the resume
        parsed_data = parser.parse_resume(text)

        # Ensure proper data structure
        parsed_data = _validate_parsed_data(parsed_data)

        # Normalize skills
        try:
            normalizer = NormalizationAgent()
            norm_result = normalizer.normalize_skills(
                parsed_data["skills"].get("technical", []),
                text
            )
            parsed_data["normalized_skills"] = norm_result.get("normalized_skills", [])
        except Exception as e:
            logger.warning(f"Skills normalization failed: {e}")
            parsed_data["normalized_skills"] = []

        processing_time = round(time.time() - start_time, 2)

        # Save to database in background
        background_tasks.add_task(
            _save_parsed_resume,
            parsed_data,
            processing_time
        )

        logger.info(f"✅ File parsing completed in {processing_time}s")
        return parsed_data

    except HTTPException:
        raise
    except Exception as e:
        processing_time = round(time.time() - start_time, 2)
        logger.error(f"❌ File parsing failed after {processing_time}s: {str(e)}")

        # Save error to database
        background_tasks.add_task(
            _save_processing_error,
            "parse_file",
            str(e),
            processing_time
        )

        raise HTTPException(
            status_code=500,
            detail=f"File processing failed: {str(e)}"
        )


# Helper functions
def _validate_parsed_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and ensure proper structure of parsed resume data."""
    if not isinstance(data, dict):
        data = {}

    # Ensure personal information structure
    if "personal" not in data or not isinstance(data.get("personal"), dict):
        data["personal"] = {
            "name": "Unknown",
            "email": "",
            "phone": "",
            "location": "",
            "linkedin": ""
        }

    personal = data["personal"]
    personal.setdefault("name", "Unknown")
    personal.setdefault("email", "")
    personal.setdefault("phone", "")
    personal.setdefault("location", "")
    personal.setdefault("linkedin", "")

    # Ensure skills structure
    if "skills" not in data or not isinstance(data.get("skills"), dict):
        data["skills"] = {"technical": [], "soft": [], "certifications": []}

    skills = data["skills"]
    skills.setdefault("technical", [])
    skills.setdefault("soft", [])
    skills.setdefault("certifications", [])

    # Ensure other fields
    data.setdefault("experience", [])
    data.setdefault("education", [])
    data.setdefault("total_experience_years", 0)
    data.setdefault("summary", "")

    return data


async def _save_parsed_resume(parsed_data: Dict[str, Any], processing_time: float) -> None:
    """Save parsed resume data to database."""
    try:
        candidate_id = await save_candidate_data(parsed_data.get("personal", {}))
        await save_processing_history(
            candidate_id,
            "parse_file",
            "file_upload",
            str(parsed_data),
            processing_time,
            True
        )
    except Exception as e:
        logger.error(f"Failed to save parsed resume: {e}")


async def _save_processing_result(result: Dict[str, Any], operation: str, processing_time: float) -> None:
    """Save processing result to database."""
    try:
        candidate_id = await save_candidate_data(result.get("parsed", {}).get("personal", {}))
        await save_processing_history(
            candidate_id,
            operation,
            str(result.get("match", {}).get("job_skills", [])),
            str(result),
            processing_time,
            True
        )
    except Exception as e:
        logger.error(f"Failed to save processing result: {e}")


async def _save_processing_error(operation: str, error: str, processing_time: float) -> None:
    """Save processing error to database."""
    try:
        await save_processing_history(
            None,
            operation,
            "",
            "",
            processing_time,
            False,
            error
        )
    except Exception as e:
        logger.error(f"Failed to save processing error: {e}")

        text = parser.extract_text(content, file.filename)
        parsed_data = parser.parse_resume(text)

        if "skills" not in parsed_data or not isinstance(parsed_data["skills"], dict):
            parsed_data["skills"] = {"technical": [], "soft": []}

        norm = normalizer.normalize_skills(parsed_data["skills"]["technical"], text)

        parsed_data["normalized_skills"] = norm.get("normalized_skills", [])

        results.append({
            "filename": file.filename,
            "data": parsed_data
        })

    return {"results": results}

@router.get("/skills/taxonomy")
def get_taxonomy():
    from app.agents.normalization_agent import SKILL_TAXONOMY
    return SKILL_TAXONOMY


@router.get("/health")
def health():
    return {"status": "running"}