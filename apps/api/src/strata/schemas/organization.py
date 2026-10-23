from typing import Optional
from pydantic import BaseModel, Field


class OrganizationRef(BaseModel):
    """Reference contract for an organization tenant."""
    org_id: str = Field(..., description="Organization UUID")
    name: str = Field(..., description="Organization legal or business name")
    org_type: str = Field(default="manufacturer", description="Enterprise type: manufacturer, recycler, municipality, cluster_authority")


class FacilityRef(BaseModel):
    """Reference contract for a manufacturing or processing site."""
    facility_id: str = Field(..., description="Facility UUID")
    org_id: str = Field(..., description="Owning organization UUID")
    name: str = Field(..., description="Facility site name")
    location_country: str = Field(default="US", description="Two-letter ISO country code")
    location_postal_code: Optional[str] = Field(default=None, description="Postal/ZIP code")
    location_coordinates: Optional[dict] = Field(default=None, description="Lat/Long geo coordinates")
