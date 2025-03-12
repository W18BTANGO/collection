import json
import os
import pandas as pd

def parse_dat_file(file_path):
    """Parses a .DAT file and extracts relevant property records."""
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            parts = line.strip().split(';')
            record_type = parts[0]

            if record_type == 'B':
                try:
                    record = {
                        "district_code": int(parts[1]),
                        "property_id": int(parts[2]),
                        "price": int(parts[15]) if parts[15] and parts[15].strip().isdigit() else None,
                        "property_name": parts[5],
                        "unit_number": parts[6] if parts[6].strip() else None,  # Ensure empty values become None
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
                    data.append(record)
                except (IndexError, ValueError) as e:
                    print(f"Skipping malformed record: {line.strip()} - Error: {e}")
    return data

# Directory containing subdirectories with .DAT files
my_dir = "2024"
dir_list = os.listdir(my_dir)

# Initialize an empty DataFrame
output_df = pd.DataFrame()

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
                temp_df = pd.DataFrame(parsed_data)
                output_df = pd.concat([output_df, temp_df], ignore_index=True)

    if not output_df.empty:
        """
        # Normalize empty unit numbers to None
        output_df['unit_number'] = output_df['unit_number'].replace("", None)

        # Convert settlement_date to datetime for sorting
        output_df['settlement_date'] = pd.to_datetime(output_df['settlement_date'], errors='coerce')

        # Keep only the latest entry for each (property_id, unit_number) based on settlement_date
        output_df = output_df.loc[
            output_df.groupby(['property_id', output_df['unit_number'].fillna('')])['settlement_date'].idxmax()
        ]
        """

        print(f"Final DataFrame shape: {output_df.shape}")
        print(output_df.head())

        # Save to JSON
        json_output_path = 'output_file.json'
        output_df.to_json(json_output_path, orient="records", indent=4)
        print(f"Data has been converted to JSON and saved to {json_output_path}")

except Exception as e:
    print(f"Error processing files: {e}")