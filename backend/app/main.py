import time

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.services.aws_scanner import (
    list_aws_regions,
    scan_aws_resources,
)
from app.services.ai_analyzer import analyze_resources
from app.exceptions import register_exception_handlers
from app.logger import logger
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    RegionsResponse,
)

app = FastAPI(
    title="AI Cloud Cost Detective API",
    description="FastAPI Backend for scanning AWS cloud resources, analyzing costs, and generating AI optimization recommendations.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "ok",
        "service": "AI Cloud Cost Detective API",
        "version": "2.1.0",
    }


@app.get(
    "/api/regions",
    response_model=RegionsResponse,
    status_code=status.HTTP_200_OK,
)
def get_regions():
    logger.info("GET /api/regions")
    return list_aws_regions()


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_region(request: AnalyzeRequest):

    start_time = time.time()

    logger.info(f"Scanning AWS Region: {request.region}")

    caller_identity, resources, summary, cost_analysis = scan_aws_resources(
        request.region
    )

    logger.info("Generating AI Analysis...")

    ai_analysis = analyze_resources(
        resources,
        request.region,
    )

    execution_time = round(time.time() - start_time, 2)

    logger.info(f"Completed in {execution_time}s")

    response = AnalyzeResponse(
        caller_identity=caller_identity,
        region=request.region,
        execution_time_seconds=execution_time,
        summary=summary,
        cost_analysis=cost_analysis,
        resources=resources,
        ai_analysis=ai_analysis,
    )

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )