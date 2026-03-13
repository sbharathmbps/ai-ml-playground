from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import os
import json
import time
import logging
from dotenv import load_dotenv 
from run_workflow import run_argo_workflow, TokenProvider

from timeseries.timeseries import timeseries_prediction
from timeseries.solar_timeseries import solar_prediction
from timeseries.wind_timeseries import wind_prediction

from database_entry import add_data, get_local_session

load_dotenv()
app = FastAPI()

SessionLocal, engine = get_local_session()
ARGO_WORKFLOW_API_URL = os.getenv('ARGO_WORKFLOW_API_URL') # "https://localhost:2746/api/v1/workflows/argo"
ARGO_WORKFLOW_YAML_PATH = os.getenv('ARGO_WORKFLOW_YAML_PATH') # "/mnt/disks/infengine-dev/pipeline-configs/"
INPUT_DIRECTORY = os.getenv('INPUT_DIRECTORY')
TOKEN_PATH = os.getenv('TOKEN_PATH', None)
# TOKEN_PATH = os.getenv('TOKEN_PATH', "/var/run/secrets/tokens/token")

auth_token_provider = TokenProvider(TOKEN_PATH)

class healthCheck_response(BaseModel):
    is_alive: bool

@app.get("/inference_api/")
async def inference_api():
    return JSONResponse(content=healthCheck_response(is_alive=True).model_dump(), status_code=200)


class inferenceApi_inputRequest(BaseModel):
    project_name: str
    model_name: str
    assets: List[str]

class inferenceApi_response(BaseModel):
    status: str
    Job_Name: str

# def run(yamal_name, dependency_chart_name,  ):
#     ARGO_WORKFLOW_YAML_PATH = ''
#     ARGO_WORKFLOW_API_URL = ''
#     yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "ukpn_v2/ukpn-pipeline.yaml")
#     dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "ukpn_v2/dependency_chart.json")
#     job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data, namespace="argo", auth_token_provider=auth_token_provider)
#     logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")


@app.post("/inference_api/")
async def inference_api(data: inferenceApi_inputRequest):


    # print(ARGO_WORKFLOW_API_URL)
    # print(ARGO_WORKFLOW_YAML_PATH)
    # print(INPUT_DIRECTORY)

    # status_code, status, job_name = 200, "hello", "job1"


    project = data.project_name
    model = data.model_name
    assets = data.assets

    # job_name = project+str(int(time.time()))
    job_name = None
    # input_path=os.path.join(INPUT_DIRECTORY, project)
    # os.chmod(input_path,0o777)
    # data = {
    #     'input': input_path,
    #     'output': os.path.join(INPUT_DIRECTORY, project, 'output/'),
    #     'asset': assets,
    #     'model': model,
    #     'project': project,
    #     # 'job_name': job_name,
    #     }
    # os.makedirs(data['output'], exist_ok=True, mode=0o777)
    # os.chmod(data['output'],0o777)

    data_dict = data.model_dump()

    if model=="ukpn_v2":
        yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "ukpn_v2/ukpn-pipeline.yaml")
        dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "ukpn_v2/dependency_chart.json")
        status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
        data_dict['job_name'] = job_name
        logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="natgrid":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "natgrid/natgrid-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "natgrid/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="sce":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "sce_v2/sce-v2-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "sce_v2/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="iberdrolla":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "iberdrola/iberdrola-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "iberdrola/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="windmill":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "windmill/windmill-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "windmill/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="windmill_v2":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "windmill_v2/windmill-v2-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "windmill_v2/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="fpl":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "fpl/fpl-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "fpl/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="clp":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "clp/clp-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "clp/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="npg":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "npg/npg-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "npg/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="gas":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "nisource/nisource-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "nisource/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}") 

    elif model=="enbridge_gas_pipeline":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "enbridge_gas/enbridge-gas-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "enbridge_gas/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="enbridge_gas_pipeline_v2":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "enbridge_gas_v2/enbridge-gas-v2-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "enbridge_gas_v2/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="thermal":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "fpl_thermal/thermal-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "fpl_thermal/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets = ["all"], dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="tata_steel":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "tata_steel/tata-steel-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "tata_steel/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    elif model=="llm":
            yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "llm_pipeline/llm-pipeline.yaml")
            dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "llm_pipeline/dependency_chart.json")
            status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
            data_dict['job_name'] = job_name
            logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    if job_name == None:
        add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Failed to start Celery Job !')
        return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)
    else:
        add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Celery Job Started !')
        return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)

# async def satellite_vegetation(request):
class satellite_vegetation_api_request(BaseModel):
    bufferSize: str
    project_name: str

@app.post("/satellite_vegetation/")
async def satellite_vegetation(data:satellite_vegetation_api_request):

    # ARGO_WORKFLOW_API_URL = os.getenv('ARGO_WORKFLOW_API_URL') # "https://localhost:2746/api/v1/workflows/argo"
    # ARGO_WORKFLOW_YAML_PATH = os.getenv('ARGO_WORKFLOW_YAML_PATH') # "/mnt/disks/infengine-dev/pipeline-configs/"
    # INPUT_DIRECTORY = os.getenv('INPUT_DIRECTORY')
    
    # data = {}
    # data.bufferSize = int(data.bufferSize)
    project = data.project_name
    job_name = project+str(int(time.time()))
    # data['project']=data['project_name']
    # data['job_name']=job_name
    # data['input']=os.path.join(INPUT_DIRECTORY,project)
    # data['output']=os.path.join(INPUT_DIRECTORY,project, 'output')
    
    # os.makedirs(data['output'], exist_ok=True)
    # os.chmod(data['output'],0o777)
    # os.chmod(data['input'],0o777)
    data_dict = data.model_dump()
    assets = ["all"]

    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "satelite_vegetation/satelite-vegetation-pipeline.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "satelite_vegetation/dependency_chart.json")
    status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
    logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    # satelite_vegetation_end_to_end(data)
    # responseData = {'status':'task created', 'Job_Name': job_name}
    add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Celery Job Started !')
    return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)



# async def satellite_vegetation(request):
class supervisor_agent_api_request(BaseModel):
    project_name: str

@app.post("/supervisor_agent/")
async def supervisor_agent(data:supervisor_agent_api_request):

    project = data.project_name
    job_name = project+str(int(time.time()))
    data_dict = data.model_dump()
    assets = ["all"]

    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "supervisor_agent/supervisor_agent.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "supervisor_agent/dependency_chart.json")
    status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
    logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Celery Job Started !')
    return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)



class nlp_inference_api_request(BaseModel):
    how_much_to_process: int
    input_excel_name: str
    project_name: str
    input_data_type: str

@app.post("/nlp_inference_api/")
async def nlp_inference(data:nlp_inference_api_request):
# async def nlp_inference(data:dict):
    logging.info(data)

    # ARGO_WORKFLOW_API_URL = os.getenv('ARGO_WORKFLOW_API_URL') # "https://localhost:2746/api/v1/workflows/argo"
    # ARGO_WORKFLOW_YAML_PATH = os.getenv('ARGO_WORKFLOW_YAML_PATH') # "/mnt/disks/infengine-dev/pipeline-configs/"
    # INPUT_DIRECTORY = os.getenv('INPUT_DIRECTORY')

    project = data.project_name
    input_excel_name = data.input_excel_name
    job_name = project+str(int(time.time()))
    # data = {
    #         'input_excel_name': input_excel_name,
    #         'project': project,
    #        }
    data_dict = data.model_dump()
    assets = ["all"]
    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "sgi_nlp/sgi-nlp-pipeline.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "sgi_nlp/dependency_chart.json")

    status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
    logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    # sgi_nlp_prediction.delay(project,job_name,input_excel_name)
    responseData={'status':'created'}
    add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Celery Job Started !')
    return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)


    
#---------------------------------------LiDAR----------------------------------------------
class lidar_inference_api_request(BaseModel):
    analysis_type: str
    threshold: str
    input_folder: str

@app.post("/lidar_rendering/")
async def lidar_inference(data:lidar_inference_api_request):

    analysis_type = data.analysis_type
    threshold = data.threshold
    input_folder = data.input_folder
    job_name = input_folder+str(int(time.time()))
    # data = {
    #         'analysis_type': analysis_type,
    #         'input_folder': input_folder,
    #         'threshold': threshold,
    #        }
    data_dict = data.model_dump()
    project = input_folder
    assets = [analysis_type,]
    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "lidar_inference/lidar-inference-pipeline.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "lidar_inference/dependency_chart.json")

    status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=input_folder, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
    logging.info(f"{job_name}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    responseData={'status':'created'}
    add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Celery Job Started !')
    return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)


class timeseries_inference_api_request(BaseModel):
    date_time_values: List[float]
class timeseries_inference_api_response(BaseModel):
    status: str
    date_time_values: List[float]

@app.post("/timeseries_inference/")
async def timeseries_inference(data:timeseries_inference_api_request):
    try:
        date_time_values = data.data_time
        output_list = timeseries_prediction(date_time_values)
        if output_list == None:
            return JSONResponse(content=inferenceApi_response(status='failed', date_time_values=[]).model_dump(), status_code=201)
        else:
            return JSONResponse(content=inferenceApi_response(status='created', date_time_values=output_list).model_dump(), status_code=201)
    except Exception as e:
        logging.exception("Error in solar inference")
        return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=500)

class solar_inference_api_request(BaseModel):
    parameters_selected: List[str]
    data_from_db: Dict[str, List[float]]

@app.post("/solar_inference/")
async def solar_inference(data:solar_inference_api_request):
    try:        
        parameters_selected = data.parameters_selected
        data_from_db = data.data_from_db
        output_list = solar_prediction(parameters_selected,data_from_db)
        logging.info(type(output_list))
        logging.info(output_list)
        if output_list == None:
            return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=201)
        else:
            loaded_values = json.loads(output_list)
            if any(x is None for x in loaded_values):
                return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=201)
            return JSONResponse(content=timeseries_inference_api_response(status='created', date_time_values=loaded_values).model_dump(), status_code=201)
    except Exception as e:
        logging.exception("Error in solar inference")
        return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=500)

class wind_inference_api_request(BaseModel):
    parameters_selected: List[str]
    data_from_db: Dict[str, List[float | str]]
@app.post("/wind_inference/")
async def wind_inference(data:wind_inference_api_request):
    try:        
        logging.info(f"Received data: {data}")
        parameters_selected = data.parameters_selected
        data_from_db = data.data_from_db
        logging.info(f"parameters_selected: {parameters_selected}")
        logging.info(f"data_from_db: {data_from_db}")
        output_list = wind_prediction(parameters_selected,data_from_db)
        logging.info(f"Output_list: {output_list}")
        if output_list == None:
            return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=201)
        else:
            loaded_values = json.loads(output_list)
            if any(x is None for x in loaded_values):
                return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=201)
            return JSONResponse(content=timeseries_inference_api_response(status='created', date_time_values=loaded_values).model_dump(), status_code=201)
    except Exception as e:
        logging.exception("Error in wind inference")
        return JSONResponse(content=timeseries_inference_api_response(status='failed', date_time_values=[]).model_dump(), status_code=500)

class raster_api_request(BaseModel):
    project_name: str
    vector: str
    image_NED: str
    image_RGB: str
    bufferSize: str

@app.post("/vegdepth_raster_analysis/")
async def raster_analysis(data:raster_api_request):
# async def raster_analysis(data:dict):

    ARGO_WORKFLOW_API_URL = os.getenv('ARGO_WORKFLOW_API_URL') # "https://localhost:2746/api/v1/workflows/argo"
    ARGO_WORKFLOW_YAML_PATH = os.getenv('ARGO_WORKFLOW_YAML_PATH') # "/mnt/disks/infengine-dev/pipeline-configs/"
    INPUT_DIRECTORY = os.getenv('INPUT_DIRECTORY')
    # logging.log(data.project_name)
    logging.info(data)

    project = data.project_name
    vector = data.vector
    image_NED = data.image_NED
    image_RGB = data.image_RGB
    bufferSize = data.bufferSize
    # src = os.path.join(INPUT_DIRECTORY, project)
    # dest = os.path.join(src, 'output')
    # data = {
    #         'project': project,
    #         'vector': vector,
    #         'image_NED': image_NED,
    #         'image_RGB': image_RGB,
    #         'bufferSize': bufferSize,
    #        }
    data_dict = data.model_dump()
    assets = ["all"]
    yaml_file_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "raster_analysis/raster-analysis-pipeline.yaml")
    dependency_chart_path = os.path.join(ARGO_WORKFLOW_YAML_PATH, "raster_analysis/dependency_chart.json")

    status_code, status, job_name = run_argo_workflow(yaml_file_path=yaml_file_path, url=ARGO_WORKFLOW_API_URL, assets=assets, dependency_chart_path=dependency_chart_path, folder_name=project, data=data_dict, namespace="argo", auth_token_provider=auth_token_provider)
    logging.info(f"{project}, {yaml_file_path},{dependency_chart_path}, {ARGO_WORKFLOW_API_URL}, {assets}")

    # vegdepth_raster_analysis_end_to_end_r2.delay(src, dest, conf)
    responseData = {'status':'created','project_name':project}
    add_data(SessionLocal=SessionLocal, project=project , job_name=job_name, status=f'Celery Job Started !')
    return JSONResponse(content=inferenceApi_response(status=status, Job_Name=job_name).model_dump(), status_code=status_code)

