import requests
import zipfile
import logging
import boto3
import os
from dotenv import load_dotenv
from utils import *

env_path = os.path.abspath("../local.env")

logging.basicConfig(level=logging.DEBUG)
boto3.set_stream_logger('botocore', level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Reading in secret keys from local.env")
load_dotenv(env_path, override=True)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
DYNAMO_DB_ACCESS_KEY=os.getenv("DYNAMO_DB_ACCESS_KEY")
DYNAMO_DB_SECRET_ACCESS_KEY=os.getenv("DYNAMO_DB_SECRET_ACCESS_KEY")
DB_NAME=os.getenv("DB_NAME")

MAX_FILE_SIZE = 100 * 1024 * 1024


dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=DYNAMO_DB_ACCESS_KEY,
    aws_secret_access_key=DYNAMO_DB_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
table = dynamodb.Table("House_price_data_test")


def extract_zips_from_input(temp_dir, url, file):
    zip_path = os.path.join(temp_dir, "input.zip")
    extract_path = os.path.join(temp_dir, "extracted_files")
    try:
        if url:
            response = requests.get(url, stream=True)
            file_size = int(response.headers.get("Content-Length", 0))
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            if not has_enough_disk_space(file_size, temp_dir):
                raise HTTPException(status_code=507, detail="Insufficient disk space")
            with open(zip_path, "wb") as buffer:
                for chunk in response.iter_content(chunk_size=8192):
                    buffer.write(chunk)
        elif file:
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        # Extract and process the ZIP file
        extract_all_zips(zip_path, extract_path)
        return extract_path
    except Exception as e:
        logger.error("Problem extracting zips from tempfile: " + str(e))