import os
import uuid
from uuid6 import uuid7
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, Float, LargeBinary, and_, select
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy import select
from datetime import datetime
from urllib.parse import quote_plus
import logging

 
Base = declarative_base()
 
class JobStatus(Base):
    __tablename__ = "photos_jobstatus"
    id = Column(Integer , primary_key=True , autoincrement=True)
    project = Column(String(255))
    job_name = Column(String(255))
    op_name = Column(String(255), default = '')
    process_name = Column(String(255), default = '')
    status = Column(String(255), default = '')
    op_timestamp = Column(DateTime, nullable=True)
    future_attr1 = Column(String(127), default = '')
    future_attr2 = Column(String(127), default = '')
    future_attr3 = Column(String(127), default = '')
    future_attr4 = Column(String(127), default = '')
    created_at = Column(DateTime, default=datetime.now(), nullable=True)

class Detection(Base):
    __tablename__ = "detection_table"
    unique_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)    
    raw_image_id = Column(UUID(as_uuid=True))
    class_name = Column(String(255), default = '')
    human_annotated = Column(Boolean, default = False)
    machine_annotated = Column(Boolean, default = True)
    annotation_type = Column(String(255), default = '')
    x_min = Column(Float)
    y_min = Column(Float)
    x_max = Column(Float)
    y_max = Column(Float)
    mask = Column(JSON, nullable=True)
    score = Column(Float)
    additional_data = Column(JSON, nullable=True)    
    visible = Column(Boolean, default = True)  
    old_annotation = Column(UUID(as_uuid=True)) 
    visual_name = Column(String(255), default = '')
    detection_type = Column(String(255), default = '')
    model_id = Column(UUID(as_uuid=True))
    detected_asset_id = Column(UUID(as_uuid=True))

class Damage_Detection(Base):
    __tablename__ = "damage_consolidation"
    unique_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)    
    raw_image_id = Column(UUID(as_uuid=True))
    good_portion_percentage = Column(Float)
    severe_damage_percentage = Column(Float)
    moderate_damage_percentage = Column(Float)
    low_damage_percentage = Column(Float)
    total_damage_percentage = Column(Float)
    damaged_or_not = Column(String(255), default = '')
    human_annotated = Column(Boolean, default = False)
    machine_annotated = Column(Boolean, default = True)
    visible = Column(Boolean, default = True)  
    old_annotation = Column(UUID(as_uuid=True)) 
    particular_damage_data = Column(JSON, nullable=True)
    detected_asset_id = Column(UUID(as_uuid=True))
    damage_type = Column(String(255), default = '')
    tilt = Column(Float, nullable=True)
    model_id = Column(UUID(as_uuid=True))

class Image_Master(Base):
    __tablename__ = "image_master_table"
    unique_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)    
    raw_image_name = Column(String(255), default = '')
    raw_image_url = Column(String(255), default = '')
    workorder_id = Column(Integer)
    asset_id = Column(Integer)
    lat = Column(Float)
    long = Column(Float)
    additional_data = Column(JSON, nullable=True)  

class Model_Master(Base):
    __tablename__ = "ml_model_master"
    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)    
    model_name = Column(String(255), default = '')
    utility_name = Column(String(255), default = '')
    detection_type = Column(String(255), default = '')
    additional_info = Column(JSON, nullable=True) 


def get_local_session():
    DB_USER = os.getenv('DB2_uvision_ia_frontend_USERNAME')
    DB_PASSWORD = os.getenv('DB2_uvision_ia_frontend_PASSWORD')
    DB_HOST = os.getenv('DB2_uvision_ia_frontend_HOST')
    DB_PORT = os.getenv('DB2_uvision_ia_frontend_PORT', '5432') 
    DB_NAME = os.getenv('DB2_uvision_ia_frontend_DB_NAME')
    logging.info(f'{DB_USER},{DB_PASSWORD},{DB_HOST},{DB_PORT},{DB_NAME}')

    DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal, engine


def get_local_session_uvision():
    DB_USER = os.getenv('DB_uvision_USERNAME')
    DB_PASSWORD = os.getenv('DB_uvision_PASSWORD')
    DB_HOST = os.getenv('DB_uvision_HOST')
    DB_PORT = os.getenv('DB_uvision_PORT', '5432')  
    DB_NAME = os.getenv('DB_uvision_DB_NAME')
    logging.info(f'{DB_USER},{DB_PASSWORD},{DB_HOST},{DB_PORT},{DB_NAME}')

    DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    engineUvision = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocalUvision = sessionmaker(autocommit=False, autoflush=False, bind=engineUvision)
    return SessionLocalUvision, engineUvision

def create_table(engine):
    # Create database table if not exists
    Base.metadata.create_all(bind=engine)
 
def create_table_uvision(engineUvision):
    # Create database table if not exists
    Base.metadata.create_all(bind=engineUvision)


def add_data(SessionLocal, project: str, job_name: str, status: str):

    session = SessionLocal()
    try:
        new_record = JobStatus(project=project, job_name=job_name, process_name='', status=status)
        session.add(new_record)
        session.commit()
        return new_record.id
    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e
    finally:
        session.close()
 

def add_detection_data(SessionLocal, detection_list, model_path, utility_name):

    session = SessionLocal()
    try:
        if model_path:
            model_id = get_model_id(SessionLocal, model_path, detection_list[0]["detection_type"], utility_name)
        else:
            model_id = None

        for detection in detection_list:
            new_record = Detection(
                raw_image_id=str(detection["raw_image_id"]), 
                class_name=detection["class_name"], 
                model_id=model_id,                
                x_min=detection["x_min"], 
                y_min=detection["y_min"], 
                x_max=detection["x_max"], 
                y_max=detection["y_max"], 
                score=detection["score"],
                mask=detection["mask"],
                visible=detection["visible"],
                visual_name=detection["visual_name"],                
                detection_type=detection["detection_type"],
                annotation_type=detection["annotation_type"],
                detected_asset_id=detection["detected_asset_id"]
                )
            session.add(new_record)
            session.flush()
        session.commit()
        return None
    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e
    finally:
        session.close()
 

def add_damage_detection_data(SessionLocal, detection_list, model_path, utility_name):

    session = SessionLocal()
    try:
        if model_path:
            model_id = get_model_id(SessionLocal, model_path, detection_list[0]["damage_type"], utility_name)
        else:
            model_id = None
            
        for detection in detection_list:
            new_record = Damage_Detection(
                raw_image_id=str(detection["raw_image_id"]), 
                detected_asset_id=detection["detected_asset_id"], 
                model_id=model_id,
                tilt=detection["tilt"],
                low_damage_percentage=detection["low_damage_percentage"],
                good_portion_percentage=detection["good_portion_percentage"], 
                severe_damage_percentage=detection["severe_damage_percentage"], 
                moderate_damage_percentage=detection["moderate_damage_percentage"], 
                total_damage_percentage=detection["total_damage_percentage"],
                particular_damage_data=detection["particular_damage_data"],
                damaged_or_not=detection["damaged_or_not"],
                visible=detection["visible"],
                damage_type=detection["damage_type"]               
                )
            session.add(new_record)
            session.flush()
        session.commit()
        return None
    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error: {str(e)}") from e
    finally:
        session.close() 



def get_image_id(SessionLocal, workorder_id, detection_type, class_name, data_from_db):
        
    session = SessionLocal()
    try:      
        queried_rows = session.query(Image_Master).filter(Image_Master.workorder_id == workorder_id).all()

        if queried_rows:
            image_ids = [{"unique_id": row.unique_id, "raw_image_name": row.raw_image_name} for row in queried_rows]
        else:
            logging.info(f"No image found for workorder_id: {workorder_id}")
            image_ids = None

        # if detection_type == "asset" and not data_from_db:
        if not data_from_db:
            return image_ids
        else:
            queried_rows = (
                session.query(Detection, Image_Master)
                .join(Image_Master, Detection.raw_image_id == Image_Master.unique_id)
                .filter(
                    Image_Master.workorder_id == workorder_id,
                    Detection.class_name.in_(class_name)
                )
                .all()
            )

            if queried_rows:
                filtered_image_ids = [{"unique_id": det.unique_id, 
                                       "raw_image_id": det.raw_image_id,
                                       "x_min": det.x_min,
                                       "y_min": det.y_min,
                                       "x_max": det.x_max,
                                       "y_max": det.y_max,
                                       "visual_name": det.visual_name,
                                       "detected_asset_id": det.detected_asset_id,
                                       "raw_image_name": img.raw_image_name}
                                       for det, img in queried_rows]                   
            else:
                logging.info(f"No image found for workorder_id: {workorder_id} and class_name: {class_name}")
                filtered_image_ids = None
            return filtered_image_ids
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e
    finally:
        session.close()


def get_model_id(SessionLocal, model_path, detection_type, utility_name):

    session = SessionLocal()
    try:
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        # Check if model already exists
        existing_model = session.execute(select(Model_Master).where(Model_Master.model_name == model_name)).scalar_one_or_none()
 
        if existing_model:
            model_id = existing_model.model_id
            logging.info(f"Model '{model_name}' found in DB with ID: {model_id}")
        else:
            # Create new model entry
            new_model = Model_Master(model_name=model_name, detection_type=detection_type, utility_name=utility_name)
            session.add(new_model)
            session.commit()
            session.refresh(new_model)
            model_id = new_model.model_id
            logging.info(f"Model '{model_name}' added to DB with new ID: {model_id}")
 
        return model_id
 
    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database error while getting model ID: {str(e)}") from e
    finally:
        session.close()


def get_annotations_from_db(SessionLocal, detection_id):

    session = SessionLocal()
    try:      
        queried_rows = session.query(Detection).filter(Detection.detected_asset_id == detection_id, Detection.annotation_type == "mask").all()

        if queried_rows:
            mask_list = [row.mask for row in queried_rows]
        else:
            logging.info(f"No mask found for detection_id: {detection_id}")
            mask_list = []
        
        return mask_list
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e
    finally:
        session.close()



def get_tilt_box_from_db(SessionLocal, image_id):

    session = SessionLocal()
    try:
        # Step 1: Filter Detection table
        subquery = (
            session.query(Detection.unique_id)
            .filter(
                Detection.raw_image_id == image_id,
                Detection.class_name.in_(['pole_concrete', 'pole_wooden', 'pole_metal'])
            )
            .subquery()
        )
 
        # Step 2: Join with DamageConsolidation table using detected_asset_id
        queried_rows = (
            session.query(Damage_Detection)
            .filter(
                Damage_Detection.detected_asset_id.in_(select(subquery)),
                Damage_Detection.damage_type == "tilt"
            )
            .first()
        )
 
        # Step 3: Extract data
        if queried_rows:
            box_data = queried_rows.particular_damage_data
        else:
            logging.info(f"No data found for image_id: {image_id}")
            box_data = {}
 
        return box_data
 
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error: {str(e)}") from e
 
    finally:
        session.close()


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