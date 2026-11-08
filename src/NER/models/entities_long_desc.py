from typing import Annotated, Literal, Union
from pydantic import Field

from .base import MentionBase


class PersonEntity(MentionBase):
    """A named human individual.

    Annotate the personal name only; exclude bare titles, ranks, honorifics and
    job labels (annotate "Chamberlain" or "Hitler", not "den minister" alone).
    The subtype reflects the social role most salient in the bulletin and drives
    the political, diplomatic, military and sports networks of interest.
    """

    type: Literal["Person"] = Field(description="A named human individual.")
    subtype: Literal[
        "Politician", "Military", "Diplomat", "Athlete", "Professional", "Other"
    ] | None = Field(
        description=(
            "Politician: holder of political office or party politician "
            "(e.g. Chamberlain, Halifax, Mussolini). "
            "Military: serviceperson or commander (e.g. generaal Winkelman). "
            "Diplomat: ambassador, envoy or treaty negotiator (e.g. Ribbentrop). "
            "Athlete: sportsperson named in a result or selection. "
            "Professional: other identifiable public professional "
            "(e.g. a named ship captain, industrialist or churchman). "
            "Other: clearly identified person not fitting the above. "
            "Null if no subtype is sufficiently supported by the text."
        )
    )


class OrganizationEntity(MentionBase):
    """A named collective body, institution, company, association or media outlet.

    Subtypes follow the research-oriented label categories so that political,
    military, economic, media, sports and party actors can be filtered and
    contrasted in analysis.
    """

    type: Literal["Organization"] = Field(description="A named organization or institution.")
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
            "Government: state body, ministry or administration "
            "(e.g. Britsche Regeering, Staten-Generaal). "
            "MilitaryOrganization: army, navy, air force or named unit "
            "(e.g. Wehrmacht, Royal Air Force). "
            "MediaOrganization: news agency, newspaper or broadcaster "
            "(e.g. Reuters, Havas, BBC). "
            "CommercialCompany: business, bank or shipping line "
            "(e.g. Holland-Amerikalijn, Bethlehem Steel). "
            "SportsClub: club or team (e.g. HHC, MCC, Ajax). "
            "PoliticalParty: party or political movement "
            "(e.g. fascistische partij). "
            "Association: other organized body (union, church body, committee). "
            "Null if uncertain."
        )
    )


class PlaceEntity(MentionBase):
    """A named geographic or geopolitical place."""

    type: Literal["Place"] = Field(description="A named geographic or geopolitical place.")
    subtype: Literal[
        "Country", "AdministrativeDivision", "Settlement", "NaturalFeature", "Infrastructure"
    ] | None = Field(
        description=(
            "Country: sovereign state (e.g. Duitschland, Vereenigde Staten, "
            "Vrije Stad Dantzig). "
            "AdministrativeDivision: province, region or district "
            "(e.g. Provincie Limburg, Yorkshire). "
            "Settlement: city, town or village (e.g. Amsterdam, Warschau, New York). "
            "NaturalFeature: sea, river, mountain or island "
            "(e.g. de Noordzee, de Rijn, de Moezel). "
            "Infrastructure: building, airport, stadium or bridge "
            "(e.g. Olympisch Stadion, Binnenhof, Vliegveld Schiphol). "
            "Null if uncertain."
        )
    )


class EventEntity(MentionBase):
    """A named or specifically identified event.

    Do not annotate generic activities or vague references. Subtypes match the
    research categories: armed conflict, diplomacy, sport and finance, plus a
    ``Political`` catch-all for elections and cabinet events and ``Other`` for
    clearly identified events outside the scheme.
    """

    type: Literal["Event"] = Field(description="A named or specifically identified event.")
    event_id: str | None = Field(
        description=(
            "ID linking mentions that refer to the same underlying event "
            "within this bulletin. Reuse the same ID for coreferential "
            "mentions. Use null if the reference cannot be resolved."
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
            "ArmedConflict: war, battle or military operation "
            "(e.g. Slag bij Tannenberg, den oorlog). "
            "DiplomaticMeeting: talks, conference or state visit between actors "
            "(e.g. onderhoud Ribbentrop en Stalin). "
            "SportsEvent: competition, race or match (e.g. Ronde van Frankrijk, "
            "kaatswedstrijden). "
            "FinancialEvent: market report or economic event "
            "(e.g. Overzicht New-Yorksche Beurs). "
            "Political: election, parliamentary event, cabinet formation or other "
            "identified political occurrence not covered above. "
            "Other: other specifically identified event. "
            "Null if uncertain."
        )
    )
    event_date: str | None = Field(
        description="Resolved event date in ISO YYYY-MM-DD format, or null."
    )
    date_resolution: Literal["explicit", "inferred", "unresolved"] | None = Field(
        description=(
            "How event_date was resolved. "
            "explicit = directly stated in the bulletin; "
            "inferred = unambiguous resolution using bulletin date or context; "
            "unresolved = a date expression exists but cannot be resolved; "
            "null = no date expression present."
        )
    )


class VehicleEntity(MentionBase):
    """A named individual vehicle: ship, aircraft, submarine or train.

    Named vessels and aircraft recur throughout 1939 bulletins (liners, "
    torpedoed ships, military aircraft) and anchor the maritime and military "
    materiel analysis.
    """

    type: Literal["Vehicle"] = Field(description="A named individual vehicle.")
    subtype: Literal["Ship", "Aircraft", "Submarine", "Train"] | None = Field(
        description=(
            "Ship: named surface vessel (e.g. SS Statendam). "
            "Aircraft: named or registered aircraft. "
            "Submarine: named or numbered submarine. "
            "Train: named train, or royal/troop train. "
            "Null if uncertain."
        )
    )

class LegalDocumentEntity(MentionBase):
    """A named legal or formal governmental document.

    Includes treaties (subtype ``Treaty``): the treaty as a legal instrument.
    A signing ceremony is annotated separately as an ``Event`` of subtype
    ``DiplomaticMeeting``.
    """

    type: Literal["LegalDocument"] = Field(
        description="A named legal or formal governmental document."
    )
    subtype: Literal["Treaty", "Law", "Decree", "Agreement", "Communique"] | None = Field(
        description=(
            "Treaty: pact, convention or agreement between parties "
            "(e.g. Russisch-Duitsche niet-aanvalsverdrag, Verdrag van Munchen). "
            "Law: statute or act. "
            "Decree: formal decree, order or ordinance. "
            "Agreement: bilateral or multilateral instrument other than a treaty. "
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


# Entity = Annotated[
#     Union[
#         PersonEntity,
#         OrganizationEntity,
#         PlaceEntity,
#         EventEntity,
#         VehicleEntity,
#         LegalDocumentEntity,
#     ],
#     Field(discriminator="type"),
# ]

