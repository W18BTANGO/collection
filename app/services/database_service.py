import requests
import zipfile
import logging
import boto3
import os
from dotenv import load_dotenv
from app.utils import *
from app.dtos.collection_dtos import EventDTO, HouseSaleDTO
from typing import List

env_path = os.path.abspath("../local.env")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
overwrite_keys = ["transaction_id"] if "transaction_id" else None

logger.info("Reading in secret keys from local.env")

MAX_FILE_SIZE = 100 * 1024 * 1024


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


class DatabaseService:
    def __init__(self, dynamodb_table):
        """
        Initialize the DatabaseService with a DynamoDB table.
        """
        self.table = dynamodb_table

    def insert_events_into_db(self, all_events: List[EventDTO]):
        """
        Insert a list of events into the DynamoDB table.
        """
        try:
            with self.table.batch_writer(overwrite_by_pkeys=overwrite_keys) as batch:
                logger.debug(f"Total events to insert: {len(all_events)}")
                
                for event in all_events:
                    attribute = event.attribute
                    # Convert HouseSaleDTO instance to dictionary
                    if isinstance(attribute, HouseSaleDTO):
                        attribute_dict = attribute.dict()
                    else:
                        attribute_dict = attribute

                    # Check if the attribute has a 'property_id'
                    if attribute_dict.get("property_id") is None:
                        logger.debug(f"Skipping event with missing property_id: {attribute_dict}")
                        continue
                    
                    # Convert property_id to string if it exists
                    if attribute_dict.get("property_id"):
                        attribute_dict["property_id"] = str(attribute_dict["property_id"])
                    
                    # Insert the event into the database
                    batch.put_item(Item=attribute_dict)
            
            return {"message": f"Successfully inserted {len(all_events)} events into the database."}

        except Exception as e:
            logger.error(f"Error inserting events into the database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error inserting events into the database: {str(e)}")