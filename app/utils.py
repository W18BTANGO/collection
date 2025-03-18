from fastapi import HTTPException
import os
# from main import parse_dat_file  # Remove this import
import zipfile
import logging
from pathlib import Path
import shutil
from decimal import Decimal
from dotenv import load_dotenv
import requests

from app.services.collection_service import parse_dat_file

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def load_env_variables(env_path):
    if load_dotenv(env_path):
        logger.info(f"Environment variables loaded from {env_path}")
    else:
        logger.info(f"Failed to load environment variables from {env_path}")

    required_vars = ["AWS_REGION", "S3_ACCESS_KEY", "S3_SECRET_ACCESS_KEY", "S3_BUCKET_NAME", "DYNAMO_DB_ACCESS_KEY", "DYNAMO_DB_SECRET_ACCESS_KEY"]
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise EnvironmentError(f"Environment variable {var} is not set.")
        logger.debug(f"{var}={value}")
        

def validate_directory(directory_path: str):
    """
    Check that a directory path is legitimate and exists.
    """
    if not directory_path:
        raise HTTPException(status_code=400, detail="No path provided")

    if not os.path.isdir(directory_path):
        raise HTTPException(status_code=400, detail="Provided path is not a directory")
    

def process_file(file_path: str):
    """Ensure that the provided file is a .DAT File, and return the event data."""
    if not file_path.endswith(".DAT"):
        return None  # Skip non-DAT files
    parsed_data = parse_dat_file(file_path)
    return parsed_data if parsed_data else None


def process_directory(directory_path: str):
    """Process all .DAT files in the given directory and return parsed data."""
    final_data = []
    for folder in os.listdir(directory_path):
        folder_path = os.path.join(directory_path, folder)
        if not os.path.isdir(folder_path):
            continue  # Skip if it's not a directory
        
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            parsed_data = process_file(file_path)
            if parsed_data:
                final_data.extend(parsed_data)
    return final_data


def extract_all_zips(zip_path: str, extract_path: str):
    """
    Recursively extracts a ZIP file, handling nested ZIP files.
    Extracts all ZIPs into the given extract_path.
    """
    os.makedirs(extract_path, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    # Recursively extract any ZIP files found inside the extracted folder
    for inner_zip in Path(extract_path).rglob("*.zip"):
        temp_extract_path = inner_zip.with_suffix("")  # Remove ".zip" from path
        try:
            with zipfile.ZipFile(inner_zip, "r") as nested_zip:
                nested_zip.extractall(temp_extract_path)
            os.remove(inner_zip)  # Delete the extracted ZIP after processing
        except zipfile.BadZipFile:
            logger.warning(f"Skipping invalid ZIP file: {inner_zip}")

def extract_zips_from_input(temp_dir, url=None, file=None):
    """
    Extracts ZIP files from either a URL or an uploaded file.
    """
    extract_path = os.path.join(temp_dir, "extracted")
    os.makedirs(extract_path, exist_ok=True)

    if url:
        # Download the ZIP file from the URL
        zip_path = os.path.join(temp_dir, "input.zip")
        response = requests.get(url)
        if response.status_code == 200:
            with open(zip_path, "wb") as f:
                f.write(response.content)
        else:
            raise HTTPException(status_code=400, detail="Failed to download ZIP file from URL")
    elif file:
        # Save the uploaded file to the temp directory
        zip_path = os.path.join(temp_dir, file.filename)
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    else:
        raise HTTPException(status_code=400, detail="Either a file or a URL must be provided.")

    # Extract the ZIP file
    extract_all_zips(zip_path, extract_path)
    return extract_path

def has_enough_disk_space(required_space: int, path: str = ".") -> bool:
    """Check if there is enough disk space available."""
    disk_usage = shutil.disk_usage(path)
    return disk_usage.free >= required_space


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)  # Or `int(obj)` if appropriate
    raise TypeError("Type not serializable")