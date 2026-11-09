from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RelationDefinition:
    description: str
    allowed_types: frozenset[tuple[str, str]]
    symmetric: bool = False


# ============================================================
# FINE-GRAINED RELATIONS (29 + no_relation)
# ============================================================

RELATION_SCHEMA_FINE: dict[str, RelationDefinition] = {
    # === Governance & Authority ===
    "governs": RelationDefinition(
        description="Subject holds political or executive office over a Place (e.g., a Prime Minister over a country, a mayor over a city). Look for titles like 'burgemeester van [Place]', 'president van [Place]'.",
        allowed_types=frozenset({
            ("Person", "Place"),
            ("Organization", "Place"),
        }),
    ),
    "leads": RelationDefinition(
        description="Subject is the head, director, commander, or chairman of an Organization. Look for 'chef van [Org]', 'voorzitter van [Org]', 'directeur van [Org]'.",
        allowed_types=frozenset({
            ("Person", "Organization"),
            ("Organization", "Organization"),
        }),
    ),
    "member_of": RelationDefinition(
        description="Subject belongs to an Organization as a member, official, or affiliate. Look for 'lid van [Org]', 'afgevaardigde van [Org]'.",
        allowed_types=frozenset({
            ("Person", "Organization"),
            ("Organization", "Organization"),
        }),
    ),
    "employs": RelationDefinition(
        description="Subject Organization employs the Object Person as staff, official, or soldier. Look for 'werknemers van [Org]', 'personeel van [Org]'.",
        allowed_types=frozenset({
            ("Organization", "Person"),
        }),
    ),
    "controls": RelationDefinition(
        description="Subject Organization has operational, political, or military control over another Organization or Place. Look for 'beheerst [Place/Org]', 'onder gezag van [Org]', 'bezette [Place]'.",
        allowed_types=frozenset({
            ("Organization", "Organization"),
            ("Organization", "Place"),
        }),
    ),
    # === Military & Conflict ===
    "commanded_by": RelationDefinition(
        description="Subject (a military Organization or Vehicle) is under the command of the Object Person. Look for 'onder leiding van [Person]', 'onder bevel van [Person]'.",
        allowed_types=frozenset({
            ("Organization", "Person"),
            ("Vehicle", "Person"),
        }),
    ),
    "attacked": RelationDefinition(
        description="Subject (Event, military Organization, or Vehicle) attacked the Object. Look for 'viel [Object] aan', 'beschoten [Object]', 'gebombardeerd [Object]'.",
        allowed_types=frozenset({
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"), ("Event", "Vehicle"),
            ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"), ("Organization", "Vehicle"),
            ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"), ("Vehicle", "Vehicle"),
        }),
    ),
    "sunk_by": RelationDefinition(
        description="Subject Vehicle (Ship or Submarine) was destroyed or sunk by the Object. Look for 'tot zinken gebracht door [Object]', 'getorpedeerd door [Object]'.",
        allowed_types=frozenset({
            ("Vehicle", "Event"), ("Vehicle", "Organization"), ("Vehicle", "Vehicle"), ("Vehicle", "Person"),
        }),
    ),
    "defeated": RelationDefinition(
        description="Subject (Event, Organization, or Person) defeated the Object in battle. Look for 'versloeg [Object]', 'overwinning op [Object]'.",
        allowed_types=frozenset({
            ("Event", "Organization"), ("Event", "Person"), ("Event", "Place"),
            ("Organization", "Organization"), ("Organization", "Person"), ("Organization", "Place"),
            ("Person", "Organization"), ("Person", "Person"), ("Person", "Place"),
        }),
    ),
    "casualty_of": RelationDefinition(
        description="Subject Person died, was wounded, or was missing as a result of the Object Event. Look for 'kwam om bij [Event]', 'gewond bij [Event]'.",
        allowed_types=frozenset({
            ("Person", "Event"),
        }),
    ),
    "operates": RelationDefinition(
        description="Subject Organization operates or owns the Object Vehicle. Look for '[Org] liet [Vehicle] varen/vliegen', '[Vehicle] van [Org]'.",
        allowed_types=frozenset({
            ("Organization", "Vehicle"),
        }),
    ),
    "deployed_in": RelationDefinition(
        description="Subject (Vehicle or Organization) is stationed, operating, or deployed in the Object Place. Look for 'gestationeerd in [Place]', 'uitgevaren naar [Place]'.",
        allowed_types=frozenset({
            ("Vehicle", "Place"),
            ("Organization", "Place"),
        }),
    ),
    # === Diplomacy & Legal ===
    "signed": RelationDefinition(
        description="Subject (Person or Organization) signed the Object LegalDocument. Look for 'onderteekend door [Person/Org]', 'getekend door [Person/Org]'.",
        allowed_types=frozenset({
            ("Person", "LegalDocument"),
            ("Organization", "LegalDocument"),
        }),
    ),
    "ratifies": RelationDefinition(
        description="Subject (Place = country, or Organization) ratifies or formally approves the Object LegalDocument. Look for 'geratificeerd door [Place/Org]', 'goedgekeurd door [Place/Org]'.",
        allowed_types=frozenset({
            ("Place", "LegalDocument"),
            ("Organization", "LegalDocument"),
        }),
    ),
    "issued": RelationDefinition(
        description="Subject (Person or Organization) issued or promulgated the Object LegalDocument. Look for 'uitgevaardigd door [Person/Org]', 'afgekondigd door [Person/Org]'.",
        allowed_types=frozenset({
            ("Person", "LegalDocument"),
            ("Organization", "LegalDocument"),
        }),
    ),
    "governs_subject": RelationDefinition(
        description="Subject LegalDocument governs, regulates, or applies to the Object. Look for 'betreffende [Object]', 'inzake [Object]', 'met betrekking tot [Object]'.",
        allowed_types=frozenset({
            ("LegalDocument", "Place"), ("LegalDocument", "Person"),
            ("LegalDocument", "Organization"), ("LegalDocument", "Event"),
        }),
    ),
    "party_to": RelationDefinition(
        description="Subject (Person, Organization, or Place) is a party, signatory, or participant to the Object LegalDocument. Look for '[Person/Org/Place] was vertegenwoordigd bij [LegalDoc]'.",
        allowed_types=frozenset({
            ("Person", "LegalDocument"),
            ("Organization", "LegalDocument"),
            ("Place", "LegalDocument"),
        }),
    ),
    # === Events & Participation ===
    "participated_in": RelationDefinition(
        description="Subject (Person, Organization, or Vehicle) took part in the Object Event. Look for 'deelnemer aan [Event]', 'nam deel aan [Event]'.",
        allowed_types=frozenset({
            ("Person", "Event"),
            ("Organization", "Event"),
            ("Vehicle", "Event"),
        }),
    ),
    "organized": RelationDefinition(
        description="Subject (Person or Organization) organized, convened, or arranged the Object Event. Look for 'georganiseerd door [Person/Org]', 'bijeengeroepen door [Person/Org]'.",
        allowed_types=frozenset({
            ("Person", "Event"),
            ("Organization", "Event"),
        }),
    ),
    "hosted": RelationDefinition(
        description="Subject Place hosted or was the venue for the Object Event. Look for '[Event] in [Place]', '[Place] was het toneel van [Event]'.",
        allowed_types=frozenset({
            ("Place", "Event"),
        }),
    ),
    "occurred_in": RelationDefinition(
        description="Subject Event took place at or in the Object Place. Look for 'gebeurde in [Place]', 'vond plaats in [Place]', 'te [Place]'.",
        allowed_types=frozenset({
            ("Event", "Place"),
        }),
    ),
    "mentions": RelationDefinition(
        description="Subject (Event, LegalDocument, or Organization) explicitly mentions or references the Object, but no more specific relation holds. Use only when no other relation applies.",
        allowed_types=frozenset({
            ("Event", "Person"), ("Event", "Place"), ("Event", "Organization"), ("Event", "Vehicle"),
            ("LegalDocument", "Person"), ("LegalDocument", "Place"), ("LegalDocument", "Organization"), ("LegalDocument", "Vehicle"),
            ("Organization", "Person"), ("Organization", "Place"), ("Organization", "Organization"), ("Organization", "Vehicle"),
        }),
    ),
    # === Sports & Competition ===
    "played_for": RelationDefinition(
        description="Subject Person (athlete) played for the Object Organization. Look for '[Person] van [Org]', '[Person] speelde voor [Org]'.",
        allowed_types=frozenset({
            ("Person", "Organization"),
        }),
    ),
    "competed_against": RelationDefinition(
        description="Subject (Person or Organization) competed against the Object (Person or Organization). Look for '[Subject] vs [Object]', '[Subject] tegen [Object]'.",
        allowed_types=frozenset({
            ("Person", "Person"), ("Person", "Organization"),
            ("Organization", "Person"), ("Organization", "Organization"),
        }),
        symmetric=True,
    ),
    "won": RelationDefinition(
        description="Subject (Person or Organization) won the Object Event. Look for '[Subject] won [Event]', 'overwinning voor [Subject]'.",
        allowed_types=frozenset({
            ("Person", "Event"),
            ("Organization", "Event"),
        }),
    ),
    # === Financial & Commercial ===
    "listed_on": RelationDefinition(
        description="Subject Organization is listed on the Object (stock exchange). Look for '[Org] op de beurs van [Place]', '[Org] noteerde op [Place/Org]'.",
        allowed_types=frozenset({
            ("Organization", "Place"),
            ("Organization", "Organization"),
        }),
    ),
    # === Spatial & Media ===
    "capital_of": RelationDefinition(
        description="Subject Place (a settlement) is the capital of the Object Place (a country). Look for '[Place], de hoofdstad van [Place]'.",
        allowed_types=frozenset({
            ("Place", "Place"),
        }),
    ),
    "located_in": RelationDefinition(
        description="Subject (Place, Organization, or Vehicle) is physically located in the Object Place. Look for 'in [Place]', 'te [Place]', 'gelegen in [Place]'.",
        allowed_types=frozenset({
            ("Place", "Place"),
            ("Organization", "Place"),
            ("Vehicle", "Place"),
        }),
    ),
    "reported": RelationDefinition(
        description="Subject Organization (media outlet or broadcaster) reports on the Object Event. Look for '[Org] meldt', '[Org] deelt mede', '[Org] verneemt'.",
        allowed_types=frozenset({
            ("Organization", "Event"),
        }),
    ),
    # === Abstention ===
    "no_relation": RelationDefinition(
        description="No specific relation holds between the two entities. Use when entities co-occur but no defined relation applies.",
        allowed_types=frozenset({
            ("Person", "Person"), ("Person", "Organization"), ("Person", "Place"),
            ("Person", "Event"), ("Person", "Vehicle"), ("Person", "LegalDocument"),
            ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"),
            ("Organization", "Event"), ("Organization", "Vehicle"), ("Organization", "LegalDocument"),
            ("Place", "Person"), ("Place", "Organization"), ("Place", "Place"),
            ("Place", "Event"), ("Place", "Vehicle"), ("Place", "LegalDocument"),
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"),
            ("Event", "Event"), ("Event", "Vehicle"), ("Event", "LegalDocument"),
            ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"),
            ("Vehicle", "Event"), ("Vehicle", "Vehicle"), ("Vehicle", "LegalDocument"),
            ("LegalDocument", "Person"), ("LegalDocument", "Organization"), ("LegalDocument", "Place"),
            ("LegalDocument", "Event"), ("LegalDocument", "Vehicle"), ("LegalDocument", "LegalDocument"),
        }),
    ),
}


# ============================================================
# COARSE-GRAINED RELATIONS (13 + no_relation)
# ============================================================

RELATION_SCHEMA_COARSE: dict[str, RelationDefinition] = {
    # C1: authority_over (governs, leads, controls, operates, employs)
    "authority_over": RelationDefinition(
        description="Subject governs, leads, controls, operates, or employs the Object. The Subject holds power, authority, or ownership over the Object.",
        allowed_types=frozenset({
            ("Person", "Place"), ("Organization", "Place"),
            ("Person", "Organization"), ("Organization", "Organization"),
            ("Organization", "Vehicle"), ("Organization", "Person"),
        }),
    ),
    # C2: affiliated_with (member_of, commanded_by)
    "affiliated_with": RelationDefinition(
        description="Subject is a member of, or under the command of, the Object. The Subject is subordinate to or belongs to the Object Organization.",
        allowed_types=frozenset({
            ("Person", "Organization"), ("Organization", "Organization"),
            ("Organization", "Person"), ("Vehicle", "Person"),
        }),
    ),
    # C3: conflict_with (attacked, sunk_by, defeated)
    "conflict_with": RelationDefinition(
        description="Subject attacked, defeated, or destroyed the Object in a military or armed-conflict context. Look for military aggression, battles, sinking, or surrender.",
        allowed_types=frozenset({
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"), ("Event", "Vehicle"),
            ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"), ("Organization", "Vehicle"),
            ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"), ("Vehicle", "Vehicle"),
            ("Person", "Organization"), ("Person", "Person"), ("Person", "Place"),
        }),
    ),
    # C4: military_involvement (deployed_in, casualty_of)
    "military_involvement": RelationDefinition(
        description="Subject is deployed in, or suffered casualties in, the Object (an Event or Place). Look for troop deployments, stationing, or persons killed/wounded.",
        allowed_types=frozenset({
            ("Vehicle", "Place"), ("Organization", "Place"), ("Person", "Event"),
        }),
    ),
    # C5: party_to_legal (signed, ratifies, issued, party_to)
    "party_to_legal": RelationDefinition(
        description="Subject signs, ratifies, issues, or is otherwise a party to the Object LegalDocument. Look for diplomatic or legal acts involving treaties, laws, decrees.",
        allowed_types=frozenset({
            ("Person", "LegalDocument"), ("Organization", "LegalDocument"), ("Place", "LegalDocument"),
        }),
    ),
    # C6: legal_governs (governs_subject)
    "legal_governs": RelationDefinition(
        description="Subject LegalDocument governs, regulates, or applies to the Object. The LegalDocument is about, or applies to, the Object entity.",
        allowed_types=frozenset({
            ("LegalDocument", "Place"), ("LegalDocument", "Person"),
            ("LegalDocument", "Organization"), ("LegalDocument", "Event"),
        }),
    ),
    # C7: participates_in_event (participated_in, organized)
    "participates_in_event": RelationDefinition(
        description="Subject participates in or organizes the Object Event. The Subject is actively involved in making the Event happen or taking part in it.",
        allowed_types=frozenset({
            ("Person", "Event"), ("Organization", "Event"), ("Vehicle", "Event"),
        }),
    ),
    # C8: event_at_place (occurred_in, hosted — direction-normalized)
    "event_at_place": RelationDefinition(
        description="Subject Event took place at, or was hosted by, the Object Place. Direction-normalized: works in both (Event, Place) and (Place, Event) directions.",
        allowed_types=frozenset({
            ("Event", "Place"), ("Place", "Event"),
        }),
        symmetric=True,
    ),
    # C9: mentions
    "mentions": RelationDefinition(
        description="Subject mentions or references the Object, with no more specific relation holding. Use only when no governance, conflict, legal, or participation relation applies.",
        allowed_types=frozenset({
            ("Event", "Person"), ("Event", "Place"), ("Event", "Organization"), ("Event", "Vehicle"),
            ("LegalDocument", "Person"), ("LegalDocument", "Place"), ("LegalDocument", "Organization"), ("LegalDocument", "Vehicle"),
            ("Organization", "Person"), ("Organization", "Place"), ("Organization", "Organization"), ("Organization", "Vehicle"),
        }),
    ),
    # C10: sports_relation (played_for, competed_against, won)
    "sports_relation": RelationDefinition(
        description="Subject (Person or Organization) plays for, competes against, or won the Object. Look for athletic competition, team membership, or match results.",
        allowed_types=frozenset({
            ("Person", "Organization"), ("Person", "Person"),
            ("Organization", "Person"), ("Organization", "Organization"),
            ("Person", "Event"), ("Organization", "Event"),
        }),
    ),
    # C11: corporate_relation (listed_on)
    "corporate_relation": RelationDefinition(
        description="Subject Organization is corporately tied to the Object: listed on a stock exchange or headquartered there.",
        allowed_types=frozenset({
            ("Organization", "Place"), ("Organization", "Organization"),
        }),
    ),
    # C12: located_in (located_in, capital_of)
    "located_in": RelationDefinition(
        description="Subject is physically located in, or is the capital of, the Object Place. Captures spatial containment and capital-city relations.",
        allowed_types=frozenset({
            ("Place", "Place"), ("Organization", "Place"), ("Vehicle", "Place"),
        }),
    ),
    # C13: reported
    "reported": RelationDefinition(
        description="Subject Organization (media outlet or broadcaster) reports on the Object Event. Look for '[Org] meldt', '[Org] deelt mede'.",
        allowed_types=frozenset({
            ("Organization", "Event"),
        }),
    ),
    # Abstention
    "no_relation": RelationDefinition(
        description="No specific relation holds between the two entities. Use when entities co-occur but no defined relation applies.",
        allowed_types=frozenset({
            ("Person", "Person"), ("Person", "Organization"), ("Person", "Place"),
            ("Person", "Event"), ("Person", "Vehicle"), ("Person", "LegalDocument"),
            ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"),
            ("Organization", "Event"), ("Organization", "Vehicle"), ("Organization", "LegalDocument"),
            ("Place", "Person"), ("Place", "Organization"), ("Place", "Place"),
            ("Place", "Event"), ("Place", "Vehicle"), ("Place", "LegalDocument"),
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"),
            ("Event", "Event"), ("Event", "Vehicle"), ("Event", "LegalDocument"),
            ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"),
            ("Vehicle", "Event"), ("Vehicle", "Vehicle"), ("Vehicle", "LegalDocument"),
            ("LegalDocument", "Person"), ("LegalDocument", "Organization"), ("LegalDocument", "Place"),
            ("LegalDocument", "Event"), ("LegalDocument", "Vehicle"), ("LegalDocument", "LegalDocument"),
        }),
    ),
}


# ============================================================
# FINE → COARSE MAPPING
# ============================================================

FINE_TO_COARSE: dict[str, str] = {
    "governs": "authority_over",
    "leads": "authority_over",
    "controls": "authority_over",
    "operates": "authority_over",
    "employs": "authority_over",
    "member_of": "affiliated_with",
    "commanded_by": "affiliated_with",
    "attacked": "conflict_with",
    "sunk_by": "conflict_with",
    "defeated": "conflict_with",
    "deployed_in": "military_involvement",
    "casualty_of": "military_involvement",
    "signed": "party_to_legal",
    "ratifies": "party_to_legal",
    "issued": "party_to_legal",
    "party_to": "party_to_legal",
    "governs_subject": "legal_governs",
    "participated_in": "participates_in_event",
    "organized": "participates_in_event",
    "occurred_in": "event_at_place",
    "hosted": "event_at_place",
    "mentions": "mentions",
    "played_for": "sports_relation",
    "competed_against": "sports_relation",
    "won": "sports_relation",
    "listed_on": "corporate_relation",
    "capital_of": "located_in",
    "located_in": "located_in",
    "reported": "reported",
    "no_relation": "no_relation",
}


# ============================================================
# CATEGORY-LEVEL (7 labels, for smallest models)
# ============================================================

COARSE_TO_CATEGORY: dict[str, str] = {
    "authority_over": "governance",
    "affiliated_with": "governance",
    "conflict_with": "conflict",
    "military_involvement": "conflict",
    "party_to_legal": "legal",
    "legal_governs": "legal",
    "participates_in_event": "event",
    "event_at_place": "event",
    "mentions": "event",
    "sports_relation": "sports",
    "corporate_relation": "financial",
    "located_in": "spatial_media",
    "reported": "spatial_media",
    "no_relation": "no_relation",
}

RELATION_SCHEMA_CATEGORY: dict[str, RelationDefinition] = {
    "governance": RelationDefinition(
        description="Subject governs, leads, controls, is a member of, or is affiliated with the Object in a political/organizational context.",
        allowed_types=frozenset({
            ("Person", "Place"), ("Organization", "Place"),
            ("Person", "Organization"), ("Organization", "Organization"),
            ("Organization", "Vehicle"), ("Organization", "Person"),
            ("Vehicle", "Person"),
        }),
    ),
    "conflict": RelationDefinition(
        description="Subject attacked, defeated, destroyed, or was deployed/casualty in the Object in a military context.",
        allowed_types=frozenset({
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"), ("Event", "Vehicle"),
            ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"), ("Organization", "Vehicle"),
            ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"), ("Vehicle", "Vehicle"),
            ("Person", "Organization"), ("Person", "Person"), ("Person", "Place"),
            ("Person", "Event"),
        }),
    ),
    "legal": RelationDefinition(
        description="Subject is party to, signs, ratifies, or issues a LegalDocument, or a LegalDocument governs the Object.",
        allowed_types=frozenset({
            ("Person", "LegalDocument"), ("Organization", "LegalDocument"), ("Place", "LegalDocument"),
            ("LegalDocument", "Place"), ("LegalDocument", "Person"),
            ("LegalDocument", "Organization"), ("LegalDocument", "Event"),
        }),
    ),
    "event": RelationDefinition(
        description="Subject participates in, organizes, or mentions the Object Event, or an Event occurred at / was hosted by a Place.",
        allowed_types=frozenset({
            ("Person", "Event"), ("Organization", "Event"), ("Vehicle", "Event"),
            ("Event", "Place"), ("Place", "Event"),
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Vehicle"),
            ("LegalDocument", "Person"), ("LegalDocument", "Place"), ("LegalDocument", "Organization"), ("LegalDocument", "Vehicle"),
            ("Organization", "Person"), ("Organization", "Place"), ("Organization", "Organization"), ("Organization", "Vehicle"),
        }),
    ),
    "sports": RelationDefinition(
        description="Subject plays for, competes against, or won the Object in an athletic context.",
        allowed_types=frozenset({
            ("Person", "Organization"), ("Person", "Person"),
            ("Organization", "Person"), ("Organization", "Organization"),
            ("Person", "Event"), ("Organization", "Event"),
        }),
    ),
    "financial": RelationDefinition(
        description="Subject Organization is corporately tied to the Object: listed on a stock exchange.",
        allowed_types=frozenset({
            ("Organization", "Place"), ("Organization", "Organization"),
        }),
    ),
    "spatial_media": RelationDefinition(
        description="Subject is physically located in the Object Place, is the capital of it, or reports on the Object Event.",
        allowed_types=frozenset({
            ("Place", "Place"), ("Organization", "Place"), ("Vehicle", "Place"),
            ("Organization", "Event"),
        }),
    ),
    "no_relation": RelationDefinition(
        description="No specific relation holds between the two entities.",
        allowed_types=frozenset({
            ("Person", "Person"), ("Person", "Organization"), ("Person", "Place"),
            ("Person", "Event"), ("Person", "Vehicle"), ("Person", "LegalDocument"),
            ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"),
            ("Organization", "Event"), ("Organization", "Vehicle"), ("Organization", "LegalDocument"),
            ("Place", "Person"), ("Place", "Organization"), ("Place", "Place"),
            ("Place", "Event"), ("Place", "Vehicle"), ("Place", "LegalDocument"),
            ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"),
            ("Event", "Event"), ("Event", "Vehicle"), ("Event", "LegalDocument"),
            ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"),
            ("Vehicle", "Event"), ("Vehicle", "Vehicle"), ("Vehicle", "LegalDocument"),
            ("LegalDocument", "Person"), ("LegalDocument", "Organization"), ("LegalDocument", "Place"),
            ("LegalDocument", "Event"), ("LegalDocument", "Vehicle"), ("LegalDocument", "LegalDocument"),
        }),
    ),
}


# ============================================================
# LITERAL TYPES
# ============================================================

FineRelationType = Literal[
    "governs",
    "leads",
    "member_of",
    "employs",
    "controls",
    "commanded_by",
    "attacked",
    "sunk_by",
    "defeated",
    "casualty_of",
    "operates",
    "deployed_in",
    "signed",
    "ratifies",
    "issued",
    "governs_subject",
    "party_to",
    "participated_in",
    "organized",
    "hosted",
    "occurred_in",
    "mentions",
    "played_for",
    "competed_against",
    "won",
    "listed_on",
    "capital_of",
    "located_in",
    "reported",
    "no_relation",
]

CoarseRelationType = Literal[
    "authority_over",
    "affiliated_with",
    "conflict_with",
    "military_involvement",
    "party_to_legal",
    "legal_governs",
    "participates_in_event",
    "event_at_place",
    "mentions",
    "sports_relation",
    "corporate_relation",
    "located_in",
    "reported",
    "no_relation",
]

CategoryRelationType = Literal[
    "governance",
    "conflict",
    "legal",
    "event",
    "sports",
    "financial",
    "spatial_media",
    "no_relation",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

ALL_ENTITY_TYPES = frozenset({
    "Person", "Organization", "Place", "Event", "Vehicle", "LegalDocument"
})


def get_allowed_relations(
    type_a: str,
    type_b: str,
    schema: dict[str, RelationDefinition],
) -> set[str]:
    """Return all relation labels whose allowed_types include (type_a, type_b)."""
    return {
        rel for rel, definition in schema.items()
        if (type_a, type_b) in definition.allowed_types
    }


def get_all_allowed_pairs(schema: dict[str, RelationDefinition]) -> set[tuple[str, str]]:
    """Return the union of all allowed type pairs across all relations in the schema."""
    pairs = set()
    for definition in schema.values():
        pairs.update(definition.allowed_types)
    return pairs


def is_symmetric(rel: str, schema: dict[str, RelationDefinition]) -> bool:
    """Check whether a relation is marked symmetric in the schema."""
    if rel in schema:
        return schema[rel].symmetric
    return False


def project_fine_to_coarse(fine_rel: str) -> str:
    """Project a fine-grained relation to its coarse-grained parent."""
    return FINE_TO_COARSE.get(fine_rel, "no_relation")


def project_coarse_to_category(coarse_rel: str) -> str:
    """Project a coarse-grained relation to its category-level parent."""
    return COARSE_TO_CATEGORY.get(coarse_rel, "no_relation")


def project_fine_to_category(fine_rel: str) -> str:
    """Project a fine-grained relation directly to its category-level parent."""
    coarse = project_fine_to_coarse(fine_rel)
    return project_coarse_to_category(coarse)