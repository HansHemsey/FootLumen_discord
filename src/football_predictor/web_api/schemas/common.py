"""Common public DTOs for the FootLumen API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PublicModel(BaseModel):
    """Base class for public API DTOs."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(PublicModel):
    status: str
    api_enabled: bool
    read_only: bool
    database_ok: bool
    app_timezone: str
    version: str
    timestamp: datetime


class VersionResponse(PublicModel):
    name: str
    version: str
    api_version: str
    read_only: bool
