from typing import Literal
from pydantic import BaseModel, Field#, model_validator

# from .base import StrictModel

RELATION_SCHEMA: dict[str, set[tuple[str, str]]] = {
    "member_of": {("Person", "Organization"), ("Organization", "Organization")},
    "leads": {("Person", "Organization"), ("Organization", "Organization")},
    "affiliated_with": {("Person", "Organization"), ("Organization", "Organization")},
    "interacts_with": {
        ("Person", "Person"), ("Person", "Organization"),
        ("Organization", "Person"), ("Organization", "Organization"),
    },
    "participates_in": {
        ("Person", "Event"), ("Organization", "Event"), ("Vehicle", "Event"),
    },
    "controls": {("Organization", "Place"), ("Organization", "Organization")},
    "located_in": {("Organization", "Place"), ("Place", "Place")},
    "occurred_in": {("Event", "Place")},
    "affects": {
        ("Event", "Place"), ("Event", "Organization")
    },
    "operates": {("Organization", "Vehicle")},
    "signed": {("Person", "LegalDocument"), ("Organization", "LegalDocument")},
    "introduces": {("Person", "LegalDocument"), ("Organization", "LegalDocument")},
}


RelationType = Literal[
    "member_of", "leads", "affiliated_with", "interacts_with",
    "participates_in", "controls", "located_in", "occurred_in",
    "affects", "operates", "signed", "introduces",
]


class RelationCandidate(BaseModel):
    id: str
    source: str = Field(description="Unique ID for this relation within the bulletin.")
    type: RelationType = Field(description="Proposed relation type.")
    target: str = Field(description="ID of the target entity mention.")
    evidence: str = Field(description="Verbatim supporting text copied from the bulletin.")
    annotation_confidence: float = Field(ge=0.0, le=1.0, description="Subjective confidence in this annotation; not a calibrated probability.",)


class ValidatedRelation(RelationCandidate):
    """A relation candidate after deterministic structural validation."""

    evidence_start: int | None = Field(
        default=None,
        description="Zero-based start offset of the located evidence span, or null.",
    )
    evidence_end: int | None = Field(
        default=None,
        description="Zero-based end offset (exclusive) of the located evidence span, or null.",
    )
    evidence_recovery: str | None = Field(
        default=None,
        description=(
            "How the evidence span was located in the source text: "
            "'exact', 'whitespace_normalized', or null if not found."
        ),
    )
    is_valid: bool = Field(
        description="True iff the candidate passes structural validation."
    )
    validation_errors: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


# Human-readable relation catalogue, for prompt construction and documentation.
RELATION_CATALOGUE: dict[str, str] = {
    "governs": (
        "Person -> Organization. The person holds office over, leads or commands the "
        "organization (a minister heads a government, a general commands an army, an editor "
        "runs a newspaper). Supports the political- and military-leadership network: who "
        "was in charge of which state body or force on the eve of war."
    ),
    "member_of": (
        "Person|Organization -> Organization. The source is a member or constituent part "
        "of the target (a party member, a regiment belonging to a service, an athlete on a "
        "national squad, a subsidiary company). Captures formal affiliation and containment "
        "hierarchies."
    ),
    "negotiates_with": (
        "Person|Organization <-> Person|Organization. The two actors hold diplomatic, "
        "political or official talks (Chamberlain with Hitler, Ribbentrop with Stalin, a "
        "government with an envoy). The core edge type for the diplomacy network and for "
        "tracing multipolar negotiation in 1939."
    ),
    "signed": (
        "Person|Organization -> LegalDocument. The actor is a signatory or formal party to "
        "a treaty, pact, law or decree (the signatories of the Nazi-Soviet non-aggression "
        "pact, of the Munich agreement). Anchors treaty- and instrument-level analysis."
    ),
    "allied_with": (
        "Organization <-> Organization. The two organizations are in alliance or cooperative "
        "alignment (the Axis powers, the Allied coalition as it forms). Modelled as directed "
        "but semantically symmetric; supports alliance-bloc analysis."
    ),
    "at_war_with": (
        "Organization <-> Organization. The two organizations are in armed conflict or a "
        "state of belligerency (Germany at war with Poland). Direct it from aggressor to "
        "defender where the text supports it, otherwise leave symmetric; supports "
        "conflict-dyad and escalation analysis."
    ),
    "controls": (
        "Organization -> Place. The organization holds political, military or "
        "administrative control over the place (occupation of Poland, administration of the "
        "Free City of Danzig). Supports territorial-control and sovereignty mapping."
    ),
    "participates_in": (
        "Person|Organization|Vehicle -> Event. The source takes part in the event: an "
        "athlete or club in a sports event, a unit or force in a battle, a ship in a "
        "maritime incident. The participation backbone of the event graph."
    ),
    "occurred_in": (
        "Event -> Place. The event happened at the place (a battle at Tannenberg, a "
        "conference in Munich). Anchors events to geography for spatial analysis."
    ),
    "located_in": (
        "Organization|Place|Vehicle -> Place. The source is based at, or geographically "
        "contained in, the target place (a government seated in a capital, a stadium in a "
        "city, a region within a country, a ship's home port). Supports base-location and "
        "containment hierarchies."
    ),
    "affects": (
        "Event -> Place|Organization|Person|Vehicle. The event materially impacts the "
        "target: an armed conflict affects a country, a financial event (beurs) affects a "
        "company or market, a sinking affects a ship. Captures impact propagation across "
        "actor types, central to the political-military-economic cross-analysis."
    ),
    "operates": (
        "Organization -> Vehicle. The organization owns or operates the named vehicle (a "
        "shipping line operating a liner, an air force operating an aircraft). Supports "
        "commercial and military materiel analysis, especially for maritime traffic."
    ),
}
