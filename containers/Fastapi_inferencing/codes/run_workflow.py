import logging
import time
from typing import Optional
import requests
import yaml
import json
import jwt
import os
logging.basicConfig(level=logging.INFO)


def get_workflow_parameters(assets, dependency_chart_path, folder_name, workflow_template, data):

    with open(dependency_chart_path, 'r') as file:
       dependency_chart = json.load(file)

    parameters = {param: "false" for values in dependency_chart.values() for param in values}
 
    if "all" in assets:
        parameters = {param: "true" for param in parameters}
        assets = [key for key in dependency_chart.keys()]
    else:
        for asset in assets:
            if asset in dependency_chart:
                for param in dependency_chart[asset]:
                    parameters[param] = "true"

    # parameter_check = workflow_template.get("spec", {}).get("arguments", {}).get("parameters", [])
    # for param in parameter_check:
    #     if param.get("name") == "data":
    #         parameters["data"] = json.dumps(data)
    #     if param.get("name") == "folder_name":
    #         parameters["folder_name"] = folder_name        
    #     if param.get("name") == "assets":
    #         parameters["assets"] = json.dumps(assets) 

    parameters["data"] = json.dumps(data)        
    parameters["assets"] = json.dumps(assets)
    parameters["folder_name"] = folder_name
    # logging.info(parameters)
    return parameters

def run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", auth_token_provider=None):
    with open(yaml_file_path, "r") as file:
        workflow_template = yaml.safe_load(file)

    

    parameters = get_workflow_parameters(assets, dependency_chart_path, folder_name, workflow_template, data)
    workflow_template['spec']['arguments'] = {"parameters": [{"name": k, "value": v} for k, v in parameters.items()]}
    workflow = {
                "namespace": namespace, 
                "serverDryRun": False,
                "workflow": workflow_template
               }
        
    url = url
    data = json.dumps(workflow)
    headers={"Content-Type": "application/json"}

    #  try with old token
    if auth_token_provider != None:
        token = auth_token_provider.get()
        headers["Authorization"] = f"Bearer {token}"
        logging.info(headers)
    response = requests.post(url, data, headers=headers, verify=False)

    # if old token fails load new token from file and retry
    if auth_token_provider and response.status_code in (401, 403):
        # Re-read token and retry once
        token = auth_token_provider.get()
        headers["Authorization"] = f"Bearer {token}"
        logging.info(headers)
        response = requests.post(url, data, headers=headers, verify=False)

    # if respose is successfull
    if response.status_code == 200:
        logging.info(f"Workflow submitted successfully.")
        logging.info(f'Name:, r{response.json().get("metadata", {}).get("name")}')
        return response.status_code, "Argo Workflow Started !", response.json().get("metadata", {}).get("name")

    else:
        logging.info(f"Failed to submit workflow")
        logging.info(response.status_code)
        logging.info(response.text)
        # print(f"Failed to submit workflow")
        # print(response.status_code)
        # print(response.text)
        return response.status_code, "Argo Workflow Failed !", None

if __name__ == '__main__':

    url = "https://localhost:2747/api/v1/workflows/argo"
    data = {}
    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/ukpn_v2/ukpn-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/ukpn_v2/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "ukpn_images"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/clp/clp-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/clp/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "CLP_test"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/natgrid/natgrid-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/natgrid/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "natgrid_substation_test"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/windmill_v2/windmill-v2-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/windmill_v2/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "windmill_24dec"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/enbridge_gas_v2/enbridge-gas-v2-pipeline.yaml"
    dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/enbridge_gas_v2/dependency_chart.json"
    assets = ["all"]
    folder_name = "enbridge_latest_test_harshitha"
    run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/fpl/fpl-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/fpl/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "fpl_harshitha"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/sce_v2/sce-v2-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/sce_v2/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "sce_v2"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/nisource/nisource-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/nisource/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "gas_nisource"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/npg/npg-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/npg/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "NPG_Nishnat_Demo"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/windmill/windmill-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/windmill/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "windmill_test"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # data["parameters_selected"] = ["AMBIENT_TEMPERATURE","MODULE_TEMPERATURE", "IRRADIATION"]
    # data["data_from_db"] = {
    #             "AMBIENT_TEMPERATURE":[
    #                                     27.0047637,
    #                                     26.88081143,
    #                                     26.68205534,
    #                                     26.5005889,
    #                                     26.596148
    #                                    ],
    #             "MODULE_TEMPERATURE":[
    #                                     25.0607889,
    #                                     24.42186883,
    #                                     24.42729031,
    #                                     24.4206776,
    #                                     25.08821041
    #                                  ],
    #             "IRRADIATION":[
    #                            0,
    #                            0,
    #                            0,
    #                            0,
    #                            0
    #                         ],
    #             }

    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/forecasting/forecasting-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/forecasting/dependency_chart.json"
    # assets = ["solar_timeseries"]
    # folder_name = ""
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # data["bufferSize"] = 2
    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/satelite_vegetation/satelite-vegetation-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/satelite_vegetation/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "satelite_vegetation_management"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)

    # data["vector"] = "PG&E_Span.zip"
    # data["image_NED"] = "IMG_PNEO4_202305221914524_MS-FS_ORT_d392055b-f7b5-48dd-c8fc-70e1741dae04_NED_R1C1.TIF"
    # data["image_RGB"] = "IMG_PNEO4_202305221914524_MS-FS_ORT_d392055b-f7b5-48dd-c8fc-70e1741dae04_RGB_R1C1.TIF"
    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/raster_analysis/raster-analysis-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/raster_analysis/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "raster_analysis"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # data["input_excel_name"] = "inf_data_on_client_data_final.xlsx"
    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/sgi_nlp/sgi-nlp-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/sgi_nlp/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "sgi_nlp"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)


    # data["threshold"] = 5
    # yaml_file_path = "/mnt/disks/infengine-dev/pipeline-configs/lidar_inference/lidar-inference-pipeline.yaml"
    # dependency_chart_path = "/mnt/disks/infengine-dev/pipeline-configs/lidar_inference/dependency_chart.json"
    # assets = ["all"]
    # folder_name = "temp_lidar"
    # run_argo_workflow(yaml_file_path, url, assets, dependency_chart_path, folder_name, data, namespace="argo", authorization=None)
# "rawAnalysis"
# "Proximity"
# "Height"