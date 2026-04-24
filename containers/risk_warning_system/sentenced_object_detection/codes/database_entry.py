import os
import uuid
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, Float, LargeBinary, and_, select, CheckConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy import select, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from urllib.parse import quote_plus
import logging

 
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
    image_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    image_path = Column(String, nullable=False)
    risk_detected = Column(Boolean)
    risk_level = Column(String, CheckConstraint("risk_level IN ('low','medium','high')"))
    risk_factors = Column(JSONB)
    explanation = Column(Text)
    created_at = Column(DateTime,server_default=func.now())

class SentencedObjectDetection(Base):
    __tablename__ = "sentenced_object_detection"
    risk_factor_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True),ForeignKey("risk_detection.image_id", ondelete="CASCADE"),nullable=False)
    risk_factor = Column(Text)
    detections = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

class JobDescriptions(Base):
    __tablename__ = "job_descriptions"
    job_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    description = Column(Text)

class ResumeIntelligence(Base):
    __tablename__ = "resume_intelligence"
    resume_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    resume_path = Column(String, nullable=False)
    extracted_field = Column(JSONB)
    user_field = Column(JSONB)
    recommended_jobs = Column(JSONB)
    created_at = Column(DateTime,server_default=func.now())

class ApplicationStatus(Base):
    __tablename__ = "application_status"
    application_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True),ForeignKey("job_descriptions.job_id", ondelete="CASCADE"))
    resume_id = Column(UUID(as_uuid=True),ForeignKey("resume_intelligence.resume_id", ondelete="CASCADE"))
    market_ctc = Column(Float)
    status = Column(Text,CheckConstraint("status IN ('selected','rejected')"))
    created_at = Column(DateTime,server_default=func.now())


def get_local_session():
    DB_USER = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT') 
    DB_NAME = os.getenv('DB_NAME')
    logging.info(f'{DB_USER},{DB_PASSWORD},{DB_HOST},{DB_PORT},{DB_NAME}')

    DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal, engine

def create_table(engine):
    # Create database table if not exists
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


def insert_uploaded_image(SessionLocal, image_id, image_path):

    session = SessionLocal()

    try:

        new_record = RiskDetection(
            image_id=image_id,
            image_path=image_path
        )

        session.add(new_record)
        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


# def get_image_path(SessionLocal, image_id):

#     session = SessionLocal()

#     try:

#         record = session.execute(
#             select(RiskDetection).where(RiskDetection.image_id == image_id)
#         ).scalar_one_or_none()

#         if record is None:
#             raise ValueError("Image not found")

#         return record.image_path

#     finally:
#         session.close()


def update_risk_detection(SessionLocal, image_id, result):

    session = SessionLocal()

    try:

        record = session.get(RiskDetection, image_id)

        if not record:
            raise ValueError("Image not found")

        record.risk_detected = result["risk_detected"]
        record.risk_level = result["risk_level"]
        record.risk_factors = result["risk_factors"]
        record.explanation = result["explanation"]

        session.commit()

    except SQLAlchemyError as e:

        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def get_risk_factors(SessionLocal, image_uuid):

    session = SessionLocal()

    try:
        # image_uuid = UUID(folder_name)

        stmt = select(RiskDetection.risk_factors).where(
            RiskDetection.image_id == image_uuid
        )

        result = session.execute(stmt).scalar_one_or_none()

        if result is None:
            print(f"No risk factors found for image_id: {image_uuid}")
            return []

        return result

    except Exception as e:
        print(f"Error fetching risk factors: {e}")
        return []

    finally:
        session.close()



def add_sentenced_detection(SessionLocal, image_uuid, final_output):

    session = SessionLocal()

    try:

        # image_uuid = UUID(folder_name)

        grounded_results = final_output.get("grounded_results", [])

        for item in grounded_results:

            risk_factor = item.get("sentence")

            detections = {
                "bboxes": item.get("bboxes", []),
                "labels": item.get("labels", [])
            }

            row = SentencedObjectDetection(
                image_id=image_uuid,
                risk_factor=risk_factor,
                detections=detections
            )

            session.add(row)

        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        print(f"DB Insert Error: {e}")

    finally:
        session.close()


if __name__ == "__main__":

    # create_table()
    
    # First insert
    SessionLocal, engine = get_local_session()
    id1 = add_data(SessionLocal=SessionLocal, project="project" , job_name="job_name", status="status")
    print(f"Inserted record ID: {id1}")
 
