
from typing import Literal
from pydantic import Field

from .base import MentionBase


class PersonEntity(MentionBase):
    """A named human individual."""

    type: Literal["Person"] = Field(
        description="A named human individual."
    )
    subtype: Literal[
        "Politician",
        "Military",
        "Diplomat",
        "Athlete",
        "Professional",
        "Other",
    ] | None = Field(
        description=(
            "Politician: political officeholder or party politician. "
            "Military: serviceperson or military commander. "
            "Diplomat: ambassador, envoy or diplomatic negotiator. "
            "Athlete: named sportsperson. "
            "Professional: other identifiable public professional. "
            "Other: identifiable person outside these categories. "
            "Null if uncertain."
        )
    )


class OrganizationEntity(MentionBase):
    """A named institution, collective body, company or association."""

    type: Literal["Organization"] = Field(
        description="A named organization or institution."
    )

    subtype: Literal[
        "Government",
        "MilitaryOrganization",
        "MediaOrganization",
        "CommercialCompany",
        "SportsClub",
        "PoliticalParty",
        "Association",
    ] | None = Field(
        description=(
            "Government: state body, ministry or administration. "
            "MilitaryOrganization: armed forces or military unit. "
            "MediaOrganization: news agency, newspaper or broadcaster. "
            "CommercialCompany: company, bank or commercial business. "
            "SportsClub: sports club or team. "
            "PoliticalParty: political party or movement. "
            "Association: other organized collective body. "
            "Null if uncertain."
        )
    )


class PlaceEntity(MentionBase):
    """A named geographic, geopolitical or infrastructural place."""

    type: Literal["Place"] = Field(
        description="A named geographic or infrastructural place."
    )

    subtype: Literal[
        "Country",
        "AdministrativeDivision",
        "Settlement",
        "NaturalFeature",
        "Infrastructure",
    ] | None = Field(
        description=(
            "Country: sovereign state or geopolitical entity. "
            "AdministrativeDivision: province, region or district. "
            "Settlement: city, town or village. "
            "NaturalFeature: sea, river, mountain or island. "
            "Infrastructure: named building, airport, stadium or bridge. "
            "Null if uncertain."
        )
    )


class EventEntity(MentionBase):
    """A named or specifically identifiable event."""

    type: Literal["Event"] = Field(
        description="A named or specifically identifiable event."
    )

    event_id: str | None = Field(
        description=(
            "Bulletin-local ID for the underlying event. "
            "Reuse the same ID for different mentions of the same event. "
            "Assign IDs in order of first occurrence (event_1, event_2, etc.). "
            "Use null when the event reference cannot be resolved confidently."
        )
    )

    subtype: Literal[
        "ArmedConflict",
        "DiplomaticMeeting",
        "SportsEvent",
        "FinancialEvent",
        "Political",
        "Other",
    ] | None = Field(
        description=(
            "ArmedConflict: war, battle or military operation. "
            "DiplomaticMeeting: diplomatic talks, conference or state visit. "
            "SportsEvent: competition, race or match. "
            "FinancialEvent: financial market report or economic event. "
            "Political: election, parliamentary event or cabinet occurrence. "
            "Other: specifically identified event outside these categories. "
            "Null if uncertain."
        )
    )

    event_date: str | None = Field(
        description="Resolved event date in ISO YYYY-MM-DD format, or null."
    )

    date_resolution: Literal[
        "explicit",
        "inferred",
        "unresolved",
    ] | None = Field(
        description=(
            "explicit: date directly stated in the bulletin. "
            "inferred: unambiguous date resolved from bulletin_date or context. "
            "unresolved: temporal expression exists but cannot be resolved. "
            "Null if no temporal expression is present."
        )
    )


class VehicleEntity(MentionBase):
    """A named individual vehicle."""

    type: Literal["Vehicle"] = Field(
        description="A named individual vehicle."
    )

    subtype: Literal[
        "Ship",
        "Aircraft",
        "Submarine",
        "Train",
    ] | None = Field(
        description=(
            "Ship: named surface vessel. "
            "Aircraft: named or registered aircraft. "
            "Submarine: named or numbered submarine. "
            "Train: named train or specifically identified royal or troop train. "
            "Null if uncertain."
        )
    )


class LegalDocumentEntity(MentionBase):
    """A named legal or formal governmental document."""

    type: Literal["LegalDocument"] = Field(
        description="A named legal or formal governmental document."
    )

    subtype: Literal[
        "Treaty",
        "Law",
        "Decree",
        "Agreement",
        "Communique",
    ] | None = Field(
        description=(
            "Treaty: pact, convention or treaty between parties. "
            "Law: statute or act. "
            "Decree: formal governmental decree or order. "
            "Agreement: formal agreement other than a treaty. "
            "Communique: official governmental or diplomatic statement. "
            "Null if uncertain."
        )
    )


Entity = (
    PersonEntity
    | OrganizationEntity
    | PlaceEntity
    | EventEntity
    | VehicleEntity
    | LegalDocumentEntity
)
