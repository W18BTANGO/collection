import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import List
import tempfile
import requests
import json

import boto3
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Response
from dotenv import load_dotenv

from dtos.collection_dtos import *
from services.collection_service import *
from utils import *

env_path = os.path.abspath("../local.env")

logging.basicConfig(level=logging.DEBUG)
boto3.set_stream_logger('botocore', level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter()

# API Routes
BASE_URL = "/"
PARSE_FROM_DAT_FOLDER = "/collection/parse/dat/directory"
PARSE_FROM_DAT_SINGLE = "/collection/parse/dat"
UPLOAD_S3 = "/upload"
DOWNLOAD_S3 = "/download"

# Read env variables
logger.info("Reading in secret keys from local.env")
load_dotenv(env_path, override=True)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DYNAMO_DB_ACCESS_KEY=os.getenv("DYNAMO_DB_ACCESS_KEY")
DYNAMO_DB_SECRET_ACCESS_KEY=os.getenv("DYNAMO_DB_SECRET_ACCESS_KEY")
DB_NAME=os.getenv("DB_NAME")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=DYNAMO_DB_ACCESS_KEY,
    aws_secret_access_key=DYNAMO_DB_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
table = dynamodb.Table("House_price_data_test")


TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@router.get(BASE_URL)
def read_root():
    """Base Endpoint, should prompt user to route to a specific endpoint"""
    raise HTTPException(status_code=404, detail="Data collection service. Please specify an endpoint")


@router.post(PARSE_FROM_DAT_FOLDER, response_model=DatasetDTO)
async def parse_directory_folder(
    request: Request,
    file: UploadFile = File(None),
):
    """
    Endpoint to parse multiple .DAT files from either:
    - A `.zip` file uploaded directly.
    - A `.zip` file from a provided URL.
    """
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    if file and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    url = None
    if "application/json" in request.headers.get("content-type", "").lower():
        try:
            body = await request.json()
            url = body.get("url")
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not file and not url:
        raise HTTPException(status_code=400, detail="Either a file or a URL must be provided.")

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "input.zip")
    extract_path = os.path.join(temp_dir, "extracted_files")

    try:
        if url:
            # Check file size before downloading
            response = requests.get(url, stream=True)
            file_size = int(response.headers.get("Content-Length", 0))
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")

            # Check disk space
            if not has_enough_disk_space(file_size, temp_dir):
                raise HTTPException(status_code=507, detail="Insufficient disk space")

            # Stream the file to disk
            with open(zip_path, "wb") as buffer:
                for chunk in response.iter_content(chunk_size=8192):
                    buffer.write(chunk)

        elif file:
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        # Extract and process the ZIP file
        extract_all_zips(zip_path, extract_path)

        #TODO Split up writing to DB and get event

        dat_files = list(Path(extract_path).rglob("*.DAT"))
        if not dat_files:
            raise HTTPException(status_code=400, detail="No .DAT files found.")

        all_events = []
        for dat_file in dat_files:
            events = parse_dat_lines(str(dat_file))
            if events:
                all_events.extend(events)

        with table.batch_writer() as batch:
            logger.debug(f"Total events to insert: {len(all_events)}")
            
            for event in all_events:
                if not isinstance(event.attribute, HouseSaleDTO):
                    logger.debug(f"Skipping event because attribute is not a HouseSaleDTO: {event}")
                    continue
                
                event_data = event.attribute.model_dump()  # Convert Pydantic model to dictionary
                
                if "property_id" not in event_data or event_data["property_id"] is None:
                    logger.debug(f"Skipping event with missing property_id: {event_data}")
                    continue
                if "property_id" in event_data and event_data["property_id"] is not None:
                    event_data["property_id"] = str(event_data["property_id"])
                    batch.put_item(Item=event_data)


        final_dataset = build_dataset_dto(all_events)
        if not final_dataset:
            raise HTTPException(status_code=400, detail="No valid data found.")

        json_data = json.dumps(final_dataset, indent=4, default=decimal_to_float)



        # Return the JSON as a downloadable file
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=dataset.json"}
        )


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing ZIP: {str(e)}")
    finally:
        # Cleanup temporary files
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
    

@router.post("/collection/parse/dat", response_model=DatasetDTO)
async def parse_directory_single(file: UploadFile = File(...)):
    """
    Endpoint to parse a single .DAT file.
    """
    temp_file_path = os.path.join(TEMP_DIR, file.filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        final_data = process_file(temp_file_path)
        if not final_data:
            raise HTTPException(status_code=400, detail="No data found to parse")
        return final_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Cleanup: Delete the temporary file after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    


@router.post(UPLOAD_S3, response_model=FileUploadResponseDTO)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the S3 bucket.
    """
    try:
        file_path = f"uploads/{file.filename}"  # S3 object path
        logger.debug(f"File path: {file_path}")
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, file_path)
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_path}"
        return FileUploadResponseDTO(message="File uploaded successfully", file_url=file_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("DOWNLOAD_S3/{file_name}")
async def download_from_s3(file_name: str):
    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/uploads/{file_name}"
    return {"download_url": file_url}
