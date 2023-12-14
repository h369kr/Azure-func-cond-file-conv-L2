import os
import azure.functions as func
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from flatten_complex_json import flatten_complex_json
from json import dumps
import xml.etree.ElementTree as ET
import pandas as pd
import json
import xmltodict
import io

def convert_csv_to_xml(csv_content):
    # Convert CSV to XML using pandas
    df = pd.read_csv(io.StringIO(csv_content))
    xml_data = df.to_xml(root_name="data", row_name="row")
    return xml_data

def convert_json_to_xml(json_content):
    try:
        json_data = json.loads(json_content)
        # with open(json_content, encoding="utf8") as file:
        #     json_data = json.load(file)
        df = flatten_complex_json(json_data)
        df = df.fillna(value="None")
        xml_data = df.to_xml(root_name="data", row_name="row")
        return xml_data
    except Exception as e:
        return f"An error occurred while converting JSON to XML: {str(e)}"

def main(req: func.HttpRequest) -> func.HttpResponse:

    # Get parameters from query string
    ip_blob_name = req.params.get('ip_blob_name')
    op_blob_name = req.params.get('op_blob_name')
    source_container_name = req.params.get('source_container_name')
    dest_container_name = req.params.get('dest_container_name')

    try:
        # Retrieve user input and validate it
        user_input = req.params.get('convertTo')
        if user_input not in ['XML', 'CSV', 'JSON']:
            return func.HttpResponse("Invalid 'convertTo' parameter. Use 'XML', 'CSV', or 'JSON'.", status_code=400)

        # Retrieve the file from Azure Blob Storage
        ip_connection_string = "DefaultEndpointsProtocol=https;AccountName=xyz1500;AccountKey=GdrlFjxAD8NHNnnTCijmngfaO1QIfBOiozXdEn5JeOE+eNp6XSJq2ka6eVwDcpnu3EydYU+BDQmC+AStsjUU3Q==;EndpointSuffix=core.windows.net"

        blob_service_client = BlobServiceClient.from_connection_string(ip_connection_string)
        blob_container_client = blob_service_client.get_container_client (source_container_name)
        blob_client = blob_container_client.get_blob_client (ip_blob_name)

        blob_data = blob_client.download_blob()
        file_content = blob_data.readall().decode("utf-8")

        op_connection_string = 'DefaultEndpointsProtocol=https;AccountName=xyz1500;AccountKey=GdrlFjxAD8NHNnnTCijmngfaO1QIfBOiozXdEn5JeOE+eNp6XSJq2ka6eVwDcpnu3EydYU+BDQmC+AStsjUU3Q==;EndpointSuffix=core.windows.net'
        op_blob_service_client = BlobServiceClient.from_connection_string (op_connection_string)

        op_container_client = op_blob_service_client.get_container_client (dest_container_name)

        # Determine the file format (XML, CSV, JSON)
        file_extension = os.path.splitext(ip_blob_name)[1].lower()

        if file_extension == '.xml':
            if user_input == 'CSV':
                # Convert XML to CSV
                df = pd.read_xml(file_content)
                # Convert XML to CSV
                csv_content = df.to_csv(index=False)
                # Upload CSV to Blob Storage
                op_blob_client = op_container_client.get_blob_client(op_blob_name)
                op_blob_client.upload_blob(csv_content, overwrite=True)
            
            elif user_input == 'JSON':
                # Convert XML to JSON
                # Parse the XML data into a Python dictionary
                xml_dict = xmltodict.parse(file_content)
                # Convert the dictionary to a JSON string
                json_data = json.dumps(xml_dict, indent=4)
                op_blob_client = op_container_client.get_blob_client(op_blob_name)
                op_blob_client.upload_blob(json_data, overwrite=True)

        elif file_extension == '.csv':
            if user_input == 'XML':
                # Convert CSV to XML
                xml_data = convert_csv_to_xml(file_content)
                # blob_name = os.path.splitext(blob_name)[0] + ".xml"
                op_blob_client = op_container_client.get_blob_client(op_blob_name)
                op_blob_client.upload_blob(xml_data, overwrite=True)

            elif user_input == 'JSON':
                # Convert CSV to JSON
                df = pd.read_csv(io.StringIO(file_content))
                json_data = df.to_json(orient='records')
                # blob_name = os.path.splitext(blob_name)[0] + ".json"
                op_blob_client = op_container_client.get_blob_client(op_blob_name)
                op_blob_client.upload_blob(json_data, overwrite=True)

        elif file_extension == '.json':
            if user_input == 'XML':
                # Convert JSON to XML
                xml_data = convert_json_to_xml(file_content)
                # blob_name = os.path.splitext(blob_name)[0] + ".xml"
                op_blob_client = op_container_client.get_blob_client(op_blob_name)
                op_blob_client.upload_blob(xml_data, overwrite=True)

            elif user_input == 'CSV':
                # Convert JSON to CSV
                # df = pd.read_json(file_content)
                json_data = json.loads(file_content)
                df = flatten_complex_json(json_data)
                df = df.fillna(value="None")
                csv_data = df.to_csv(index=False)
                # blob_name = os.path.splitext(blob_name)[0] + ".csv"
                op_blob_client = op_container_client.get_blob_client(op_blob_name)
                op_blob_client.upload_blob(csv_data, overwrite=True)

        return func.HttpResponse(f"File converted to {user_input} and uploaded successfully.", status_code=200)

    except Exception as e:
        return func.HttpResponse(f"An error occurred: {str(e)}", status_code=500)
