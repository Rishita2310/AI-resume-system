"""
AI Resume ATS System - Simple Test Version
===========================================
"""

from fastapi import FastAPI

# Create FastAPI application
app = FastAPI(
    title="AI Resume ATS System",
    description="Professional Resume Analysis API",
    version="1.0.0",
    docs_url="/docs"
)

@app.get("/")
async def root():
    return {"message": "AI Resume ATS System is running!", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AI Resume ATS System"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)