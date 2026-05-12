from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import settings
from app.routers import analysis, reports


app = FastAPI(title=settings.app_name)

origins = ["*"] if settings.frontend_origin == "*" else [settings.frontend_origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(reports.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
