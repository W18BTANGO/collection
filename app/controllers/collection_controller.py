import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import List
import tempfile

import boto3
from fastapi import APIRouter, HTTPException, UploadFile, File
from dotenv import load_dotenv

from dtos.collection_dtos import DatasetDTO, FileUploadResponseDTO
from services.collection_service import *
from utils import *

# Load environment variables
env_path = os.path.abspath("../local.env")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter()

# API Routes
BASE_URL = "/"
PARSE_FROM_DAT_FOLDER = "/collection/parse/dat/directory"
PARSE_FROM_DAT_SINGLE = "/collection/parse/dat"
UPLOAD = "/upload"

# Read env variables
logger.info("Reading in secret keys from local.env")
load_dotenv(env_path, override=True)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

TEMP_DIR = "temp_uploads"  # Temporary directory for extracted files
os.makedirs(TEMP_DIR, exist_ok=True)  # Ensure the directory exists

@router.get(BASE_URL)
def read_root():
    """Base Endpoint, should prompt user to route to a specific endpoint"""
    raise HTTPException(status_code=404, detail="Data collection service. Please specify an endpoint")


@router.post(PARSE_FROM_DAT_FOLDER, response_model=DatasetDTO)
async def parse_directory_folder(file: UploadFile = File(...)):
    """
    Endpoint to parse multiple .DAT files from an uploaded .zip file, including nested .zip files.
    - Upload a `.zip` file containing multiple `.DAT` files (or nested .zip archives).
    - The system extracts and processes all .DAT files into a single DatasetDTO.
    """
    zip_path = os.path.join(TEMP_DIR, file.filename)
    extract_path = os.path.join(TEMP_DIR, file.filename.replace(".zip", ""))
    all_events = []  # List to store events from all files

    try:
        # Save uploaded ZIP file
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Recursively extract all ZIP files
        extract_all_zips(zip_path, extract_path)

        # Find all .DAT files
        dat_files = list(Path(extract_path).rglob("*.DAT"))
        if not dat_files:
            raise HTTPException(status_code=400, detail="No .DAT files found in the uploaded ZIP.")

        logger.info(f"Found {len(dat_files)} DAT files: {dat_files}")

        # Process each .DAT file
        for dat_file in dat_files:
            events = parse_dat_lines(str(dat_file))
            if events:
                all_events.extend(events)

        # Cleanup
        shutil.rmtree(extract_path)  # Remove extracted files
        os.remove(zip_path)  # Remove zip file

        # Construct final DatasetDTO
        final_dataset = build_dataset_dto(all_events)
        if not final_dataset:
            raise HTTPException(status_code=400, detail="No valid data found in the uploaded files.")

        return final_dataset

    except Exception as e:
        logger.error(f"Error processing ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

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
    


@router.post(UPLOAD, response_model=FileUploadResponseDTO)
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


@router.get("/download-from-s3/{file_name}")
async def download_from_s3(file_name: str):
    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/uploads/{file_name}"
    return {"download_url": file_url}
