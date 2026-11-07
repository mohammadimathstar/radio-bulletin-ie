from typing import Annotated, Literal, Union
from pydantic import Field

from .base import MentionBase


class PersonEntity(MentionBase):
    """A named human individual. Annotate the personal name only, excluding titles, ranks, honorifics, and job labels."""
    type: Literal["Person"] = Field(description="A named human individual.")
    subtype: Literal[
        "Politician", "Military", "Diplomat", "Professional", "Athlete"
    ] | None = Field(
        description="Politician: political officeholder/party politician; " \
                    "Military: military person; Diplomat: diplomatic representative; " \
                    "Professional: other identifiable profession; " \
                    "Athlete: sportsperson. " \
                    "Null if no subtype is sufficiently supported."
    )


class OrganizationEntity(MentionBase):
    """A named collective body, institution, company, association, or media organization."""
    type: Literal["Organization"] = Field(description="A named organization or institution.")
    subtype: Literal[
        "Government", "Military", "Media", "Company", "Association"
    ] | None = Field(
        description="Government: state body or administration; " \
        "Military: armed force/unit/institution; " \
        "Media: newspaper, broadcaster, or news organization; " \
        "Company: commercial enterprise; " \
        "Association: other organized association. " \
        "Null if uncertain."
    )


class PlaceEntity(MentionBase):
    """A named geographic or geopolitical place."""
    type: Literal["Place"] = Field(description="A named geographic or geopolitical place.")
    subtype: Literal[
        "Country", "Region", "Settlement", "Feature"
    ] | None = Field(
        description="Country: country/state; " \
        "Region: geographic or administrative region; " \
        "Settlement: city/town/village; " \
        "Feature: named geographic feature such as river, sea, mountain, or island. " \
        "Null if uncertain."
    )


class EventEntity(MentionBase):
    """A named or specifically identified event. Do not annotate generic activities or vague event references."""
    type: Literal["Event"] = Field(description="A named or specifically identified event.")
    subtype: Literal[
        "Conflict", "Political", "Sports", "Economic", "Other"
    ] | None = Field(
        description="Conflict: war, battle, or military conflict; " \
        "Political: political meeting, election, conference, or state event; " \
        "Sports: match, race, or competition; " \
        "Economic: strike, market/economic event, or industrial event; " \
        "Other: other specifically identified event. Null if uncertain."
    )
    event_date: str | None = Field(
        description="Resolved event date in ISO YYYY-MM-DD format, or null."
    )
    date_resolution: Literal["explicit", "inferred", "unresolved"] | None = Field(
        description="How event_date was resolved. explicit = directly stated; " \
        "inferred = unambiguous resolution using bulletin date/context; " \
        "unresolved = expression exists but date cannot be resolved; " \
        "null = no date expression."
    )
    

class VehicleEntity(MentionBase):
    """A named individual vehicle such as a ship, aircraft, or submarine."""
    type: Literal["Vehicle"] = Field(description="A named individual vehicle.")
    subtype: Literal["Ship", "Aircraft", "Submarine"] | None = Field(
        description="Ship: named vessel; " \
        "Aircraft: named or registered aircraft; " \
        "Submarine: named/numbered submarine." \
        "Null if uncertain."
    )


class LegalDocumentEntity(MentionBase):
    """A named legal or formal governmental document."""
    type: Literal["LegalDocument"] = Field(description="A named legal or formal governmental document.")
    subtype: Literal["Treaty", "Law", "Decree"] | None = Field(
        description="Treaty: treaty or agreement; " \
        "Law: statute or law; " \
        "Decree: formal decree/order. " \
        "Null if uncertain."
    )


Entity = Annotated[
    Union[
        PersonEntity,
        OrganizationEntity,
        PlaceEntity,
        EventEntity,
        VehicleEntity,
        LegalDocumentEntity,
    ],
    Field(discriminator="type"),
]

