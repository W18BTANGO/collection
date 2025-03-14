import pytest
from fastapi.testclient import TestClient
from app.main import app  # Assuming your FastAPI app is in the file app.py
import os
import tempfile
import json

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
        dat_content = "B;12345;67890;John Doe;45;Property Name;1A;Street Number;Street Name;Suburb;2000;500;sq.m;2024-01-01;2024-02-01;1500000;Residential;Sale Type;House\n"
        with open(os.path.join(folder1, "file1.DAT"), 'w') as f:
            f.write(dat_content)
        
        with open(os.path.join(folder2, "file2.DAT"), 'w') as f:
            f.write(dat_content)

        yield tmpdir

def test_parse_directory_success(client, mock_dat_files):
    # Test successful parsing
    response = client.post('/parse', json={"directory_path": '../test'})
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0  # There should be some events in the response

def test_parse_directory_no_path(client):
    # Test no directory path provided
    response = client.post('/parse_directory', json={})
    
    assert response.status_code == 404  # Unprocessable Entity status code
    data = response.json()
    assert 'detail' in data  # Make sure 'detail' key exists


def test_parse_directory_invalid_path(client):
    # Test invalid directory path
    response = client.post('/parse', json={"directory_path": "/invalid/path"})
    
    assert response.status_code == 400
    data = response.json()
    print(data)
    assert data['detail'] == 'Provided path is not a directory'

def test_parse_directory_no_dat_files(client, mock_dat_files):
    # Create an empty folder to test case with no .DAT files
    empty_folder = os.path.join(mock_dat_files, "empty_folder")
    os.makedirs(empty_folder)

    response = client.post('/parse', json={"directory_path": empty_folder})

    assert response.status_code == 404
    data = response.json()
    print(data)
    assert data['detail'] == 'No data found to parse'
