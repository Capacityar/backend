from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, create_db_tables
from app.modules.attempts.router import router as attempts_router, student_attempts_router
from app.modules.gap_analysis.router import router as gap_analysis_router, student_gap_analyses_router
from app.modules.job_descriptions.router import router as job_descriptions_router
from app.modules.learning_paths.router import router as learning_paths_router, student_paths_router
from app.modules.skills.router import router as skills_router
from app.modules.skills.seed import seed_skills_if_empty
from app.modules.user_skills.router import router as user_skills_router
from app.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_tables()
    db = SessionLocal()
    try:
        seed_skills_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(users_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(job_descriptions_router, prefix="/api")
app.include_router(learning_paths_router, prefix="/api")
app.include_router(student_paths_router, prefix="/api")
app.include_router(attempts_router, prefix="/api")
app.include_router(student_attempts_router, prefix="/api")
app.include_router(gap_analysis_router, prefix="/api")
app.include_router(student_gap_analyses_router, prefix="/api")
app.include_router(user_skills_router, prefix="/api")
