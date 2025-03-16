from datetime import datetime
from typing import Optional
import logging
from ..dtos.collection_dtos import *

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Function to parse .DAT file and convert to Adage 3.0 format
def parse_dat_file(file_path: str) -> Optional[DatasetDTO]:
    """Parses a .DAT file and extracts relevant property records, converting them to Adage 3.0 format."""
    events = []
    current_time = datetime.now().isoformat()  # Current timestamp for the dataset

    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split(';')
                if parts[0] == 'B':  # Check for record type 'B'
                    # Construct DTO objects
                    event = EventDTO(
                        time_object=TimeObject(
                            timestamp=parts[13],  # Use contract_date as the event timestamp
                            duration=0,
                            duration_unit="day",
                            timezone="AEDT",
                        ),
                        event_type="sales report",
                        attribute=HouseSaleDTO(
                            district_code=int(parts[1]),
                            property_id=int(parts[2]),
                            price=int(parts[15]) if parts[15] and parts[15].strip().isdigit() else None,
                            property_name=parts[5],
                            unit_number=parts[6] if parts[6].strip() else None,
                            street_number=parts[7],
                            street_name=parts[8],
                            suburb=parts[9],
                            postcode=parts[10],
                            land_area=float(parts[11]) if parts[11] and 
                                parts[11].strip().replace('.', '', 1).isdigit() else None,
                            area_unit=parts[12],
                            contract_date=parts[13],
                            settlement_date=parts[14],
                            zoning_code=parts[16],
                            property_type=parts[18],
                            sale_type=parts[17],
                            nature_of_property=parts[19] if len(parts) > 19 else None
                        )
                    )
                    events.append(event)

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return None

    # Return the complete dataset in Adage 3.0 format using DTO
    return DatasetDTO(
        data_source="NSW Valuer General",
        dataset_type="sales report",
        dataset_id="2024",  # Temporary value
        time_object=TimeObject(
            timestamp=current_time,  # Use the current time for dataset timestamp
            timezone="AEDT"
        ),
        events=events
    )