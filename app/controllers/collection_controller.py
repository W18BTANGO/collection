import logging
import os
import boto3
from fastapi import APIRouter, HTTPException, UploadFile, File
from dotenv import load_dotenv

from dtos.collection_dtos import *
from services.collection_service import parse_dat_file
from utils import validate_directory, process_directory

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../local.env'))
load_dotenv(env_path)
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Logger setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
router = APIRouter()

# API Routes
BASE_URL = "/"
UPLOAD = "/upload"
PARSE_UPLOAD = "/collection/upload"
PARSE_URL = "/collection/url"

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


@router.get(BASE_URL)
def read_root():
    """Base Endpoint, should prompt user to route to a specific endpoint"""
    raise HTTPException(status_code=404, detail="Data collection service. Please specify an endpoint")


@router.post(PARSE_UPLOAD, response_model=List[DatasetDTO])
async def parse_directory(request: DirectoryPath):
    """
    Endpoint to parse a given directory and return processed data.
    Usage:
        - Please upload a folder of .DAT Files that you would like processed
    """
    directory_path = request.directory_path
    logger.info(f"User attempting to collect data from: {directory_path}")

    validate_directory(directory_path)  # Validate input directory

    try:
        final_data = process_directory(directory_path)
        if not final_data:
            raise HTTPException(status_code=400, detail="No data found to parse")
        return final_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")


@router.post(UPLOAD, response_model=FileUploadResponseDTO)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the S3 bucket.
    """
    try:
        file_path = f"uploads/{file.filename}"  # S3 object path
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, file_path)

        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_path}"
        return FileUploadResponseDTO(message="File uploaded successfully", file_url=file_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/download-from-s3/{file_name}")
async def download_from_s3(file_name: str):
    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/uploads/{file_name}"
    return {"download_url": file_url}
