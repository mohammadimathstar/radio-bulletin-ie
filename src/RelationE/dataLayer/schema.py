"""
Relation schema for the Dutch radio bulletin knowledge graph.

Entity types:
    Person, Organization, Place, Event, Vehicle, LegalDocument

The schema has three levels:
    - fine: individual relations
    - coarse: groups of fine relations
    - category: broad relation categories

The fine-grained schema is the source of truth. Coarse relations and
categories are derived from it.

Important modelling decisions:
    - no_relation is an abstention option, not a relation in this schema.
    - Place includes both countries and ordinary geographical locations.
      The schema therefore does not treat Place as a general political actor.
    - met_with and negotiated_with are restricted to Person/Organization
      pairs. Place is not allowed as either participant.
    - allied_with is restricted to Organization/Organization.
    - opposed is directional: the subject opposes the object.
    - Place is allowed in treaty-related relations because countries are
      represented as Place in the NER output. The text must establish that
      the Place is acting as a country.
    - Relation direction is semantic: (subject type, object type).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


# ---------------------------------------------------------------------
# Entity types and constants
# ---------------------------------------------------------------------

NO_RELATION = "no_relation"

PERSON = "Person"
ORG = "Organization"
PLACE = "Place"
EVENT = "Event"
VEHICLE = "Vehicle"
LEGAL = "LegalDocument"

ALL_ENTITY_TYPES = frozenset({
    PERSON,
    ORG,
    PLACE,
    EVENT,
    VEHICLE,
    LEGAL,
})


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _x(
    subjects: Iterable[str],
    objects: Iterable[str],
) -> frozenset[tuple[str, str]]:
    """Create all allowed (subject_type, object_type) combinations."""
    return frozenset(
        (subject, obj)
        for subject in subjects
        for obj in objects
    )


@dataclass(frozen=True)
class RelationDefinition:
    """
    Definition of a relation.

    allowed_types:
        Allowed (subject_type, object_type) combinations.

    symmetric:
        Whether the relation has the same meaning when subject and object
        are reversed. This is a property of the fine-grained relation.
    """

    description: str
    allowed_types: frozenset[tuple[str, str]]
    symmetric: bool = False


# ---------------------------------------------------------------------
# Fine-grained relations
# ---------------------------------------------------------------------

FINE_RELATIONS: dict[str, RelationDefinition] = {

    # ================================================================
    # Governance and authority
    # ================================================================

    "governs": RelationDefinition(
        description=(
            "The subject holds political or executive authority over "
            "the object Place. Examples include a prime minister governing "
            "a country or a mayor governing a city. Look for explicit "
            "evidence such as 'burgemeester van [Place]' or "
            "'regeert over [Place]'. A title alone is not sufficient."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PLACE,),
        ),
    ),

    "leads": RelationDefinition(
        description=(
            "The subject Person is the head, director, commander, captain "
            "or chairman of the object Organization or Vehicle. Examples "
            "include 'voorzitter van [Organization]', 'directeur van "
            "[Organization]' and 'kapitein van [Vehicle]'."
        ),
        allowed_types=_x(
            (PERSON,),
            (ORG, VEHICLE),
        ),
    ),

    "member_of": RelationDefinition(
        description=(
            "The subject Person or Organization belongs to the object "
            "Organization as a member, official, employee, soldier or "
            "delegate. Look for explicit evidence such as 'lid van', "
            "'afgevaardigde van' or 'personeel van'."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (ORG,),
        ),
    ),

    "controls": RelationDefinition(
        description=(
            "The subject Organization has operational, political or "
            "military control over the object Organization or Place. "
            "Look for explicit evidence such as 'beheerst', "
            "'onder gezag van' or 'bezette [Place]'."
        ),
        allowed_types=_x(
            (ORG,),
            (ORG, PLACE),
        ),
    ),

    "operates": RelationDefinition(
        description=(
            "The subject Organization operates or owns the object "
            "Vehicle. Look for evidence such as '[Vehicle] van de "
            "[Organization]' or '[Organization] liet [Vehicle] varen'."
        ),
        allowed_types=_x(
            (ORG,),
            (VEHICLE,),
        ),
    ),

    # ================================================================
    # Military and armed conflict
    # ================================================================

    "attacked": RelationDefinition(
        description=(
            "The subject Person, Organization or Vehicle attacked the "
            "object Person, Organization, Place or Vehicle. This relation "
            "requires evidence of an actual attack, such as 'viel aan', "
            "'beschoten' or 'gebombardeerd'. Do not use it for diplomatic "
            "opposition or criticism."
        ),
        allowed_types=_x(
            (PERSON, ORG, VEHICLE),
            (PERSON, ORG, PLACE, VEHICLE),
        ),
    ),

    "sunk_by": RelationDefinition(
        description=(
            "The subject Vehicle, usually a ship or submarine, was sunk "
            "or destroyed by the object Person, Organization or Vehicle. "
            "Look for evidence such as 'tot zinken gebracht door' or "
            "'getorpedeerd door'. The object is the agent responsible."
        ),
        allowed_types=_x(
            (VEHICLE,),
            (PERSON, ORG, VEHICLE),
        ),
    ),

    "defeated": RelationDefinition(
        description=(
            "The subject Person or Organization defeated the object "
            "Person, Organization or Place in a battle or war. Look for "
            "evidence such as 'versloeg' or 'overwinning op'. For sports "
            "results, use 'beat' instead."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PERSON, ORG, PLACE),
        ),
    ),

    "casualty_of": RelationDefinition(
        description=(
            "The subject Person died, was wounded or went missing as a "
            "result of the object Event. Look for evidence such as "
            "'kwam om bij', 'gewond bij' or 'vermist na'."
        ),
        allowed_types=_x(
            (PERSON,),
            (EVENT,),
        ),
    ),

    "deployed_in": RelationDefinition(
        description=(
            "The subject Vehicle or Organization was stationed or "
            "militarily deployed in the object Place. Look for evidence "
            "such as 'gestationeerd in' or 'troepen in'. For ordinary "
            "travel, use 'traveled_to'."
        ),
        allowed_types=_x(
            (VEHICLE, ORG),
            (PLACE,),
        ),
    ),

    # ================================================================
    # Movement
    # ================================================================

    "traveled_to": RelationDefinition(
        description=(
            "The subject Person, Organization or Vehicle travelled, "
            "sailed or flew to the object Place. Look for evidence such "
            "as 'vertrok naar', 'aangekomen te', 'reisde naar' or "
            "'uitgevaren naar'. Do not infer that an Organization "
            "travelled merely because one of its representatives did."
        ),
        allowed_types=_x(
            (PERSON, ORG, VEHICLE),
            (PLACE,),
        ),
    ),

    "departed_from": RelationDefinition(
        description=(
            "The subject Person, Organization or Vehicle left the "
            "object Place. Look for evidence such as 'vertrok uit' "
            "or 'verliet'. Do not infer that an Organization departed "
            "merely because one of its representatives did."
        ),
        allowed_types=_x(
            (PERSON, ORG, VEHICLE),
            (PLACE,),
        ),
    ),

    # ================================================================
    # Diplomacy
    # ================================================================

    "met_with": RelationDefinition(
        description=(
            "The subject Person or Organization met with the object "
            "Person or Organization, held an audience or had a direct "
            "conversation with them. Look for evidence such as "
            "'ontving', 'onderhoud met' or 'bezocht'. Both participants "
            "must be explicitly involved in the meeting. Place entities "
            "are not valid participants."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PERSON, ORG),
        ),
        symmetric=True,
    ),

    "negotiated_with": RelationDefinition(
        description=(
            "The subject Person or Organization negotiated or held "
            "discussions with the object Person or Organization about "
            "an agreement, dispute or other matter. Look for evidence "
            "such as 'onderhandelingen tusschen [A] en [B]' or "
            "'besprekingen met [B]'. Both participants must be "
            "explicitly involved in the negotiations. Place entities "
            "are not valid participants."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PERSON, ORG),
        ),
        symmetric=True,
    ),

    "allied_with": RelationDefinition(
        description=(
            "The subject Organization and object Organization are "
            "allies or have a pact of mutual support. Look for evidence "
            "such as 'bondgenoot', 'verbond tusschen' or an explicit "
            "alliance agreement. Place entities are not valid participants."
        ),
        allowed_types=_x(
            (ORG,),
            (ORG,),
        ),
        symmetric=True,
    ),

    "opposed": RelationDefinition(
        description=(
            "The subject Person or Organization opposed, protested "
            "against, criticized or rejected the object Person, "
            "Organization or Event, without necessarily using armed "
            "force. The relation is directional: the subject is the "
            "one expressing opposition. Look for evidence such as "
            "'protesteerde tegen', 'verzet zich tegen' or "
            "'afwijzing van'."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PERSON, ORG, EVENT),
        ),
    ),

    # ================================================================
    # Legal relations and treaties
    # ================================================================

    "signed": RelationDefinition(
        description=(
            "The subject Person, Organization or country signed the "
            "object LegalDocument or treaty Event. Look for evidence "
            "such as 'onderteekend door', 'getekend door' or "
            "'teekende het verdrag'. A Place subject is valid only "
            "when the text clearly refers to a country acting as "
            "a signatory, not merely to a geographical location."
        ),
        allowed_types=_x(
            (PERSON, ORG, PLACE),
            (LEGAL, EVENT),
        ),
    ),

    "ratifies": RelationDefinition(
        description=(
            "The subject Organization or country formally ratified "
            "or approved the object LegalDocument or treaty Event. "
            "Look for evidence such as 'geratificeerd door' or "
            "'goedgekeurd door'. A Place subject is valid only when "
            "the text clearly refers to a country acting as a "
            "signatory or ratifying party."
        ),
        allowed_types=_x(
            (ORG, PLACE),
            (LEGAL, EVENT),
        ),
    ),

    "issued": RelationDefinition(
        description=(
            "The subject Person or Organization issued, published "
            "or promulgated the object LegalDocument. Look for "
            "evidence such as 'uitgevaardigd door' or 'afgekondigd door'."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (LEGAL,),
        ),
    ),

    "governs_subject": RelationDefinition(
        description=(
            "The subject LegalDocument governs, regulates or applies "
            "to the object Place, Person, Organization or Event. "
            "Look for evidence such as 'betreffende', 'inzake' or "
            "'met betrekking tot'. The text must indicate legal "
            "scope or applicability, not merely mention the object."
        ),
        allowed_types=_x(
            (LEGAL,),
            (PLACE, PERSON, ORG, EVENT),
        ),
    ),

    "party_to": RelationDefinition(
        description=(
            "The subject Person, Organization or country is formally "
            "a party to the object LegalDocument or treaty Event. "
            "Do not use this for ordinary participation in an event; "
            "use 'participated_in' instead. A Place subject is valid "
            "only when the text clearly refers to a country acting "
            "as a treaty party."
        ),
        allowed_types=_x(
            (PERSON, ORG, PLACE),
            (LEGAL, EVENT),
        ),
    ),

    # ================================================================
    # Events
    # ================================================================

    "participated_in": RelationDefinition(
        description=(
            "The subject Person, Organization or Vehicle took part "
            "in the object Event. Look for evidence such as "
            "'deelnemer aan' or 'nam deel aan'. The subject may be "
            "named inside the event phrase, but participation must "
            "be explicit."
        ),
        allowed_types=_x(
            (PERSON, ORG, VEHICLE),
            (EVENT,),
        ),
    ),

    "organized": RelationDefinition(
        description=(
            "The subject Person or Organization organized, convened "
            "or arranged the object Event. Look for evidence such as "
            "'georganiseerd door' or 'bijeengeroepen door'."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (EVENT,),
        ),
    ),

    "occurred_in": RelationDefinition(
        description=(
            "The subject Event took place in the object Place. Look "
            "for evidence such as 'vond plaats in [Place]', "
            "'[Event] te [Place]' or '[Place] was het toneel van "
            "[Event]'. A dateline alone is not sufficient proof "
            "unless the reporting context establishes that the "
            "event itself took place there."
        ),
        allowed_types=_x(
            (EVENT,),
            (PLACE,),
        ),
    ),

    # ================================================================
    # Sports
    # ================================================================

    "played_for": RelationDefinition(
        description=(
            "The subject Person, as an athlete, played for the object "
            "Organization, such as a sports club or team. Look for "
            "evidence such as '[Person] speelde voor [Organization]' "
            "or '[Person] van [Club]'."
        ),
        allowed_types=_x(
            (PERSON,),
            (ORG,),
        ),
    ),

    "competed_against": RelationDefinition(
        description=(
            "The subject Person or Organization competed against the "
            "object Person or Organization, and the text does not "
            "establish who won. Look for evidence such as '[A] tegen "
            "[B]' or 'wedstrijd tusschen [A] en [B]'. Use 'beat' "
            "when the winner is explicitly stated."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PERSON, ORG),
        ),
        symmetric=True,
    ),

    "beat": RelationDefinition(
        description=(
            "The subject Person or Organization defeated the object "
            "Person or Organization in a sports match or contest. "
            "The text must say who won. Look for evidence such as "
            "'[Subject] won van [Object]', 'versloeg' or "
            "'[Subject] won met 11-2 van [Object]'."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (PERSON, ORG),
        ),
    ),

    "won": RelationDefinition(
        description=(
            "The subject Person or Organization won the object Event. "
            "Look for evidence such as '[Subject] won [Event]' or "
            "'winnaar van [Event]'."
        ),
        allowed_types=_x(
            (PERSON, ORG),
            (EVENT,),
        ),
    ),

    # ================================================================
    # Financial
    # ================================================================

    "listed_on": RelationDefinition(
        description=(
            "The subject Organization is listed or quoted on the "
            "object Organization, such as a stock exchange. The object "
            "should be an Organization, not merely a city where an "
            "exchange is located. Look for evidence such as "
            "'[Organization] op de beurs van [Exchange]'."
        ),
        allowed_types=_x(
            (ORG,),
            (ORG,),
        ),
    ),

    # ================================================================
    # Spatial relations
    # ================================================================

    "capital_of": RelationDefinition(
        description=(
            "The subject Place, referring to a city, is the capital "
            "of the object Place, referring to a country. Look for "
            "explicit evidence such as '[Place], de hoofdstad van "
            "[Place]'. Since both countries and cities are labelled "
            "Place, the text must establish the roles."
        ),
        allowed_types=_x(
            (PLACE,),
            (PLACE,),
        ),
    ),

    "located_in": RelationDefinition(
        description=(
            "The subject Person, Organization, Vehicle or Place is "
            "physically located in the object Place. For a Person, "
            "this includes temporary physical presence at a particular "
            "time, not necessarily residence or permanent assignment. "
            "For an Organization or Vehicle, it indicates its physical "
            "location. Look for explicit evidence such as 'in [Place]', "
            "'te [Place]', 'aanwezig te [Place]' or 'bevindt zich in "
            "[Place]'. A dateline alone does not establish this relation "
            "for a Person, Organization or Vehicle. Do not infer a "
            "Person's location merely from their title or nationality."
        ),
        allowed_types=_x(
            (PERSON, PLACE, ORG, VEHICLE),
            (PLACE,),
        ),
    ),

    "based_in": RelationDefinition(
        description=(
            "The subject Organization is based in, or has its home "
            "location in, the object Place. Look for evidence such "
            "as '[Organization] uit [Place]' or 'de [Organization] "
            "van [Place]'. Do not infer this from a dateline alone."
        ),
        allowed_types=_x(
            (ORG,),
            (PLACE,),
        ),
    ),

    # ================================================================
    # Reporting
    # ================================================================

    "reported": RelationDefinition(
        description=(
            "The subject Organization, such as a news agency or "
            "broadcaster, reports on the object Event. The Organization "
            "must be the source of the report, not merely the topic "
            "of the report. Look for evidence such as '[Organization] "
            "meldt', '[Organization] deelt mede' or '[Organization] "
            "verneemt'."
        ),
        allowed_types=_x(
            (ORG,),
            (EVENT,),
        ),
    ),
}


# ---------------------------------------------------------------------
# Coarse relations
# ---------------------------------------------------------------------

# coarse relation -> (category, description, fine relation members)

COARSE_GROUPS: dict[
    str,
    tuple[str, str, tuple[str, ...]]
] = {

    "authority_over": (
        "governance",
        "Subject governs, leads, controls or operates the Object.",
        ("governs", "leads", "controls", "operates"),
    ),

    "affiliated_with": (
        "governance",
        "Subject is a member, official or employee of the Object Organization.",
        ("member_of",),
    ),

    "diplomacy": (
        "governance",
        "Subject and Object meet, negotiate, ally or oppose each other.",
        ("met_with", "negotiated_with", "allied_with", "opposed"),
    ),

    "conflict_with": (
        "conflict",
        "Subject attacked, defeated or destroyed the Object in armed conflict.",
        ("attacked", "sunk_by", "defeated"),
    ),

    "military_involvement": (
        "conflict",
        "Subject is deployed in, or suffered casualties in, the Object.",
        ("deployed_in", "casualty_of"),
    ),

    "party_to_legal": (
        "legal",
        "Subject signs, ratifies, issues or is a party to the Object legal document or treaty.",
        ("signed", "ratifies", "issued", "party_to"),
    ),

    "legal_governs": (
        "legal",
        "Subject LegalDocument governs or applies to the Object.",
        ("governs_subject",),
    ),

    "participates_in_event": (
        "event",
        "Subject participates in or organizes the Object Event.",
        ("participated_in", "organized"),
    ),

    "event_at_place": (
        "event",
        "Subject Event took place at the Object Place.",
        ("occurred_in",),
    ),

    "sports_relation": (
        "sports",
        "Subject plays for, competes against, beats or wins the Object.",
        ("played_for", "competed_against", "beat", "won"),
    ),

    "corporate_relation": (
        "financial",
        "Subject Organization is listed on the Object Organization.",
        ("listed_on",),
    ),

    "movement": (
        "spatial_media",
        "Subject travelled to or left the Object Place.",
        ("traveled_to", "departed_from"),
    ),

    "located_in": (
        "spatial_media",
        "Subject is located in, based in, or is the capital of the Object Place.",
        ("located_in", "capital_of", "based_in"),
    ),

    "reported": (
        "spatial_media",
        "Subject Organization reports on the Object Event.",
        ("reported",),
    ),
}


# ---------------------------------------------------------------------
# Category descriptions
# ---------------------------------------------------------------------

CATEGORY_DESCRIPTIONS = {
    "governance": (
        "authority, membership and diplomacy between persons "
        "and organizations"
    ),
    "conflict": (
        "armed conflict, deployment and casualties"
    ),
    "legal": (
        "treaties, laws and the parties to them"
    ),
    "event": (
        "participation in events and where events take place"
    ),
    "sports": (
        "sports teams, matches and results"
    ),
    "financial": (
        "listing on exchanges"
    ),
    "spatial_media": (
        "location, movement and news reporting"
    ),
}


# ---------------------------------------------------------------------
# Derive coarse and category schemas
# ---------------------------------------------------------------------

FINE_TO_COARSE = {
    fine: coarse
    for coarse, (_, _, members) in COARSE_GROUPS.items()
    for fine in members
}

COARSE_TO_CATEGORY = {
    coarse: category
    for coarse, (category, _, _) in COARSE_GROUPS.items()
}


def _derive(
    groups: Mapping[str, tuple[str, ...]],
    descriptions: Mapping[str, str],
    parent: Mapping[str, RelationDefinition],
) -> dict[str, RelationDefinition]:
    """
    Derive a higher-level schema from its child relations.

    The allowed type pairs are the union of the child relations.

    A derived relation is marked symmetric only when all its child
    relations are symmetric. Therefore, a mixed group such as diplomacy
    is not symmetric at the coarse level. Fine-grained symmetry must be
    used when determining semantic direction.
    """
    result = {}

    for name, members in groups.items():
        result[name] = RelationDefinition(
            description=descriptions[name],
            allowed_types=frozenset().union(
                *(parent[member].allowed_types for member in members)
            ),
            symmetric=all(
                parent[member].symmetric
                for member in members
            ),
        )

    return result


RELATION_SCHEMA_FINE = FINE_RELATIONS

RELATION_SCHEMA_COARSE = _derive(
    groups={
        coarse: definition[2]
        for coarse, definition in COARSE_GROUPS.items()
    },
    descriptions={
        coarse: definition[1]
        for coarse, definition in COARSE_GROUPS.items()
    },
    parent=FINE_RELATIONS,
)

_category_members: dict[str, list[str]] = {}

for coarse, category in COARSE_TO_CATEGORY.items():
    _category_members.setdefault(category, []).append(coarse)

RELATION_SCHEMA_CATEGORY = _derive(
    groups={
        category: tuple(members)
        for category, members in _category_members.items()
    },
    descriptions=CATEGORY_DESCRIPTIONS,
    parent=RELATION_SCHEMA_COARSE,
)

SCHEMAS = {
    "fine": RELATION_SCHEMA_FINE,
    "coarse": RELATION_SCHEMA_COARSE,
    "category": RELATION_SCHEMA_CATEGORY,
}


# ---------------------------------------------------------------------
# Public schema functions
# ---------------------------------------------------------------------

def get_schema(
    level: str = "fine",
) -> dict[str, RelationDefinition]:
    """Return the schema at the requested level."""
    if level not in SCHEMAS:
        raise ValueError(
            f"level must be one of {sorted(SCHEMAS)}, "
            f"not {level!r}"
        )

    return SCHEMAS[level]


def get_allowed_relations(
    type_a: str,
    type_b: str,
    schema: Mapping[str, RelationDefinition],
) -> set[str]:
    """
    Return relations that can hold FROM type_a TO type_b.

    The order is semantic: type_a is the subject and type_b is the object.
    """
    return {
        relation
        for relation, definition in schema.items()
        if (type_a, type_b) in definition.allowed_types
    }


def compatible_relations(
    type1: str,
    type2: str,
    schema: Mapping[str, RelationDefinition],
) -> list[str]:
    """
    Return relations compatible with two entity types in either order.

    The textual order of mentions does not necessarily correspond to
    the semantic subject/object order.

    no_relation is not included; it should be added separately by the
    relation-extraction step.
    """
    return [
        relation
        for relation, definition in schema.items()
        if (
            (type1, type2) in definition.allowed_types
            or (type2, type1) in definition.allowed_types
        )
    ]


def is_symmetric(
    relation: str,
    schema: Mapping[str, RelationDefinition],
) -> bool:
    """Return whether a relation is symmetric."""
    if relation not in schema:
        return False

    return schema[relation].symmetric


def project_fine_to_coarse(fine: str) -> str:
    """Project a fine relation to its coarse relation."""
    return FINE_TO_COARSE.get(fine, NO_RELATION)


def project_fine_to_category(fine: str) -> str:
    """Project a fine relation to its broad category."""
    coarse = project_fine_to_coarse(fine)

    return COARSE_TO_CATEGORY.get(
        coarse,
        NO_RELATION,
    )


def check_entity_types(
    types_in_data: Mapping[str, int],
    schema: Mapping[str, RelationDefinition] | None = None,
) -> dict:
    """
    Compare NER entity types with the types used by the schema.

    Returns:
        unknown_to_schema:
            Types present in the data but not in the schema.

        unused_by_data:
            Types in the schema but absent from the data.

        unreachable_relations:
            Relations for which no allowed type pair is present in data.
    """
    schema = schema or FINE_RELATIONS

    types_in_schema = {
        entity_type
        for definition in schema.values()
        for pair in definition.allowed_types
        for entity_type in pair
    }

    present_types = set(types_in_data)

    unreachable = sorted(
        relation
        for relation, definition in schema.items()
        if not any(
            subject in present_types and obj in present_types
            for subject, obj in definition.allowed_types
        )
    )

    return {
        "unknown_to_schema": sorted(
            present_types - types_in_schema
        ),
        "unused_by_data": sorted(
            types_in_schema - present_types
        ),
        "unreachable_relations": unreachable,
    }


# ---------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------

def validate_schema() -> list[str]:
    """
    Validate the consistency of the relation schema.

    Returns an empty list when no problems are found.
    """
    problems = []

    # Validate fine-grained relations.
    for relation, definition in FINE_RELATIONS.items():

        if relation == NO_RELATION:
            problems.append(
                "no_relation must not be a relation of the schema"
            )

        if not definition.allowed_types:
            problems.append(
                f"{relation}: no allowed type pairs"
            )

        for subject_type, object_type in definition.allowed_types:
            if subject_type not in ALL_ENTITY_TYPES:
                problems.append(
                    f"{relation}: unknown subject type "
                    f"{subject_type}"
                )

            if object_type not in ALL_ENTITY_TYPES:
                problems.append(
                    f"{relation}: unknown object type "
                    f"{object_type}"
                )

        if definition.symmetric:
            for subject_type, object_type in definition.allowed_types:
                if (
                    object_type,
                    subject_type,
                ) not in definition.allowed_types:
                    problems.append(
                        f"{relation}: symmetric relation is not "
                        "closed under swapping the types"
                    )

        if relation not in FINE_TO_COARSE:
            problems.append(
                f"{relation}: has no coarse relation"
            )

    # Every fine relation must belong to exactly one coarse group.
    for relation in FINE_RELATIONS:
        group_count = sum(
            relation in members
            for _, _, members in COARSE_GROUPS.values()
        )

        if group_count == 0:
            problems.append(
                f"{relation}: does not belong to a coarse group"
            )
        elif group_count > 1:
            problems.append(
                f"{relation}: belongs to more than one coarse group"
            )

    # Every coarse group must reference existing fine relations.
    for coarse, (_, _, members) in COARSE_GROUPS.items():
        for member in members:
            if member not in FINE_RELATIONS:
                problems.append(
                    f"{coarse}: unknown fine relation {member}"
                )

    # Every coarse group must reference a known category.
    for coarse, (category, _, _) in COARSE_GROUPS.items():
        if category not in CATEGORY_DESCRIPTIONS:
            problems.append(
                f"{coarse}: unknown category {category}"
            )

    return problems


# ---------------------------------------------------------------------
# Optional command-line validation
# ---------------------------------------------------------------------

if __name__ == "__main__":
    errors = validate_schema()

    if errors:
        print("Schema validation failed:")
        for error in errors:
            print(f" - {error}")
    else:
        print("Schema validation passed.")

    print(f"Fine relations: {len(RELATION_SCHEMA_FINE)}")
    print(f"Coarse relations: {len(RELATION_SCHEMA_COARSE)}")
    print(f"Categories: {len(RELATION_SCHEMA_CATEGORY)}")