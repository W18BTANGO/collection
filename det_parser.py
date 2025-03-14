import json
import os
import pandas as pd
from datetime import datetime

def parse_dat_file(file_path):
    """Parses a .DAT file and extracts relevant property records, converting them to Adage 3.0 format."""
    events = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # Current timestamp for the dataset
    for line in open(file_path, 'r'):
        parts = line.strip().split(';')
        record_type = parts[0]

        if record_type == 'B':
            try:
                # Create the event structure for Adage 3.0 format
                event = {
                    "time_object": {
                        "timestamp": parts[13],  # Use contract_date as the event timestamp
                        "duration": 0,
                        "duration_unit": "day",
                        "timezone": "AEDT",
                    },
                    "event_type": "sales report",
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
            except (IndexError, ValueError) as e:
                print(f"Skipping malformed record: {line.strip()} - Error: {e}")

    # Return the complete dataset in Adage 3.0 format
    return {
        "data_source": "NSW Valuer General",
        "dataset_type": "sales reports",
        "dataset_id": "2024",  # Temporary value
        "time_object": {
            "timestamp": current_time,  # Use the current time for dataset timestamp
            "timezone": "AEDT"
        },
        "events": events
    }

# Directory containing subdirectories with .DAT files
my_dir = "../2024"
dir_list = os.listdir(my_dir)

# Initialize a list to hold the final JSON structure
final_data = []

try:
    for folder in dir_list:
        folder_path = os.path.join(my_dir, folder)
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
        # Save to JSON
        json_output_path = 'output_file.json'
        with open(json_output_path, 'w') as json_file:
            json.dump(final_data, json_file, indent=4)
        
        print(f"Data has been converted to JSON and saved to {json_output_path}")
    else:
        print("No data to write.")

except Exception as e:
    print(f"Error processing files: {e}")
