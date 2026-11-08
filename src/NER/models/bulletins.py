from pydantic import BaseModel, ConfigDict, model_validator, Field
from typing import Literal
from datetime import date, datetime, timezone
from typing import Self

from .entities import Entity



TOPICS = Literal["politics", "military", "economy", "sports", "weather", "other"]


class BulletinInput(BaseModel):
    bulletin_id: str
    text: str
    bulletin_date: str | None = None

    @model_validator(mode="after")
    def compute_bulletin_date(self) -> Self:
        self.bulletin_date = parse_bulletin_id(self.bulletin_id)
        return self


class NERExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topics: list[TOPICS]
    entities: list[Entity]


class NEROutput(BaseModel):

    bulletin_id: str
    bulletin_date: str | None

    topics: list[TOPICS]
    entities: list[Entity]

    language: Literal["nl"] 
    schema_version: str
    annotation_guideline_version: str
    text: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    model: str

    

def parse_bulletin_id(bulletin_id: str) -> str | None:
    parts = bulletin_id.split(":")
    try:
        inferred_date = date(int(parts[2]), int(parts[3]), int(parts[4])).isoformat()
    except ValueError:
        inferred_date = None
    return inferred_date
