import pytest
from fastapi import HTTPException
import os
import tempfile
import shutil
from app.utils import (
    load_env_variables,
    validate_directory,
    process_file,
    process_directory,
    extract_all_zips,
    extract_zips_from_input,
    has_enough_disk_space,
    decimal_to_float
)
from app.services.collection_service import parse_dat_file
from decimal import Decimal
from unittest.mock import patch, MagicMock

def test_validate_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        validate_directory(temp_dir)
        with pytest.raises(HTTPException):
            validate_directory("invalid_directory")

def test_extract_all_zips():
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "test.zip")
        extract_path = os.path.join(temp_dir, "extracted")
        with tempfile.TemporaryDirectory() as temp_extract_dir:
            with open(os.path.join(temp_extract_dir, "file1.DAT"), 'w') as f:
                f.write("B;12345;67890;John Doe;45;Property Name;1A;Street Number;Street Name;Suburb;2000;500;sq.m;2024-01-01;2024-02-01;1500000;Residential;Sale Type;House;ExtraField1;ExtraField2\n")
            shutil.make_archive(base_name=zip_path.replace('.zip', ''), format='zip', root_dir=temp_extract_dir)
        extract_all_zips(zip_path, extract_path)
        assert os.path.exists(os.path.join(extract_path, "file1.DAT"))

def test_has_enough_disk_space():
    assert has_enough_disk_space(1) == True
    assert has_enough_disk_space(10**12) == False

def test_decimal_to_float():
    assert decimal_to_float(Decimal('10.5')) == 10.5
    with pytest.raises(TypeError):
        decimal_to_float("string")
