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


def get_resume_fields(SessionLocal, resume_id):
    session = SessionLocal()

    try:
        resume_uuid = uuid.UUID(str(resume_id))

        stmt = select(ResumeIntelligence.extracted_field, ResumeIntelligence.user_field).where(
            ResumeIntelligence.resume_id == resume_uuid
        )
        row = session.execute(stmt).one_or_none()

        if row is None:
            raise ValueError(f"Resume not found for resume_id: {resume_id}")

        extracted_field, user_field = row
        return extracted_field or {}, user_field or {}

    finally:
        session.close()


def get_resume_user_field(SessionLocal, resume_id):
    session = SessionLocal()

    try:
        resume_uuid = uuid.UUID(str(resume_id))

        stmt = select(ResumeIntelligence.user_field).where(
            ResumeIntelligence.resume_id == resume_uuid
        )
        row = session.execute(stmt).one_or_none()

        if row is None:
            raise ValueError(f"Resume not found for resume_id: {resume_id}")

        (user_field,) = row
        return user_field or {}

    finally:
        session.close()


def update_market_ctc_by_resume(SessionLocal, resume_id, market_ctc):
    session = SessionLocal()

    try:
        resume_uuid = uuid.UUID(str(resume_id))

        stmt = select(ApplicationStatus).where(ApplicationStatus.resume_id == resume_uuid)
        records = session.execute(stmt).scalars().all()

        if not records:
            raise ValueError(f"No application_status rows found for resume_id: {resume_id}")

        for record in records:
            record.market_ctc = float(market_ctc)

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()
