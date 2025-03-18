from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# Define request model for input
class ZipRequest(BaseModel):
    zip_url: str

class ParseRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL of the ZIP file to download")

class DirectoryPath(BaseModel):
    directory_path: str

class TimeObject(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the event")
    duration: Optional[int] = Field(0, description="Duration of the event")
    duration_unit: Optional[str] = Field("day", description="Unit of duration")
    timezone: str = Field("AEDT", description="Time zone")

class HouseSaleDTO(BaseModel):
    transaction_id: str = Field (None, description="primary DB Key")
    district_code: Optional[int] = Field(None, description="District code of the property")
    property_id: Optional[int] = Field(None, description="Unique identifier for the property")
    price: Optional[int] = Field(None, description="Price of the property")
    property_name: Optional[str] = Field("Unknown", description="Name of the property")
    unit_number: Optional[str] = Field(None, description="Unit number of the property")
    street_number: Optional[str] = Field("", description="Street number of the property")
    street_name: Optional[str] = Field("", description="Street name of the property")
    suburb: Optional[str] = Field("", description="Suburb of the property")
    postcode: Optional[str] = Field("", description="Postcode of the property")
    land_area: Optional[Decimal] = Field(None, description="Land area of the property")
    area_unit: Optional[str] = Field("", description="Unit of land area")
    contract_date: Optional[str] = Field(None, description="Contract date of the sale")
    settlement_date: Optional[str] = Field(None, description="Settlement date of the sale")
    zoning_code: Optional[str] = Field("", description="Zoning code of the property")
    property_type: Optional[str] = Field("", description="Type of property")
    sale_type: Optional[str] = Field("", description="Type of sale")
    nature_of_property: Optional[str] = Field(None, description="Nature of the property")

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