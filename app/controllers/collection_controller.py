import logging
import os
import shutil
from typing import List
import tempfile
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Response
from dotenv import load_dotenv

from dtos.collection_dtos import *
from services.collection_service import *
from utils import *
from services.database_service import *

env_path = os.path.abspath("../local.env")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter()

logger.info("Reading in secret keys from local.env")
load_dotenv(env_path, override=True)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DYNAMO_DB_ACCESS_KEY=os.getenv("DYNAMO_DB_ACCESS_KEY")
DYNAMO_DB_SECRET_ACCESS_KEY=os.getenv("DYNAMO_DB_SECRET_ACCESS_KEY")
DB_NAME=os.getenv("DB_NAME")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
TEMP_DIR = "temp_uploads"


BASE_URL = "/"
PARSE_FROM_DAT_FOLDER = "/collection/parse/dat/directory"
PARSE_FROM_DAT_SINGLE = "/collection/parse/dat"
COLLECT_AS_DATASET_DTO = "/collection/parse/dat/toevent"
UPLOAD_DB = "/collection/uploadtoDB"
UPLOAD_S3 = "/upload"
DOWNLOAD_S3 = "/download"


s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=os.getenv("DYNAMO_DB_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("DYNAMO_DB_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)
dynamodb_table = dynamodb.Table("House_price_data_test")
database_service = DatabaseService(dynamodb_table)
os.makedirs(TEMP_DIR, exist_ok=True)


@router.get(BASE_URL)
def read_root():
    """Base Endpoint, should prompt user to route to a specific endpoint"""
    raise HTTPException(status_code=404, detail="Data collection service. Please specify an endpoint")


@router.post(PARSE_FROM_DAT_FOLDER, response_model=List[EventDTO])
async def parse_directory_folder(
    request: Request,
    file: UploadFile = File(None),
):
    """
    Endpoint to parse multiple .DAT files from either:
    - A `.zip` file uploaded directly.
    - A `.zip` file from a provided URL.
    """
    # Request body validation
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

    # Extract zips
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "input.zip")
    extract_path = extract_zips_from_input(temp_dir, url, file)

    try:
        all_events = extract_events_from_directory(extract_path)
        return all_events

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing ZIP: {str(e)}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
    

@router.post(PARSE_FROM_DAT_SINGLE, response_model=DatasetDTO)
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
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    
@router.post(COLLECT_AS_DATASET_DTO, response_model=DatasetDTO)
async def build_final_dataset(
    request: Request,
    file: UploadFile = File(None)
):
    """
    Endpoint to collect all events, build a dataset DTO, and return it as a downloadable JSON file.
    """
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

    # Extract zips
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "input.zip")
    extract_path = extract_zips_from_input(temp_dir, url, file)

    try:
        all_events = extract_events_from_directory(extract_path)
        final_dataset = build_dataset_dto(all_events)
        if not final_dataset:
            raise HTTPException(status_code=400, detail="No valid data found.")
        
        json_data = json.dumps(final_dataset, indent=4, default=decimal_to_float)
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=dataset.json"}
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building dataset: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(zip_path):
            os.remove(zip_path)


@router.put(UPLOAD_DB)
async def events_into_db(all_events: List[EventDTO]):
    """
    Endpoint to insert a list of events into the database.
    Accepts a JSON array of event objects.
    """
    try:
        logger.log("Inserting events into Database")
        database_service.insert_events_into_db(all_events)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


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


@router.get(f"{DOWNLOAD_S3}/" + "{file_name}")
async def download_from_s3(file_name: str):
    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/uploads/{file_name}"
    return {"download_url": file_url}
