from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Request bodies reject unknown fields (security.mdc: strict input validation)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
