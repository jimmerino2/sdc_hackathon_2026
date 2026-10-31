from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.auth.router import router as auth_router
from app.challenge.router import router as challenge_router
from app.config import get_settings
from app.forecast.router import router as forecast_router
from app.hive.router import router as hive_router
from app.hrd.router import router as hrd_router
from app.interests.router import router as interests_router
from app.jobs.router import router as jobs_router
from app.llm.router import router as llm_router
from app.llm_bench.router import router as llm_bench_router
from app.methodology.router import router as methodology_router
from app.occupational.router import router as occupational_router
from app.outlook.router import router as outlook_router
from app.profile.router import router as profile_router
from app.roadmap.router import router as roadmap_router
from app.resume.router import router as resume_router
from app.sdg.router import router as sdg_router
from app.social.router import router as social_router


def create_app() -> FastAPI:
    app = FastAPI(title="SDC Hackathon 2026")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def index():
        return RedirectResponse(url="/docs")

    app.include_router(auth_router)
    app.include_router(challenge_router)
    app.include_router(forecast_router)
    app.include_router(hive_router)
    app.include_router(hrd_router)
    app.include_router(interests_router)
    app.include_router(jobs_router)
    app.include_router(llm_router)
    app.include_router(llm_bench_router)
    app.include_router(methodology_router)
    app.include_router(occupational_router)
    app.include_router(outlook_router)
    app.include_router(profile_router)
    app.include_router(roadmap_router)
    app.include_router(resume_router)
    app.include_router(sdg_router)
    app.include_router(social_router)
    return app


app = create_app()
