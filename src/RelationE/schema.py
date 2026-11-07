from dataclasses import dataclass


@dataclass(frozen=True)
class RelationDefinition:
    description: str
    allowed_types: frozenset[tuple[str, str]]
    symmetric: bool = False


RELATION_SCHEMA = {
    "member_of": RelationDefinition(
        description="A person or organization belongs to an organization.",
        allowed_types=frozenset({
            ("Person", "Organization"),
            ("Organization", "Organization"),
        }),
    ),

    "leads": RelationDefinition(
        description="A person or organization leads an organization.",
        allowed_types=frozenset({
            ("Person", "Organization"),
            ("Organization", "Organization"),
        }),
    ),

    "interacts_with": RelationDefinition(
        description=(
            "Two persons or organizations directly interact, "
            "communicate, meet, negotiate, or cooperate."
        ),
        allowed_types=frozenset({
            ("Person", "Person"),
            ("Person", "Organization"),
            ("Organization", "Organization"),
        }),
        symmetric=True,
    ),

    "participates_in": RelationDefinition(
        description="An entity takes part in an event.",
        allowed_types=frozenset({
            ("Person", "Event"),
            ("Organization", "Event"),
            ("Vehicle", "Event"),
        }),
    ),

    "controls": RelationDefinition(
        description="An organization exercises control over a place or organization.",
        allowed_types=frozenset({
            ("Organization", "Place"),
            ("Organization", "Organization"),
        }),
    ),

    "located_in": RelationDefinition(
        description="An organization or place is geographically located in a place.",
        allowed_types=frozenset({
            ("Organization", "Place"),
            ("Place", "Place"),
        }),
    ),

    "occurred_in": RelationDefinition(
        description="An event takes place in a particular location.",
        allowed_types=frozenset({
            ("Event", "Place"),
        }),
    ),

    "affects": RelationDefinition(
        description="An event has an impact on a place or organization.",
        allowed_types=frozenset({
            ("Event", "Place"),
            ("Event", "Organization"),
        }),
    ),

    "operates": RelationDefinition(
        description="An organization operates or manages a vehicle.",
        allowed_types=frozenset({
            ("Organization", "Vehicle"),
        }),
    ),

    "signed": RelationDefinition(
        description="A person or organization formally signs a legal document.",
        allowed_types=frozenset({
            ("Person", "LegalDocument"),
            ("Organization", "LegalDocument"),
        }),
    ),
}


NO_RELATION = "no_relation"