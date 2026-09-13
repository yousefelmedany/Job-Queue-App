from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database import Base, SessionLocal, engine
from app.models import Job
from app.schemas import JobCreate, JobResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Background Job Queue", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.post("/jobs", response_model=JobResponse, status_code=202)
def create_job(request: JobCreate):
    with SessionLocal.begin() as session:
        values = request.model_dump()
        statement = (
            insert(Job)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[Job.idempotency_key])
            .returning(Job.id)
        )
        job_id = session.scalar(statement)
        if job_id is None:
            job = session.scalar(select(Job).where(Job.idempotency_key == request.idempotency_key))
        else:
            job = session.get(Job, job_id)
        return job


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID):
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job


@app.get("/health")
def health():
    return {"status": "ok"}
