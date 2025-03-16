from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

# Define request model for input
class ZipRequest(BaseModel):
    zip_url: str

class DirectoryPath(BaseModel):
    directory_path: str


class TimeObject(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the event")
    duration: Optional[int] = Field(0, description="Duration of the event")
    duration_unit: Optional[str] = Field("day", description="Unit of duration")
    timezone: str = Field("AEDT", description="Time zone")

class HouseSaleDTO(BaseModel):
    district_code: int
    property_id: int
    price: Optional[int]
    property_name: str
    unit_number: Optional[str]
    street_number: str
    street_name: str
    suburb: str
    postcode: str
    land_area: Optional[float]
    area_unit: str
    contract_date: str
    settlement_date: str
    zoning_code: str
    property_type: str
    sale_type: str
    nature_of_property: Optional[str]

class EventDTO(BaseModel):
    time_object: TimeObject
    event_type: str = Field("sales report", description="Type of event")
    attribute: HouseSaleDTO

class DatasetDTO(BaseModel):
    data_source: str = Field("NSW Valuer General", description="Source of the dataset")
    dataset_type: str = Field("sales report", description="Dataset type")
    dataset_id: str = Field("2024", description="Dataset identifier")
    time_object: TimeObject
    events: List[EventDTO]

class FileUploadResponseDTO(BaseModel):
    message: str
    file_url: str