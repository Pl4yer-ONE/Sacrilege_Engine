"""FastAPI application for Sacrilege Engine."""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import get_settings
from src.analysis_orchestrator import AnalysisOrchestrator


# Pydantic models for API responses
class DemoUploadResponse(BaseModel):
    demo_id: str
    status: str
    message: str


class AnalysisStatusResponse(BaseModel):
    demo_id: str
    status: str
    progress: int = 0
    error: Optional[str] = None


class MistakeResponse(BaseModel):
    title: str
    description: str
    fix: str
    rounds: list[int]
    category: str
    severity: str


class FixesResponse(BaseModel):
    mechanical: Optional[str]
    tactical: Optional[str]
    mental: Optional[str]


class ReportResponse(BaseModel):
    player_id: str
    player_name: str
    top_mistakes: list[MistakeResponse]
    fixes: FixesResponse
    scores: dict[str, float]


# In-memory storage (replace with DB in production)
demo_storage: dict[str, dict] = {}


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Sacrilege Engine",
        description="CS2 Demo Decision Intelligence System",
        version="0.1.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Ensure upload directory exists
    settings.demo_upload_dir.mkdir(parents=True, exist_ok=True)
    
    @app.get("/")
    async def root():
        return {"name": "Sacrilege Engine", "version": "0.1.0"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.post("/v1/demos/upload", response_model=DemoUploadResponse)
    async def upload_demo(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...)
    ):
        """Upload a demo file for analysis."""
        # Validate file extension
        if not file.filename.endswith('.dem'):
            raise HTTPException(400, "File must be a .dem file")
        
        # Generate demo ID
        demo_id = str(uuid.uuid4())
        
        # Save file
        file_path = settings.demo_upload_dir / f"{demo_id}.dem"
        
        try:
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            raise HTTPException(500, f"Failed to save file: {e}")
        
        # Store status
        demo_storage[demo_id] = {
            "status": "processing",
            "file_path": str(file_path),
            "progress": 0,
            "error": None,
            "result": None,
        }
        
        # Queue analysis
        background_tasks.add_task(run_analysis, demo_id, file_path)
        
        return DemoUploadResponse(
            demo_id=demo_id,
            status="processing",
            message="Demo uploaded. Analysis started."
        )
    
    @app.get("/v1/demos/{demo_id}/status", response_model=AnalysisStatusResponse)
    async def get_status(demo_id: str):
        """Get analysis status."""
        if demo_id not in demo_storage:
            raise HTTPException(404, "Demo not found")
        
        data = demo_storage[demo_id]
        
        return AnalysisStatusResponse(
            demo_id=demo_id,
            status=data["status"],
            progress=data["progress"],
            error=data["error"],
        )
    
    @app.get("/v1/demos/{demo_id}/report")
    async def get_report(demo_id: str, player_id: Optional[str] = None):
        """Get analysis report."""
        if demo_id not in demo_storage:
            raise HTTPException(404, "Demo not found")
        
        data = demo_storage[demo_id]
        
        if data["status"] != "complete":
            raise HTTPException(400, f"Analysis not complete. Status: {data['status']}")
        
        result = data["result"]
        
        if not result or not result.player_reports:
            raise HTTPException(500, "No analysis results available")
        
        # Get specific player or first player
        if player_id:
            if player_id not in result.player_reports:
                raise HTTPException(404, f"Player {player_id} not found")
            report = result.player_reports[player_id]
        else:
            report = list(result.player_reports.values())[0]
        
        # Convert to response format
        mistakes = [
            MistakeResponse(
                title=m.title,
                description=m.description,
                fix=m.fix,
                rounds=m.rounds,
                category=m.category.value,
                severity=m.severity.value,
            )
            for m in report.top_mistakes
        ]
        
        return ReportResponse(
            player_id=report.player_id,
            player_name=report.player_name,
            top_mistakes=mistakes,
            fixes=FixesResponse(
                mechanical=report.mechanical_fix,
                tactical=report.tactical_fix,
                mental=report.mental_fix,
            ),
            scores=report.scores,
        )
    
    @app.get("/v1/demos/{demo_id}/players")
    async def get_players(demo_id: str):
        """Get list of players in demo."""
        if demo_id not in demo_storage:
            raise HTTPException(404, "Demo not found")
        
        data = demo_storage[demo_id]
        
        if data["status"] != "complete":
            raise HTTPException(400, "Analysis not complete")
        
        result = data["result"]
        
        if not result or not result.player_reports:
            return {"players": []}
        
        players = [
            {"id": pid, "name": report.player_name}
            for pid, report in result.player_reports.items()
        ]
        
        return {"players": players}
    
    return app


def run_analysis(demo_id: str, file_path: Path):
    """Run analysis in background."""
    try:
        demo_storage[demo_id]["progress"] = 10
        
        orchestrator = AnalysisOrchestrator()
        
        demo_storage[demo_id]["progress"] = 30
        
        result = orchestrator.analyze(file_path)
        
        demo_storage[demo_id]["progress"] = 100
        
        if result.success:
            demo_storage[demo_id]["status"] = "complete"
            demo_storage[demo_id]["result"] = result
        else:
            demo_storage[demo_id]["status"] = "failed"
            demo_storage[demo_id]["error"] = result.error
            
    except Exception as e:
        demo_storage[demo_id]["status"] = "failed"
        demo_storage[demo_id]["error"] = str(e)


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
