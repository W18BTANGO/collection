from fastapi import APIRouter, HTTPException
import os
from services.collection_service import parse_dat_file
import zipfile
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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