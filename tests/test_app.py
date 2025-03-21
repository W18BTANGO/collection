import pytest
from fastapi.testclient import TestClient
from main import app
import os
import tempfile
import json
import shutil

client = TestClient(app)

@pytest.fixture
def client():
    # Create a test client for the FastAPI app
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_dat_files():
    # Create a temporary directory with mock .DAT files for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        folder1 = os.path.join(tmpdir, "folder1")
        folder2 = os.path.join(tmpdir, "folder2")

        os.makedirs(folder1)
        os.makedirs(folder2)

        # Create mock .DAT files
        dat_content = "B;12345;67890;John Doe;45;Property Name;1A;Street Number;Street Name;Suburb;2000;500;sq.m;2024-01-01;2024-02-01;1500000;Residential;Sale Type;House;ExtraField1;ExtraField2;ExtraField2;ExtraField2;ExtraField2\n"
        with open(os.path.join(folder1, "file1.DAT"), 'w') as f:
            f.write(dat_content)
        
        with open(os.path.join(folder2, "file2.DAT"), 'w') as f:
            f.write(dat_content)

        yield tmpdir

def test_parse_directory_success(client, mock_dat_files):
    # Test successful parsing
    zip_path = os.path.join(mock_dat_files, "test.zip")
    shutil.make_archive(base_name=zip_path.replace('.zip', ''), format='zip', root_dir=mock_dat_files)
    
    with open(zip_path, "rb") as file:
        response = client.post('/collection/parse/dat/directory', files={"file": file})
    
    if response.status_code != 200:
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0  # There should be some events in the response

def test_parse_directory_no_path(client):
    # Test no directory path provided
    response = client.post('/collection/parse/dat/directory', json={})
    
    assert response.status_code == 400  # Bad Request status code
    data = response.json()
    assert 'detail' in data  # Make sure 'detail' key exists

def test_parse_directory_invalid_path(client):
    # Test invalid directory path
    response = client.post('/collection/parse/dat/directory', json={"url": "/invalid/path"})
    
    assert response.status_code == 400
    data = response.json()
    assert data['detail'] == 'Invalid URL'

def test_parse_directory_no_dat_files(client, mock_dat_files):
    # Create an empty folder to test case with no .DAT files
    empty_folder = os.path.join(mock_dat_files, "empty_folder")
    os.makedirs(empty_folder)

    response = client.post('/collection/parse/dat/directory')

    assert response.status_code == 400
    data = response.json()
    assert data['detail'] == 'Either a file or a URL must be provided.'

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 404
    assert response.json() == {"detail": "Data collection service. Please specify an endpoint"}
