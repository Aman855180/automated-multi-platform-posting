"""FastAPI entry point for the Automated Multi-Platform Posting System.

Endpoints:
- POST /posting: Automatically publishes message across 5+ platforms concurrently.
- GET /health: Service health and configured platform status check.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("automated_posting")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for startup and shutdown logging."""
    logger.info("Starting Automated Multi-Platform Posting System on port %s", settings.APP_PORT)
    yield
    logger.info("Shutting down Automated Multi-Platform Posting System.")


app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description=(
        "Production-minded REST API that receives a short message with a CTA link "
        "and automatically publishes it across at least five third-party platforms concurrently."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Posting service instance
posting_service = PostingService(config=settings)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint providing service metadata."""
    return {
        "service": "Automated Multi-Platform Posting System",
        "version": "1.0.0",
        "documentation": "/docs",
        "posting_endpoint": "/posting",
        "status": "operational",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint displaying configured target platforms."""
    platform_names = [p.name for p in posting_service.platforms]
    return {
        "status": "healthy",
        "target_platforms_count": len(platform_names),
        "target_platforms": platform_names,
    }


@app.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    tags=["Posting"],
    summary="Publish message across all target platforms concurrently",
    response_description="Consolidated results from all integrated platforms",
)
async def post_message(payload: PostingRequest) -> PostingResponse:
    """Accept a validated marketing or update message containing exactly one CTA URL

    and publish it across all integrated platforms concurrently.
    """
    try:
        response = await posting_service.publish_message(payload.message)
        return response
    except Exception as exc:
        logger.exception("Unexpected error in /posting endpoint handler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {str(exc)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=(settings.APP_ENV == "development"),
    )
