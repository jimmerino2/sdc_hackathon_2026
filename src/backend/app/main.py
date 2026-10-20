from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.llm.router import router as llm_router
from app.product.router import router as product_router


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

    app.include_router(llm_router)
    app.include_router(product_router)
    return app


app = create_app()
