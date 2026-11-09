"""
The relation schema: ONE source of truth (33 fine relations) with the coarse and category levels derived from it.

Revised from the uploaded schemas.py; the structure (RelationDefinition, three levels, projections, Dutch cue phrases in the descriptions) is kept. What changed and why:
  * `no_relation` is NOT a relation of the schema any more: it is the abstention option, added once by jev.py. (As a schema entry it made every pair of types "compatible"
    and produced three `no_relation` options per question.)
  * Duplicates that are the same fact from two sides were merged: hosted -> occurred_in (direction options already handle "[Place] was the scene of [Event]"),
    commanded_by -> leads (a person leads an organization or a ship), employs -> member_of (member, official, employee).  `mentions` (a catch-all that attracts every
    unclear pair) was removed: that is what no_relation is for.
  * Legal relations also accept an Event as object (a treaty is an Event in the NER output, there is no LegalDocument in it).
  * Added what the bulletins are full of: beat (sports results: "HHC won van EDO"), traveled_to / departed_from (ships, delegations), based_in ("Stedelijk Orkest uit PURMEREND"),
    met_with / negotiated_with / allied_with / opposed (diplomacy).
  * The coarse and category levels are built from COARSE_GROUPS, so a fine relation cannot be forgotten or mapped twice (checked by validate_schema).
Only the entity TYPE is used (Person, Organization, Place, Event, Vehicle, LegalDocument); subtypes and topics are not needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

NO_RELATION = "no_relation"
PERSON, ORG, PLACE, EVENT, VEHICLE, LEGAL = "Person", "Organization", "Place", "Event", "Vehicle", "LegalDocument"
ALL_ENTITY_TYPES = frozenset({PERSON, ORG, PLACE, EVENT, VEHICLE, LEGAL})
ACTORS = (PERSON, ORG, PLACE)           # people, organizations and countries can act in politics


def _x(subjects: Iterable[str], objects: Iterable[str]) -> frozenset[tuple[str, str]]:
    objects = tuple(objects)
    return frozenset((s, o) for s in subjects for o in objects)


@dataclass(frozen=True)
class RelationDefinition:
    description: str
    allowed_types: frozenset[tuple[str, str]]       # (subject type, object type); the subject is the head of the relation
    symmetric: bool = False


FINE_RELATIONS: dict[str, RelationDefinition] = {
    # ---- governance and authority
    "governs": RelationDefinition("Subject holds political or executive office over a Place (a prime minister over a country, a mayor over a city). Look for 'burgemeester van [Place]', 'president van [Place]'.",
                                  _x((PERSON, ORG), (PLACE,))),
    "leads": RelationDefinition("Subject is the head, director, commander, captain or chairman of the Object Organization or Vehicle. Look for 'chef van [Org]', 'voorzitter van [Org]', 'directeur van [Org]', 'kapitein van [Vehicle]', 'onder bevel van' (reversed).",
                                _x((PERSON,), (ORG, VEHICLE))),
    "member_of": RelationDefinition("Subject belongs to the Object Organization as a member, official, employee, soldier or delegate. Look for 'lid van [Org]', 'afgevaardigde van [Org]', 'personeel van [Org]'.",
                                    _x((PERSON, ORG), (ORG,))),
    "controls": RelationDefinition("Subject Organization has operational, political or military control over the Object Organization or Place. Look for 'beheerst [Object]', 'onder gezag van [Org]', 'bezette [Place]'.",
                                   _x((ORG,), (ORG, PLACE))),
    "operates": RelationDefinition("Subject Organization operates or owns the Object Vehicle. Look for '[Vehicle] van de [Org]', '[Org] liet [Vehicle] varen/vliegen'.",
                                   _x((ORG,), (VEHICLE,))),
    # ---- military and conflict
    "attacked": RelationDefinition("Subject (Event, military Organization or Vehicle) attacked the Object. Look for 'viel [Object] aan', 'beschoten [Object]', 'gebombardeerd [Object]'.",
                                   _x((EVENT, ORG, VEHICLE), (PERSON, ORG, PLACE, VEHICLE))),
    "sunk_by": RelationDefinition("Subject Vehicle (ship, submarine) was destroyed or sunk by the Object. Look for 'tot zinken gebracht door [Object]', 'getorpedeerd door [Object]'.",
                                  _x((VEHICLE,), (EVENT, ORG, VEHICLE, PERSON))),
    "defeated": RelationDefinition("Subject defeated the Object in BATTLE or war. Look for 'versloeg [Object]', 'overwinning op [Object]'. For sports results use beat.",
                                   _x((EVENT, ORG, PERSON), (ORG, PERSON, PLACE))),
    "casualty_of": RelationDefinition("Subject Person died, was wounded or missing as a result of the Object Event. Look for 'kwam om bij [Event]', 'gewond bij [Event]'.",
                                      _x((PERSON,), (EVENT,))),
    "deployed_in": RelationDefinition("Subject (Vehicle or Organization) is stationed or deployed MILITARILY in the Object Place. Look for 'gestationeerd in [Place]', 'troepen in [Place]'. For ordinary journeys use traveled_to.",
                                      _x((VEHICLE, ORG), (PLACE,))),
    # ---- movement
    "traveled_to": RelationDefinition("Subject (Person, Organization or Vehicle) travelled, sailed or flew to the Object Place. Look for 'vertrok naar [Place]', 'aangekomen te [Place]', 'reisde naar [Place]', 'uitgevaren naar [Place]'.",
                                      _x((PERSON, ORG, VEHICLE), (PLACE,))),
    "departed_from": RelationDefinition("Subject (Person, Organization or Vehicle) left the Object Place. Look for 'vertrok uit [Place]', 'verliet [Place]'.",
                                        _x((PERSON, ORG, VEHICLE), (PLACE,))),
    # ---- diplomacy
    "met_with": RelationDefinition("Subject and Object met in person or held an audience or conversation. Look for 'ontving', 'onderhoud met', 'bezocht [Person]'.", 
                                   _x(ACTORS, ACTORS), True),
    "negotiated_with": RelationDefinition("Subject and Object negotiated or conferred about an agreement or dispute. Look for 'onderhandelingen tusschen [A] en [B]', 'besprekingen met [B]'.", _x(ACTORS, ACTORS), True),
    "allied_with": RelationDefinition("Subject and Object (organizations or countries) are allies or have a pact of mutual support. Look for 'bondgenoot', 'verbond tusschen'.", _x((ORG, PLACE), (ORG, PLACE)), True),
    "opposed": RelationDefinition("Subject protested against, criticized or rejected the Object, without armed action. Look for 'protesteerde tegen [Object]', 'verzet zich tegen', 'afwijzing van [Object]'.", _x(ACTORS, ACTORS + (EVENT,))),
    # ---- diplomacy and law
    "signed": RelationDefinition("Subject (Person, Organization or country) signed the Object LegalDocument or treaty (a treaty may be an Event). Look for 'onderteekend door', 'getekend door', 'teekende het verdrag'.", _x(ACTORS, (LEGAL, EVENT))),
    "ratifies": RelationDefinition("Subject (country or Organization) ratified or formally approved the Object LegalDocument or treaty. Look for 'geratificeerd door', 'goedgekeurd door'.", _x((PLACE, ORG), (LEGAL, EVENT))),
    "issued": RelationDefinition("Subject (Person or Organization) issued or promulgated the Object LegalDocument. Look for 'uitgevaardigd door', 'afgekondigd door'.", _x((PERSON, ORG), (LEGAL,))),
    "governs_subject": RelationDefinition("Subject LegalDocument governs, regulates or applies to the Object. Look for 'betreffende [Object]', 'inzake [Object]', 'met betrekking tot [Object]'.", _x((LEGAL,), (PLACE, PERSON, ORG, EVENT))),
    "party_to": RelationDefinition("Subject (Person, Organization or country) is a party to the Object LegalDocument or TREATY/pact/agreement (an Event). Not for ordinary events: use participated_in.", _x(ACTORS, (LEGAL, EVENT))),
    # ---- events
    "participated_in": RelationDefinition("Subject (Person, Organization or Vehicle) took part in the Object Event. Look for 'deelnemer aan [Event]', 'nam deel aan [Event]'; the Subject may be named inside the event phrase.", _x((PERSON, ORG, VEHICLE), (EVENT,))),
    "organized": RelationDefinition("Subject (Person or Organization) organized, convened or arranged the Object Event. Look for 'georganiseerd door [Subject]', 'bijeengeroepen door [Subject]'.", _x((PERSON, ORG), (EVENT,))),
    "occurred_in": RelationDefinition("Subject Event took place in, or was hosted by, the Object Place. Look for 'vond plaats in [Place]', '[Event] te [Place]', '[Place] was het toneel van [Event]'.", _x((EVENT,), (PLACE,))),
    # ---- sports
    "played_for": RelationDefinition("Subject Person (athlete) played for the Object Organization. Look for '[Person] van [Club]', '[Person] speelde voor [Club]'.", _x((PERSON,), (ORG,))),
    "competed_against": RelationDefinition("Subject and Object played against each other and the text does NOT say who won. Look for '[A] tegen [B]', '[A]-[B]', 'wedstrijd tusschen [A] en [B]'.", _x((PERSON, ORG), (PERSON, ORG)), True),
    "beat": RelationDefinition("Subject beat the Object in a sports match or contest (the text says who won). Look for '[Subject] won van [Object]', 'versloeg', '[Subject] won met 11-2 van [Object]'.", _x((PERSON, ORG), (PERSON, ORG))),
    "won": RelationDefinition("Subject (Person or Organization) won the Object Event. Look for '[Subject] won [Event]', 'winnaar van [Event]'.", _x((PERSON, ORG), (EVENT,))),
    # ---- financial
    "listed_on": RelationDefinition("Subject Organization is listed or quoted on the Object (a stock exchange). Look for '[Org] op de beurs van [Place]', '[Org] noteerde te [Place]'.", _x((ORG,), (PLACE, ORG))),
    # ---- spatial and media
    "capital_of": RelationDefinition("Subject Place (a city) is the capital of the Object Place (a country). Look for '[Place], de hoofdstad van [Place]'.", _x((PLACE,), (PLACE,))),
    "located_in": RelationDefinition("Subject (Place, Organization or Vehicle) is physically located in the Object Place. Look for 'in [Place]', 'te [Place]', 'gelegen in [Place]'.", _x((PLACE, ORG, VEHICLE), (PLACE,))),
    "based_in": RelationDefinition("Subject Organization (club, band, society, firm) is based in, or comes from, the Object Place. Look for '[Org] uit [Place]', 'de [Org] van [Place]'.", _x((ORG,), (PLACE,))),
    "reported": RelationDefinition("Subject Organization (news agency, broadcaster) reports on the Object Event. Look for '[Org] meldt', '[Org] deelt mede', '[Org] verneemt'.", _x((ORG,), (EVENT,))),
}

#: coarse relation -> (category, description, fine members)
COARSE_GROUPS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "authority_over": ("governance", "Subject governs, leads, controls or operates the Object.", ("governs", "leads", "controls", "operates")),
    "affiliated_with": ("governance", "Subject is a member, official or employee of the Object organization.", ("member_of",)),
    "diplomacy": ("governance", "Subject and Object meet, negotiate, ally or oppose each other.", ("met_with", "negotiated_with", "allied_with", "opposed")),
    "conflict_with": ("conflict", "Subject attacked, defeated or destroyed the Object in an armed conflict.", ("attacked", "sunk_by", "defeated")),
    "military_involvement": ("conflict", "Subject is deployed in, or suffered casualties in, the Object.", ("deployed_in", "casualty_of")),
    "party_to_legal": ("legal", "Subject signs, ratifies, issues or is a party to the Object legal document or treaty.", ("signed", "ratifies", "issued", "party_to")),
    "legal_governs": ("legal", "Subject LegalDocument governs or applies to the Object.", ("governs_subject",)),
    "participates_in_event": ("event", "Subject participates in or organizes the Object Event.", ("participated_in", "organized")),
    "event_at_place": ("event", "Subject Event took place at the Object Place.", ("occurred_in",)),
    "sports_relation": ("sports", "Subject plays for, competes against, beat or won the Object.", ("played_for", "competed_against", "beat", "won")),
    "corporate_relation": ("financial", "Subject Organization is listed on the Object.", ("listed_on",)),
    "movement": ("spatial_media", "Subject travelled to or left the Object Place.", ("traveled_to", "departed_from")),
    "located_in": ("spatial_media", "Subject is located in, based in, or is the capital of the Object Place.", ("located_in", "capital_of", "based_in")),
    "reported": ("spatial_media", "Subject Organization reports on the Object Event.", ("reported",)),
}
CATEGORY_DESCRIPTIONS = {
    "governance": "authority, membership and diplomacy between persons, organizations and countries",
    "conflict": "armed conflict, deployment and casualties", "legal": "treaties, laws and the parties to them",
    "event": "participation in events and where events take place", "sports": "sports teams, matches and results",
    "financial": "listing on exchanges", "spatial_media": "location, movement and news reporting",
}
FINE_TO_COARSE = {fine: coarse for coarse, (_, _, members) in COARSE_GROUPS.items() for fine in members}
COARSE_TO_CATEGORY = {coarse: cat for coarse, (cat, _, _) in COARSE_GROUPS.items()}


def _derive(groups: Mapping[str, tuple[str, ...]], descriptions: Mapping[str, str], parent: Mapping[str, RelationDefinition]) -> dict[str, RelationDefinition]:
    out = {}
    for name, members in groups.items():
        out[name] = RelationDefinition(descriptions[name], frozenset().union(*(parent[m].allowed_types for m in members)), all(parent[m].symmetric for m in members))
    return out


RELATION_SCHEMA_FINE = FINE_RELATIONS
RELATION_SCHEMA_COARSE = _derive({c: g[2] for c, g in COARSE_GROUPS.items()}, {c: g[1] for c, g in COARSE_GROUPS.items()}, FINE_RELATIONS)
_cat_members: dict[str, list[str]] = {}
for _c, _cat in COARSE_TO_CATEGORY.items():
    _cat_members.setdefault(_cat, []).append(_c)
RELATION_SCHEMA_CATEGORY = _derive({k: tuple(v) for k, v in _cat_members.items()}, CATEGORY_DESCRIPTIONS, RELATION_SCHEMA_COARSE)
SCHEMAS = {"fine": RELATION_SCHEMA_FINE, "coarse": RELATION_SCHEMA_COARSE, "category": RELATION_SCHEMA_CATEGORY}


def get_schema(level: str = "fine") -> dict[str, RelationDefinition]:
    if level not in SCHEMAS:
        raise ValueError(f"level must be one of {sorted(SCHEMAS)}, not {level!r}")
    return SCHEMAS[level]


def get_allowed_relations(type_a: str, type_b: str, schema: Mapping[str, RelationDefinition]) -> set[str]:
    """Relations that can hold FROM an entity of type_a TO an entity of type_b (the direction matters)."""
    return {r for r, d in schema.items() if (type_a, type_b) in d.allowed_types}


def compatible_relations(type1: str, type2: str, schema: Mapping[str, RelationDefinition]) -> list[str]:
    """Relations compatible with two entity types in EITHER direction (the textual order is not the semantic direction), in schema order. no_relation is never in the list."""
    return [r for r, d in schema.items() if (type1, type2) in d.allowed_types or (type2, type1) in d.allowed_types]


def is_symmetric(rel: str, schema: Mapping[str, RelationDefinition]) -> bool:
    return schema[rel].symmetric if rel in schema else False


def project_fine_to_coarse(fine: str) -> str:
    return FINE_TO_COARSE.get(fine, NO_RELATION)


def project_fine_to_category(fine: str) -> str:
    return COARSE_TO_CATEGORY.get(project_fine_to_coarse(fine), NO_RELATION)


def check_entity_types(types_in_data: Mapping[str, int], schema: Mapping[str, RelationDefinition] | None = None) -> dict:
    """Compare the entity types of the NER output with the schema: types the schema does not know (their pairs are skipped), schema types the data never has, and
    the relations that can never fire because one of their types is missing in the data."""
    schema = schema or FINE_RELATIONS
    in_schema = {t for d in schema.values() for pair in d.allowed_types for t in pair}
    present = set(types_in_data)
    unreachable = sorted(r for r, d in schema.items() if not any(a in present and b in present for a, b in d.allowed_types))
    return dict(unknown_to_schema=sorted(present - in_schema), unused_by_data=sorted(in_schema - present), unreachable_relations=unreachable)


def validate_schema() -> list[str]:
    """Problems of the schema itself (empty = consistent)."""
    problems = []
    for rel, d in FINE_RELATIONS.items():
        if rel == NO_RELATION:
            problems.append("no_relation must not be a relation of the schema")
        if not d.allowed_types or any(t not in ALL_ENTITY_TYPES for p in d.allowed_types for t in p):
            problems.append(f"{rel}: empty or unknown types")
        if d.symmetric and any((b, a) not in d.allowed_types for a, b in d.allowed_types):
            problems.append(f"{rel}: symmetric but not closed under swapping the types")
        if rel not in FINE_TO_COARSE:
            problems.append(f"{rel}: has no coarse relation")
    multi = [r for r in FINE_TO_COARSE if sum(r in g[2] for g in COARSE_GROUPS.values()) != 1]
    problems += [f"{r}: in more than one coarse group" for r in multi]
    problems += [f"coarse group {c}: unknown fine member {m}" for c, g in COARSE_GROUPS.items() for m in g[2] if m not in FINE_RELATIONS]
    return problems
