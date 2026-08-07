import datetime
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Set

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from ai_analyzer import analyze_resources
from auth import create_access_token, get_current_user, hash_password, verify_password
from aws_scanner import list_aws_regions, scan_aws_resources
from db import create_user, get_user_analyses, get_user_by_email, init_db, save_analysis
from exceptions import register_exception_handlers
from logger import logger
from models import (
    AnalysisHistoryResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    AuthTokenResponse,
    RegionsResponse,
    UserAuthRequest,
    WebSocketProgressMessage,
)




class ConnectionManager:
    """Manages active WebSocket connections for analysis progress tracking."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, analysis_id: str):
        await websocket.accept()
        if analysis_id not in self.active_connections:
            self.active_connections[analysis_id] = set()
        self.active_connections[analysis_id].add(websocket)
        logger.info(f"WebSocket client connected for analysis_id: '{analysis_id}'")

    def disconnect(self, websocket: WebSocket, analysis_id: str):
        if analysis_id in self.active_connections:
            self.active_connections[analysis_id].discard(websocket)
            if not self.active_connections[analysis_id]:
                del self.active_connections[analysis_id]
        logger.info(f"WebSocket client disconnected for analysis_id: '{analysis_id}'")

    async def send_progress(self, analysis_id: str, stage: str, progress_percent: int):
        if analysis_id in self.active_connections:
            msg = WebSocketProgressMessage(
                analysis_id=analysis_id,
                stage=stage,
                progress_percent=progress_percent,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
            dead_sockets = set()
            for ws in self.active_connections[analysis_id]:
                try:
                    await ws.send_text(msg.model_dump_json())
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message: {str(e)}")
                    dead_sockets.add(ws)

            for ws in dead_sockets:
                self.disconnect(ws, analysis_id)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing database on startup."""
    logger.info("Initializing application database...")
    await init_db()
    yield
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="AI Cloud Cost Detective API",
    description="FastAPI Backend for scanning AWS resources, analyzing costs with OpenRouter AI, saving history to PostgreSQL, and streaming live progress updates via WebSockets.",
    version="3.0.0",
    lifespan=lifespan
)

# Register CORS middleware for http://localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom error exception handlers
register_exception_handlers(app)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint verifying API service status."""
    return {"status": "ok", "service": "AI Cloud Cost Detective API", "version": "3.0.0"}


@app.post("/api/auth/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserAuthRequest):
    """
    POST /api/auth/signup
    Accepts email and password, hashes password using bcrypt, stores user, and returns JWT access token.
    """
    logger.info(f"Signup attempt for email: '{user_data.email}'")
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    pwd_hash = hash_password(user_data.password)
    user = await create_user(user_data.email, pwd_hash)

    token = create_access_token(data={"sub": user["email"], "user_id": user["id"]})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": user["id"], "email": user["email"]}
    )


@app.post("/api/auth/login", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
async def login(user_data: UserAuthRequest):
    """
    POST /api/auth/login
    Validates user credentials and returns a JWT access token.
    """
    logger.info(f"Login attempt for email: '{user_data.email}'")
    user = await get_user_by_email(user_data.email)
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    token = create_access_token(data={"sub": user["email"], "user_id": user["id"]})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": user["id"], "email": user["email"]}
    )



@app.get("/api/regions", response_model=RegionsResponse, status_code=status.HTTP_200_OK)
def get_regions(current_user: dict = Depends(get_current_user)):
    """
    Fetch the list of all available AWS regions using 'aws ec2 describe-regions'.
    """
    logger.info(f"Received request for GET /api/regions from user: {current_user.get('sub')}")
    return list_aws_regions()


@app.get("/api/history", response_model=AnalysisHistoryResponse, status_code=status.HTTP_200_OK)
async def get_history(current_user: dict = Depends(get_current_user)):
    """
    Returns previous AWS cloud cost analysis history from PostgreSQL.
    """
    user_id = current_user.get("user_id")
    logger.info(f"Received request for GET /api/history from user_id: {user_id}")
    records = await get_user_analyses(user_id=user_id)
    return AnalysisHistoryResponse(history=records, count=len(records))


@app.websocket("/ws/progress/{analysis_id}")
async def websocket_progress_endpoint(websocket: WebSocket, analysis_id: str):
    """
    WebSocket endpoint streaming real-time scan and AI analysis progress updates to the frontend.
    """
    await manager.connect(websocket, analysis_id)
    try:
        while True:
            # Keep connection alive until closed by client
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, analysis_id)


@app.post("/api/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_region(request: AnalyzeRequest, current_user: dict = Depends(get_current_user)):
    """
    Performs IAM verification, scans AWS resources, queries Cost Explorer, runs OpenRouter AI cost analysis,
    streams real-time progress via WebSockets, and stores history in PostgreSQL.
    """
    start_time = time.time()
    user_id = current_user.get("user_id")
    analysis_id = request.analysis_id or f"scan-{uuid.uuid4().hex[:10]}"
    logger.info(f"Received POST /api/analyze for region: '{request.region}' by user_id: '{user_id}' (analysis_id: '{analysis_id}')")

    # Stage 1: Verifying credentials
    await manager.send_progress(analysis_id, "Verifying AWS credentials...", 10)

    # Stage 2: Fetching AWS regions
    await manager.send_progress(analysis_id, "Fetching AWS regions...", 25)

    # Stage 3: Scanning AWS resources
    await manager.send_progress(analysis_id, f"Scanning AWS resources in {request.region}...", 50)
    caller_identity, resources, summary, cost_analysis = scan_aws_resources(request.region)

    # Stage 4: AI Cloud Cost Analysis
    await manager.send_progress(analysis_id, "Analyzing cloud costs with AI...", 75)
    ai_analysis = analyze_resources(
        resources=[r.model_dump() for r in resources],
        region=request.region,
        account_id=caller_identity.account_id,
        summary_counts=summary.model_dump()
    )

    # Stage 5: Storing analysis results
    await manager.send_progress(analysis_id, "Storing analysis results...", 90)

    response_payload = AnalyzeResponse(
        analysis_id=analysis_id,
        caller_identity=caller_identity,
        region=request.region,
        execution_time_seconds=round(time.time() - start_time, 2),
        summary=summary,
        cost_analysis=cost_analysis,
        ai_analysis=ai_analysis,
        resources=resources
    )

    est_savings_str = f"${ai_analysis.total_estimated_monthly_savings:.2f}"
    await save_analysis(
        analysis_id=analysis_id,
        region=request.region,
        resources_scanned=summary.total_resources,
        issues_found=len(ai_analysis.issues),
        estimated_monthly_savings=est_savings_str,
        analysis_result=response_payload.model_dump(),
        status="completed",
        user_id=user_id
    )

    # Stage 6: Analysis complete
    await manager.send_progress(analysis_id, "Analysis complete.", 100)

    execution_time = round(time.time() - start_time, 2)
    logger.info(f"POST /api/analyze completed in {execution_time}s for analysis_id: '{analysis_id}'")

    return response_payload



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
