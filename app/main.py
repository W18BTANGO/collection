import os
import zipfile
import requests
import pandas as pd
from datetime import datetime
from io import BytesIO
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Collection API", description="API for collecting housing data", version="1.0.0")

# Define request model for input
class ZipRequest(BaseModel):
    zip_url: str

class DirectoryPath(BaseModel):
    directory_path: str

# Function to parse .DAT file and convert to Adage 3.0 format
def parse_dat_file(file_path: str) -> Optional[Dict]:
    """Parses a .DAT file and extracts relevant property records, converting them to Adage 3.0 format."""
    events = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # Current timestamp for the dataset
    try:
        for line in open(file_path, 'r'):
            parts = line.strip().split(';')
            record_type = parts[0]

            if record_type == 'B':
                # Create the event structure for Adage 3.0 format
                event = {
                    "time_object": {
                        "timestamp": parts[13],  # Use contract_date as the event timestamp
                        "duration": 0,
                        "duration_unit": "day",
                        "timezone": "AEDT",
                    },
                    "event_type": "sales report",  # For simplicity, using 'sensor reading'
                    "attribute": {
                        "district_code": int(parts[1]),
                        "property_id": int(parts[2]),
                        "price": int(parts[15]) if parts[15] and parts[15].strip().isdigit() else None,
                        "property_name": parts[5],
                        "unit_number": parts[6] if parts[6].strip() else None,
                        "street_number": parts[7],
                        "street_name": parts[8],
                        "suburb": parts[9],
                        "postcode": parts[10],
                        "land_area": float(parts[11]) if parts[11] and parts[11].strip().replace('.', '', 1).isdigit() else None,
                        "area_unit": parts[12],
                        "contract_date": parts[13],
                        "settlement_date": parts[14],
                        "zoning_code": parts[16],
                        "property_type": parts[18],
                        "sale_type": parts[17],
                        "nature_of_property": parts[19] if len(parts) > 19 else None
                    }
                }
                events.append(event)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None

    # Return the complete dataset in Adage 3.0 format
    return {
        "data_source": "NSW Valuer General",
        "dataset_type": "sales report",
        "dataset_id": "2024",  # Temporary value
        "time_object": {
            "timestamp": current_time,  # Use the current time for dataset timestamp
            "timezone": "AEDT"
        },
        "events": events
    }
@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.post("/parse", response_model=List[Dict])
async def parse_directory(request: DirectoryPath):
    directory_path = request.directory_path

    if not directory_path:
        raise HTTPException(
            status_code=400,
            detail=f"No path provided"
        )

    if not os.path.isdir(directory_path):
        raise HTTPException(
            status_code=400,
            detail=f'Provided path is not a directory'
        )


    final_data = []

    try:
        dir_list = os.listdir(directory_path)

        for folder in dir_list:
            folder_path = os.path.join(directory_path, folder)
            if not os.path.isdir(folder_path):
                continue  # Skip if it's not a directory

            temp_dir_list = os.listdir(folder_path)
            for file in temp_dir_list:
                file_path = os.path.join(folder_path, file)
                if not file.endswith(".DAT"):
                    continue  # Skip non-DAT files

                parsed_data = parse_dat_file(file_path)
                if parsed_data:
                    final_data.append(parsed_data)

        if final_data:
            return final_data
        else:
            raise HTTPException(
            status_code=400,
            detail=f"No data found to parse"
        )

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f'No data found to parse'
        )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
