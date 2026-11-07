from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class MentionBase(StrictModel):
    id: str = Field(description="Unique ID for this textual mention within the bulletin.")
    text: str = Field(description="Exact substring copied from the original bulletin.")
    normalized_name: str | None
    start: int = Field(ge=0, description="Zero-based character offset of the first character of the entity. Inclusive.")
    end: int = Field(gt=0, description="Zero-based character offset immediately after the last character of the entity. Exclusive.")
    annotation_confidence: float = Field(
        ge=0.0, le=1.0,
        description="Subjective confidence in this annotation; not a calibrated probability."
    )

