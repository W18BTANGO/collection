import logging
from dtos.collection_dtos import *
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_dat_lines(file_path: str) -> List[EventDTO]:
    """Parses lines from a .DAT file and extracts property records."""
    events = []
    current_time = datetime.now().isoformat()  # Current timestamp

    try:
        with open(file_path, 'r') as file:
            for line_number, line in enumerate(file, start=1):
                parts = line.strip().split(';')

                if parts[0] != 'B':  # Ensure record type is 'B'
                    continue

                if len(parts) < 20:
                    logger.warning(f"Skipping line {line_number}: Insufficient columns (found {len(parts)}, expected 20)")
                    continue

                try:
                    district_code = int(parts[1]) if parts[1].isdigit() else None
                    property_id = int(parts[2]) if parts[2].isdigit() else None
                    price = int(parts[15]) if parts[15] and parts[15].strip().isdigit() else None
                    land_area = float(parts[11]) if parts[11].replace('.', '', 1).isdigit() else None
                    timestamp = parts[13].strip() or current_time

                    if not property_id:
                        logger.warning(f"Skipping line {line_number}: Missing or invalid property_id")
                        continue
                    if not price:
                        logger.warning(f"Skipping line {line_number}: Missing or invalid price")
                        continue

                    event = EventDTO(
                        time_object=TimeObject(
                            timestamp=timestamp,
                            duration=0,
                            duration_unit="day",
                            timezone="AEDT",
                        ),
                        event_type="sales report",
                        attribute=HouseSaleDTO(
                            transaction_id=str(uuid.uuid4()),
                            district_code=district_code,
                            property_id=property_id,
                            price=price,
                            property_name=parts[5].strip() or "Unknown",
                            unit_number=parts[6].strip() or None,
                            street_number=parts[7].strip() or "",
                            street_name=parts[8].strip() or "",
                            suburb=parts[9].strip() or "",
                            postcode=parts[10].strip() or None,
                            land_area=land_area,
                            area_unit=parts[12].strip() or "",
                            contract_date=parts[13] or "",
                            settlement_date=parts[14].strip() or None,
                            zoning_code=parts[16].strip() or "",
                            property_type=parts[18].strip() or None,
                            sale_type=parts[17].strip() or None,
                            nature_of_property=parts[19].strip() if len(parts) > 19 else None,
                        )
                    )
                    events.append(event)

                except ValueError as ve:
                    logger.warning(f"Skipping line {line_number}: Data format issue ({ve})")
                    continue

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return []

    if not events:
        logger.warning(f"No valid events found in {file_path}")

    return events

def build_dataset_dto(events: List[EventDTO], dataset_id: str = "2024") -> DatasetDTO:
    """Constructs the final DatasetDTO from parsed events."""
    if not events:
        return None

    current_time = datetime.now().isoformat()

    dataset = DatasetDTO(
        data_source="NSW Valuer General",
        dataset_type="sales report",
        dataset_id=dataset_id,
        time_object=TimeObject(
            timestamp=current_time,
            duration=0,
            duration_unit="seconds",
            timezone="AEDT",
        ),
        events=events
    )
    logger.debug(f"Successfully built DatasetDTO with {len(events)} events")
    return dataset.model_dump()

def parse_dat_file(file_path: str) -> DatasetDTO:
    """Main function to parse a .DAT file and return the final DatasetDTO."""
    events = parse_dat_lines(file_path)
    return build_dataset_dto(events)


