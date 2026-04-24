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
  