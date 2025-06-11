from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
from crews.crew_manager import kickoff_crew, get_crew_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CrewAI Agent System",
    description="A simple agent system using CrewAI for research and writing tasks",
    version="1.0.0"
)

# Pydantic models for request/response
class CrewInput(BaseModel):
    topic: str = Field(..., description="The topic to research and write about", min_length=3)
    additional_context: Optional[str] = Field(None, description="Additional context or requirements")

class CrewResponse(BaseModel):
    status: str
    result: Optional[str]
    message: str

# In-memory storage for demo (use database in production)
job_results = {}

@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to CrewAI Agent System",
        "endpoints": {
            "status": "/status",
            "kickoff": "/kickoff",
            "health": "/health"
        }
    }

@app.get("/status")
async def get_status():
    """Get crew status and configuration"""
    try:
        status = get_crew_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@app.post("/kickoff", response_model=CrewResponse)
async def kickoff_crew_endpoint(crew_input: CrewInput):
    """Start the crew workflow"""
    try:
        logger.info(f"Starting crew workflow for topic: {crew_input.topic}")
        
        # Prepare inputs for the crew
        inputs = {
            "topic": crew_input.topic
        }
        
        if crew_input.additional_context:
            inputs["additional_context"] = crew_input.additional_context
        
        # Execute crew workflow
        result = kickoff_crew(inputs)
        
        logger.info("Crew workflow completed")
        return CrewResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in kickoff endpoint: {str(e)}")
        return CrewResponse(
            status="error",
            result=None,
            message=f"Error starting crew workflow: {str(e)}"
        )

@app.post("/kickoff-async")
async def kickoff_crew_async(crew_input: CrewInput, background_tasks: BackgroundTasks):
    """Start crew workflow asynchronously"""
    import uuid
    
    job_id = str(uuid.uuid4())
    job_results[job_id] = {"status": "running", "result": None}
    
    def run_crew_background(inputs: dict, job_id: str):
        try:
            result = kickoff_crew(inputs)
            job_results[job_id] = result
        except Exception as e:
            job_results[job_id] = {
                "status": "error",
                "result": None,
                "message": f"Background job error: {str(e)}"
            }
    
    inputs = {"topic": crew_input.topic}
    if crew_input.additional_context:
        inputs["additional_context"] = crew_input.additional_context
    
    background_tasks.add_task(run_crew_background, inputs, job_id)
    
    return {"job_id": job_id, "status": "started", "message": "Crew workflow started in background"}

@app.get("/job/{job_id}")
async def get_job_result(job_id: str):
    """Get the result of an async job"""
    if job_id not in job_results:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_results[job_id]

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"message": f"Invalid input: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)