from fastapi import APIRouter, HTTPException
import os
from services.collection_service import parse_dat_file


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