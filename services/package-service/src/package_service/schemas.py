from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from package_service.versions import parse_version

MAX_VERSION_PART = 100


class PackageCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    name: str = Field(
        ..., min_length=2, max_length=100, pattern=r"^[a-z][a-z0-9-]*$"
    )
    description: str = Field(default="", max_length=500)


class PackageOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    name: str
    description: str
    created_at: datetime
    latest_version: str | None = None
    

class ReleaseCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
        )

    version: str = Field(max_length=15)

    @field_validator("version")
    @classmethod
    def check_version(cls, value: str) -> str:
        if max(parse_version(value)) > MAX_VERSION_PART:
            raise ValueError(f"version parts must be at most {MAX_VERSION_PART}")
        return value


class ReleaseOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    version: str
    released_at: datetime