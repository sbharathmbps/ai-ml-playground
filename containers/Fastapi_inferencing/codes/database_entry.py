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
from uuid import UUID as uuid_UUID

 
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
    status = Column(Text,CheckConstraint("status IN ('applied','selected','rejected')"))
    created_at = Column(DateTime,server_default=func.now())

class TrafficInspection(Base):
    __tablename__ = "traffic_inspection"
    video_id = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    video_path = Column(String, nullable=False)
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
 
def create_table_uvision(engineUvision):
    # Create database table if not exists
    Base.metadata.create_all(bind=engineUvision)


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

def get_job_status(SessionLocal, job_id):
    session = SessionLocal()
    try:
        job = session.query(JobStatus).filter(JobStatus.job_id == job_id).first()
        if job is None:
            return None
        return {"status": job.status, "progress": job.progress}
    finally:
        session.close()

#================================ Risk warning system ==========================================

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


def get_risk_factors(SessionLocal, folder_name):

    session = SessionLocal()

    try:
        image_uuid = UUID(folder_name)

        stmt = select(RiskDetection.risk_factors).where(
            RiskDetection.image_id == image_uuid
        )

        result = session.execute(stmt).scalar_one_or_none()

        if result is None:
            print(f"No risk factors found for image_id: {folder_name}")
            return []

        return result

    except Exception as e:
        print(f"Error fetching risk factors: {e}")
        return []

    finally:
        session.close()



def add_sentenced_detection(SessionLocal, folder_name, final_output):

    session = SessionLocal()

    try:

        image_uuid = UUID(folder_name)

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


def get_risk_warning_outcomes(SessionLocal, image_id):

    session = SessionLocal()

    try:
        image_uuid = uuid_UUID(str(image_id))

        risk_stmt = select(
            RiskDetection.image_id,
            RiskDetection.image_path,
            RiskDetection.risk_detected,
            RiskDetection.risk_level,
            RiskDetection.risk_factors,
            RiskDetection.explanation
        ).where(RiskDetection.image_id == image_uuid)

        risk_row = session.execute(risk_stmt).first()

        if risk_row is None:
            return None

        detection_stmt = select(
            SentencedObjectDetection.risk_factor,
            SentencedObjectDetection.detections
        ).where(SentencedObjectDetection.image_id == image_uuid)

        detection_rows = session.execute(detection_stmt).all()

        sentenced_detections = []
        detections_by_risk_factor = {}

        for row in detection_rows:
            detection_item = {
                "risk_factor": row[0],
                "detections": row[1] or {"bboxes": [], "labels": []}
            }
            sentenced_detections.append(detection_item)
            detections_by_risk_factor[row[0]] = detection_item["detections"]

        return {
            "image_id": str(risk_row[0]),
            "image_path": risk_row[1],
            "risk_detected": risk_row[2],
            "risk_level": risk_row[3],
            "risk_factors": risk_row[4] or [],
            "explanation": risk_row[5],
            "sentenced_detections": sentenced_detections,
            "detections_by_risk_factor": detections_by_risk_factor
        }

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()

#================================ Resume salary intelligence ==========================================

def insert_uploaded_resume(SessionLocal, resume_id, resume_path):

    session = SessionLocal()

    try:

        new_record = ResumeIntelligence(
            resume_id=resume_id,
            resume_path=resume_path
        )

        session.add(new_record)
        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def get_resume_fields(SessionLocal, resume_id):

    session = SessionLocal()

    try:
        resume_uuid = uuid_UUID(str(resume_id))
        stmt = select(
            ResumeIntelligence.extracted_field,
            ResumeIntelligence.user_field
        ).where(ResumeIntelligence.resume_id == resume_uuid)
        result = session.execute(stmt).first()

        if result is None:
            return None

        extracted_field = result[0] or {}
        user_field = result[1] or {}

        # Show user-updated values first, fallback to extracted values.
        prefilled_fields = extracted_field.copy()
        prefilled_fields.update(user_field)

        return {
            "resume_id": str(resume_uuid),
            "extracted_field": extracted_field,
            "user_field": user_field,
            "prefilled_field": prefilled_fields
        }

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def update_user_fields(SessionLocal, resume_id, user_field):

    session = SessionLocal()

    try:
        resume_uuid = uuid_UUID(str(resume_id))
        record = session.get(ResumeIntelligence, resume_uuid)

        if not record:
            return False

        record.user_field = user_field
        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def get_recommended_jobs(SessionLocal, resume_id):

    session = SessionLocal()

    try:
        resume_uuid = uuid_UUID(str(resume_id))
        stmt = select(ResumeIntelligence.recommended_jobs).where(
            ResumeIntelligence.resume_id == resume_uuid
        )
        result = session.execute(stmt).scalar_one_or_none()

        if result is None:
            return None

        recommended_jobs_mapped = []

        if isinstance(result, dict):
            for rank, value in result.items():
                job_id = None
                description = None
                score = None

                if isinstance(value, dict):
                    job_id = value.get("job_id")
                    description = value.get("description")
                    score = value.get("score")
                elif isinstance(value, str):
                    try:
                        uuid_UUID(value)
                        job_id = value
                    except ValueError:
                        description = value

                recommended_jobs_mapped.append(
                    {
                        "rank": rank,
                        "job_id": job_id,
                        "description": description,
                        "score": score
                    }
                )

        return {
            "resume_id": str(resume_uuid),
            "recommended_jobs": result or [],
            "recommended_jobs_mapped": recommended_jobs_mapped
        }

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def apply_for_job(SessionLocal, resume_id, job_id):

    session = SessionLocal()

    try:
        resume_uuid = uuid_UUID(str(resume_id))
        job_uuid = uuid_UUID(str(job_id))

        resume_record = session.get(ResumeIntelligence, resume_uuid)
        if not resume_record:
            return {"success": False, "reason": "resume_not_found"}

        job_record = session.get(JobDescriptions, job_uuid)
        if not job_record:
            return {"success": False, "reason": "job_not_found"}

        application_record = ApplicationStatus(
            resume_id=resume_uuid,
            job_id=job_uuid,
            status="applied"
        )

        session.add(application_record)
        session.commit()

        return {
            "success": True,
            "application_id": str(application_record.application_id)
        }

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def get_hr_applications(SessionLocal, status=None):

    session = SessionLocal()

    try:
        stmt = select(
            ApplicationStatus.application_id,
            ApplicationStatus.resume_id,
            ApplicationStatus.job_id,
            ApplicationStatus.market_ctc,
            ApplicationStatus.status,
            ApplicationStatus.created_at,
            ResumeIntelligence.resume_path,
            ResumeIntelligence.user_field,
            JobDescriptions.description
        ).join(
            ResumeIntelligence,
            ApplicationStatus.resume_id == ResumeIntelligence.resume_id
        ).join(
            JobDescriptions,
            ApplicationStatus.job_id == JobDescriptions.job_id
        )

        if status is not None:
            stmt = stmt.where(ApplicationStatus.status == status)

        rows = session.execute(stmt).all()

        result = []
        for row in rows:
            result.append(
                {
                    "application_id": str(row[0]),
                    "resume_id": str(row[1]),
                    "job_id": str(row[2]),
                    "market_ctc": row[3],
                    "status": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "resume_path": row[6],
                    "user_field": row[7] or {},
                    "job_description": row[8]
                }
            )

        return result

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def update_application_status(SessionLocal, application_id, status):

    session = SessionLocal()

    try:
        application_uuid = uuid_UUID(str(application_id))
        record = session.get(ApplicationStatus, application_uuid)

        if not record:
            return False

        record.status = status
        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def find_existing_market_ctc(SessionLocal, resume_id):

    session = SessionLocal()

    try:
        resume_uuid = uuid_UUID(str(resume_id))

        stmt = select(ApplicationStatus.market_ctc).where(
            ApplicationStatus.resume_id == resume_uuid,
            ApplicationStatus.market_ctc.is_not(None)
        )
        return session.execute(stmt).scalar_one_or_none()

    finally:
        session.close()


def update_application_market_ctc(SessionLocal, application_id, market_ctc):

    session = SessionLocal()

    try:
        application_uuid = uuid_UUID(str(application_id))
        record = session.get(ApplicationStatus, application_uuid)

        if not record:
            return False

        record.market_ctc = float(market_ctc)
        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e

    finally:
        session.close()


def get_application_market_ctc(SessionLocal, application_id):

    session = SessionLocal()

    try:
        application_uuid = uuid_UUID(str(application_id))

        stmt = select(
            ApplicationStatus.application_id,
            ApplicationStatus.resume_id,
            ApplicationStatus.job_id,
            ApplicationStatus.market_ctc,
            ApplicationStatus.status
        ).where(ApplicationStatus.application_id == application_uuid)

        row = session.execute(stmt).first()

        if row is None:
            return None

        return {
            "application_id": str(row[0]),
            "resume_id": str(row[1]),
            "job_id": str(row[2]),
            "market_ctc": row[3],
            "status": row[4]
        }

    finally:
        session.close()


# def insert_uploaded_video(SessionLocal, video_id, video_path):

#     session = SessionLocal()

#     try:

#         new_record = TrafficInspection(
#             video_id=video_id,
#             video_path=video_path
#         )

#         session.add(new_record)
#         session.commit()

#     except SQLAlchemyError as e:
#         session.rollback()
#         raise RuntimeError(f"Database error: {str(e)}") from e

#     finally:
#         session.close()
        

if __name__ == "__main__":

    # create_table()
    
    # First insert
    SessionLocal, engine = get_local_session()
    id1 = add_data(SessionLocal=SessionLocal, project="project" , job_name="job_name", status="status")
    print(f"Inserted record ID: {id1}")
 
    # First insert
    SessionLocalUvision, engineUvision = get_local_session_uvision()
    id1 = add_detection_data(SessionLocalUvision, class_name="pole", x_min=23, y_min=41, x_max=57, y_max=64, score=99)
    # id1 = add_damage_detection_data(SessionLocal, good_portion_percentage=24, severe_damage_percentage=24, moderate_damage_percentage=24, low_damage_percentage=24, damaged_or_not="yes")
