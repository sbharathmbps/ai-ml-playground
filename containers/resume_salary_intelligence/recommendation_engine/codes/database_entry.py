import os
import uuid
import logging
from datetime import datetime
from urllib.parse import quote_plus

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    CheckConstraint,
    Text,
    ForeignKey,
    select,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func


Base = declarative_base()


class JobStatus(Base):
    __tablename__ = "jobs_status"
    job_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    status = Column(String(20),nullable=False)
    progress = Column(Integer,default=0)
    updated_at = Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    __table_args__ = (
    CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')",name="check_status"),
    CheckConstraint("progress >= 0 AND progress <= 100",name="check_progress"),
    )


class RiskDetection(Base):
    __tablename__ = "risk_detection"
    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_path = Column(String, nullable=False)
    risk_detected = Column(Boolean)
    risk_level = Column(String, CheckConstraint("risk_level IN ('low','medium','high')"))
    risk_factors = Column(JSONB)
    explanation = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class SentencedObjectDetection(Base):
    __tablename__ = "sentenced_object_detection"
    risk_factor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey("risk_detection.image_id", ondelete="CASCADE"), nullable=False)
    risk_factor = Column(Text)
    detections = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class JobDescriptions(Base):
    __tablename__ = "job_descriptions"
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text)


class ResumeIntelligence(Base):
    __tablename__ = "resume_intelligence"
    resume_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_path = Column(String, nullable=False)
    extracted_field = Column(JSONB)
    user_field = Column(JSONB)
    recommended_jobs = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class ApplicationStatus(Base):
    __tablename__ = "application_status"
    application_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.job_id", ondelete="CASCADE"))
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resume_intelligence.resume_id", ondelete="CASCADE"))
    market_ctc = Column(Float)
    status = Column(Text, CheckConstraint("status IN ('selected','rejected')"))
    created_at = Column(DateTime, server_default=func.now())


def get_local_session():
    db_user = os.getenv("DB_USERNAME")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    logging.info(f"{db_user},{db_password},{db_host},{db_port},{db_name}")

    database_url = f"postgresql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal, engine


def create_table(engine):
    Base.metadata.create_all(bind=engine)


def create_table_uvision(engine_uvision):
    Base.metadata.create_all(bind=engine_uvision)

def update_progress(SessionLocal, status, progress, job_id):
    session = SessionLocal()

    try:
        job = session.query(JobStatus).filter(JobStatus.job_id == job_id).first()

        if job:
            job.status = status
            job.progress = progress
        else:
            job = JobStatus(
                job_id=job_id,
                status=status,
                progress=progress
            )
            session.add(job)

        session.commit()
        session.refresh(job)

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def get_job_descriptions(SessionLocal):
    session = SessionLocal()

    try:
        stmt = select(JobDescriptions.job_id, JobDescriptions.description)
        rows = session.execute(stmt).all()
        return [(str(job_id), description) for job_id, description in rows]

    finally:
        session.close()


def update_recommended_jobs(SessionLocal, resume_id, recommended_jobs):
    session = SessionLocal()

    try:
        resume_uuid = uuid.UUID(str(resume_id))

        record = session.get(ResumeIntelligence, resume_uuid)
        if not record:
            raise ValueError(f"Resume not found for resume_id: {resume_id}")

        record.recommended_jobs = recommended_jobs
        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()
