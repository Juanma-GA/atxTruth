from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Request bodies reject unknown fields (security.mdc: strict input validation)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def sent_fields(model: BaseModel, *, exclude_none: bool = False) -> dict[str, object]:
    """Fields the client actually sent, keeping nested models (e.g. TranslatableText) as objects."""
    data = {name: getattr(model, name) for name in model.model_fields_set}
    if exclude_none:
        data = {k: v for k, v in data.items() if v is not None}
    return data
