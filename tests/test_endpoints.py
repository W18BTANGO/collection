import sys
import os
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient
from main import app  # Updated import
import tempfile
import json
from unittest.mock import patch, MagicMock
from app.utils import load_env_variables
import shutil

# Ensure the parent directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.abspath("../local.env")
load_env_variables(env_path)

client = TestClient(app)

@pytest.fixture(scope="class")
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="class")
def mock_dynamodb():
    with patch("boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_resource.return_value.meta.client.meta.region_name = os.getenv("AWS_REGION")
        yield mock_table

@pytest.fixture(scope="class")
def mock_s3():
    with patch("boto3.client") as mock_client:
        mock_client.return_value.upload_fileobj = MagicMock()
        yield mock_client

@pytest.fixture
def mock_dat_files():
    # Create a temporary directory with mock .DAT files for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        folder1 = os.path.join(tmpdir, "folder1")
        folder2 = os.path.join(tmpdir, "folder2")

        os.makedirs(folder1)
        os.makedirs(folder2)

        # Create mock .DAT files
        dat_content = "B;12345;67890;John Doe;45;Property Name;1A;Street Number;Street Name;Suburb;2000;500;sq.m;2024-01-01;2024-02-01;1500000;Residential;Sale Type;House;ExtraField1;ExtraField2;ExtraField2;ExtraField2;\n"
        with open(os.path.join(folder1, "file1.DAT"), 'w') as f:
            f.write(dat_content)
        
        with open(os.path.join(folder2, "file2.DAT"), 'w') as f:
            f.write(dat_content)

        yield tmpdir

@pytest.mark.usefixtures("client", "mock_dynamodb", "mock_s3")
class TestEndpoints:

    def test_read_root(self, client):
        response = client.get("/")
        assert response.status_code == 404
        assert response.json() == {"detail": "Data collection service. Please specify an endpoint"}

    def test_parse_directory_folder_file_upload(self, client, mock_dat_files):
        # Create a zip file from the mock .DAT files
        zip_path = os.path.join(mock_dat_files, "test.zip")
        shutil.make_archive(base_name=zip_path.replace('.zip', ''), format='zip', root_dir=mock_dat_files)
        # Test file upload
        with open(os.path.join(mock_dat_files, zip_path), "rb") as file:
            response = client.post('/collection/parse/dat/directory', files={"file": file})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # There should be some events in the response

#    def test_parse_directory_folder_url_input(self, client, requests_mock):
#        # Mock the URL to return a valid response
#        requests_mock.get("https://www.valuergeneral.nsw.gov.au/__psi/weekly/20250106.zip", content=b"dummy zip content", headers={"Content-Type": "application/zip"})
#
#        response = client.post(
#            "/collection/parse/dat/directory",
#            json={"url": "https://www.valuergeneral.nsw.gov.au/__psi/weekly/20250106.zip"}
#        )
#        
#        assert response.status_code == 200
#        assert isinstance(response.json(), list)

    def test_parse_directory_folder_invalid_input(self, client):
        response = client.post("/collection/parse/dat/directory")
        assert response.status_code == 400
        assert response.json() == {"detail": "Either a file or a URL must be provided."}

    def test_build_final_dataset(self, client, mock_dat_files):
        # Test building final dataset
        # Create a zip file from the mock .DAT files
        zip_path = os.path.join(mock_dat_files, "test.zip")
        shutil.make_archive(base_name=zip_path.replace('.zip', ''), format='zip', root_dir=mock_dat_files)

        # Test file upload
        with open(os.path.join(mock_dat_files, zip_path), "rb") as file:
            response = client.post('/collection/parse/dat/toevent', files={"file": file})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "events" in data  # Ensure the response contains events

    def test_events_into_db(self, client, mock_dynamodb):
        mock_batch_writer = MagicMock()
        mock_dynamodb.batch_writer.return_value.__enter__.return_value = mock_batch_writer

        dummy_events = [
            {"time_object": {"timestamp": "2024-01-01T00:00:00", "duration": 0, "duration_unit": "day", "timezone": "AEDT"},
             "event_type": "sales report",
             "attribute": {"transaction_id": "txn123", "property_id": 123, "price": 250000, "location": "New York"}},
            {"time_object": {"timestamp": "2024-01-01T00:00:00", "duration": 0, "duration_unit": "day", "timezone": "AEDT"},
             "event_type": "sales report",
             "attribute": {"transaction_id": "txn456", "property_id": 456, "price": 300000, "location": "Los Angeles"}}
        ]
        response = client.put(
            "/collection/uploadtoDB",
            json=dummy_events
        )
        
        assert response.status_code == 200

    def test_upload_file(self, client, mock_s3):
        dummy_file = ("test.txt", b"dummy content", "text/plain")

        response = client.post(
            "/upload",
            files={"file": dummy_file}
        )
        
        assert response.status_code == 200
        assert response.json() == {
            "message": "File uploaded successfully",
            "file_url": f"https://{os.getenv('S3_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/uploads/test.txt"
        }

    def test_download_from_s3(self, client):
        response = client.get("/download/test.txt")
        assert response.status_code == 200
        assert response.json() == {
            "download_url": f"https://{os.getenv('S3_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/uploads/test.txt"
        }