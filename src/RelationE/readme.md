# Final Relation Taxonomy (Aligned with Bulletin Content & Entity Schema)

## Key Changes from Original

**Removed** (not observed with named entities in bulletins):
- `subsidiary_of` — never explicitly stated
- `owns` — never explicitly stated (covered by `operates` for vehicles)
- `acquired` — never observed (financial bulletins discuss stock prices, not M&A)
- `headquartered_in` — never explicitly stated

**Kept all others** — all are attested in the bulletins with named entities.

**Result**: 29 fine relations + `no_relation`, 13 coarse relations + `no_relation`.

---

## A. Fine-Grained Relations (29 + `no_relation`)

| # | Relation | Definition | Domain → Range | Category |
|---|----------|-----------|----------------|----------|
| 1 | `governs` | Subject holds political office over a Place. | Person \| Organization → Place | Governance |
| 2 | `leads` | Subject is the leader/director/commander of an Organization. | Person \| Organization → Organization | Governance |
| 3 | `member_of` | Subject belongs to an Organization as a member. | Person \| Organization → Organization | Governance |
| 4 | `employs` | Subject Organization employs the Object Person. | Organization → Person | Governance |
| 5 | `controls` | Subject Organization has control over another Organization or Place. | Organization → Organization \| Place | Governance |
| 6 | `commanded_by` | Subject (military Org or Vehicle) is under command of Object Person. | Organization \| Vehicle → Person | Military |
| 7 | `attacked` | Subject attacked the Object. | Event \| Organization \| Vehicle → Person \| Organization \| Place \| Vehicle | Military |
| 8 | `sunk_by` | Subject Vehicle was destroyed/sunk by the Object. | Vehicle → Event \| Organization \| Vehicle \| Person | Military |
| 9 | `defeated` | Subject defeated the Object in battle. | Event \| Organization \| Person → Organization \| Person \| Place | Military |
| 10 | `casualty_of` | Subject Person died or was wounded in the Object Event. | Person → Event | Military |
| 11 | `operates` | Subject Organization operates/owns the Object Vehicle. | Organization → Vehicle | Military |
| 12 | `deployed_in` | Subject (Vehicle or Organization) is stationed in the Object Place. | Vehicle \| Organization → Place | Military |
| 13 | `signed` | Subject signed the Object LegalDocument. | Person \| Organization → LegalDocument | Legal |
| 14 | `ratifies` | Subject ratifies/approves the Object LegalDocument. | Place \| Organization → LegalDocument | Legal |
| 15 | `issued` | Subject issued the Object LegalDocument. | Person \| Organization → LegalDocument | Legal |
| 16 | `governs_subject` | Subject LegalDocument governs the Object. | LegalDocument → Place \| Person \| Organization \| Event | Legal |
| 17 | `party_to` | Subject is a party/signatory to the Object LegalDocument. | Person \| Organization \| Place → LegalDocument | Legal |
| 18 | `participated_in` | Subject took part in the Object Event. | Person \| Organization \| Vehicle → Event | Events |
| 19 | `organized` | Subject organized/convened the Object Event. | Person \| Organization → Event | Events |
| 20 | `hosted` | Subject Place hosted the Object Event. | Place → Event | Events |
| 21 | `occurred_in` | Subject Event took place at the Object Place. | Event → Place | Events |
| 22 | `mentions` | Subject explicitly mentions/references the Object, with no more specific relation holding. | Event \| LegalDocument \| Organization → Person \| Place \| Organization \| Vehicle | Events |
| 23 | `played_for` | Subject Person played for the Object Organization. | Person → Organization | Sports |
| 24 | `competed_against` | Subject competed against the Object. | Person \| Organization → Person \| Organization | Sports |
| 25 | `won` | Subject won the Object Event. | Person \| Organization → Event | Sports |
| 26 | `listed_on` | Subject Organization is listed on the Object (stock exchange). | Organization → Place \| Organization | Financial |
| 27 | `capital_of` | Subject Place is the capital of the Object Place. | Place → Place | Spatial |
| 28 | `located_in` | Subject is physically located in the Object Place. | Place \| Organization \| Vehicle → Place | Spatial |
| 29 | `reported` | Subject Organization reports on the Object Event. | Organization → Event | Media |

---

## B. Coarse-Grained Relations (13 + `no_relation`)

| # | Coarse Relation | Definition | Domain → Range | Absorbs |
|---|----------------|-----------|----------------|--------|
| C1 | `authority_over` | Subject governs, leads, controls, operates, or employs the Object. | Person \| Organization → Person \| Organization \| Place \| Vehicle | `governs`, `leads`, `controls`, `operates`, `employs` |
| C2 | `affiliated_with` | Subject is a member of, or under the command of, the Object. | Person \| Organization \| Vehicle → Organization \| Person | `member_of`, `commanded_by` |
| C3 | `conflict_with` | Subject attacked, defeated, or destroyed the Object in military context. | Event \| Organization \| Person \| Vehicle → Person \| Organization \| Place \| Vehicle | `attacked`, `sunk_by`, `defeated` |
| C4 | `military_involvement` | Subject is deployed in, or suffered casualties in, the Object. | Person \| Organization \| Vehicle → Event \| Place | `deployed_in`, `casualty_of` |
| C5 | `party_to_legal` | Subject signs, ratifies, issues, or is a party to the Object LegalDocument. | Person \| Organization \| Place → LegalDocument | `signed`, `ratifies`, `issued`, `party_to` |
| C6 | `legal_governs` | Subject LegalDocument governs or applies to the Object. | LegalDocument → Person \| Organization \| Place \| Event | `governs_subject` |
| C7 | `participates_in_event` | Subject participates in or organizes the Object Event. | Person \| Organization \| Vehicle → Event | `participated_in`, `organized` |
| C8 | `event_at_place` | Subject Event took place at, or was hosted by, the Object Place (direction-normalized). | Event → Place | `occurred_in`, `hosted` |
| C9 | `mentions` | Subject mentions/references the Object, with no more specific relation holding. | Event \| LegalDocument \| Organization → Person \| Place \| Organization \| Vehicle | `mentions` |
| C10 | `sports_relation` | Subject plays for, competes against, or won the Object. | Person \| Organization → Person \| Organization \| Event | `played_for`, `competed_against`, `won` |
| C11 | `corporate_relation` | Subject Organization is listed on the Object (exchange or place). | Organization → Place \| Organization | `listed_on` |
| C12 | `located_in` | Subject is physically located in, or is the capital of, the Object Place. | Place \| Organization \| Vehicle → Place | `located_in`, `capital_of` |
| C13 | `reported` | Subject Organization (media outlet) reports on the Object Event. | Organization → Event | `reported` |

**Note on C8**: When the candidate pair direction is `(Place, Event)`, the classifier should still label it `event_at_place` (direction-normalized). The valid pairs include both `("Event", "Place")` and `("Place", "Event")` so the classifier can assign the label regardless of input order.

---

## C. Fine → Coarse Mapping

| Fine | Coarse | Category |
|------|--------|----------|
| `governs` | `authority_over` | Governance |
| `leads` | `authority_over` | Governance |
| `controls` | `authority_over` | Governance |
| `operates` | `authority_over` | Governance |
| `employs` | `authority_over` | Governance |
| `member_of` | `affiliated_with` | Governance |
| `commanded_by` | `affiliated_with` | Governance |
| `attacked` | `conflict_with` | Military |
| `sunk_by` | `conflict_with` | Military |
| `defeated` | `conflict_with` | Military |
| `deployed_in` | `military_involvement` | Military |
| `casualty_of` | `military_involvement` | Military |
| `signed` | `party_to_legal` | Legal |
| `ratifies` | `party_to_legal` | Legal |
| `issued` | `party_to_legal` | Legal |
| `party_to` | `party_to_legal` | Legal |
| `governs_subject` | `legal_governs` | Legal |
| `participated_in` | `participates_in_event` | Events |
| `organized` | `participates_in_event` | Events |
| `occurred_in` | `event_at_place` | Events |
| `hosted` | `event_at_place` | Events |
| `mentions` | `mentions` | Events |
| `played_for` | `sports_relation` | Sports |
| `competed_against` | `sports_relation` | Sports |
| `won` | `sports_relation` | Sports |
| `listed_on` | `corporate_relation` | Financial |
| `capital_of` | `located_in` | Spatial |
| `located_in` | `located_in` | Spatial |
| `reported` | `reported` | Media |
| `no_relation` | `no_relation` | — |

---

## D. Python Format

### Fine-Grained

```python
from typing import Literal

RELATION_SCHEMA_FINE: dict[str, set[tuple[str, str]]] = {
    # === Governance & Authority ===
    "governs": {("Person", "Place"), ("Organization", "Place")},
    "leads": {("Person", "Organization"), ("Organization", "Organization")},
    "member_of": {("Person", "Organization"), ("Organization", "Organization")},
    "employs": {("Organization", "Person")},
    "controls": {("Organization", "Organization"), ("Organization", "Place")},
    # === Military & Conflict ===
    "commanded_by": {("Organization", "Person"), ("Vehicle", "Person")},
    "attacked": {
        ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"), ("Event", "Vehicle"),
        ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"), ("Organization", "Vehicle"),
        ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"), ("Vehicle", "Vehicle"),
    },
    "sunk_by": {
        ("Vehicle", "Event"), ("Vehicle", "Organization"), ("Vehicle", "Vehicle"), ("Vehicle", "Person"),
    },
    "defeated": {
        ("Event", "Organization"), ("Event", "Person"), ("Event", "Place"),
        ("Organization", "Organization"), ("Organization", "Person"), ("Organization", "Place"),
        ("Person", "Organization"), ("Person", "Person"), ("Person", "Place"),
    },
    "casualty_of": {("Person", "Event")},
    "operates": {("Organization", "Vehicle")},
    "deployed_in": {("Vehicle", "Place"), ("Organization", "Place")},
    # === Diplomacy & Legal ===
    "signed": {("Person", "LegalDocument"), ("Organization", "LegalDocument")},
    "ratifies": {("Place", "LegalDocument"), ("Organization", "LegalDocument")},
    "issued": {("Person", "LegalDocument"), ("Organization", "LegalDocument")},
    "governs_subject": {
        ("LegalDocument", "Place"), ("LegalDocument", "Person"),
        ("LegalDocument", "Organization"), ("LegalDocument", "Event"),
    },
    "party_to": {
        ("Person", "LegalDocument"), ("Organization", "LegalDocument"), ("Place", "LegalDocument"),
    },
    # === Events & Participation ===
    "participated_in": {("Person", "Event"), ("Organization", "Event"), ("Vehicle", "Event")},
    "organized": {("Person", "Event"), ("Organization", "Event")},
    "hosted": {("Place", "Event")},
    "occurred_in": {("Event", "Place")},
    "mentions": {
        ("Event", "Person"), ("Event", "Place"), ("Event", "Organization"), ("Event", "Vehicle"),
        ("LegalDocument", "Person"), ("LegalDocument", "Place"), ("LegalDocument", "Organization"), ("LegalDocument", "Vehicle"),
        ("Organization", "Person"), ("Organization", "Place"), ("Organization", "Organization"), ("Organization", "Vehicle"),
    },
    # === Sports & Competition ===
    "played_for": {("Person", "Organization")},
    "competed_against": {
        ("Person", "Person"), ("Person", "Organization"),
        ("Organization", "Person"), ("Organization", "Organization"),
    },
    "won": {("Person", "Event"), ("Organization", "Event")},
    # === Financial & Commercial ===
    "listed_on": {("Organization", "Place"), ("Organization", "Organization")},
    # === Spatial & Media ===
    "capital_of": {("Place", "Place")},
    "located_in": {("Place", "Place"), ("Organization", "Place"), ("Vehicle", "Place")},
    "reported": {("Organization", "Event")},
    # === Abstention ===
    "no_relation": {
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
    },
}

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

# Map fine → coarse for projection
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
```

### Coarse-Grained

```python
RELATION_SCHEMA_COARSE: dict[str, set[tuple[str, str]]] = {
    # C1: authority_over (governs, leads, controls, operates, employs)
    "authority_over": {
        ("Person", "Place"), ("Organization", "Place"),
        ("Person", "Organization"), ("Organization", "Organization"),
        ("Organization", "Vehicle"), ("Organization", "Person"),
    },
    # C2: affiliated_with (member_of, commanded_by)
    "affiliated_with": {
        ("Person", "Organization"), ("Organization", "Organization"),
        ("Organization", "Person"), ("Vehicle", "Person"),
    },
    # C3: conflict_with (attacked, sunk_by, defeated)
    "conflict_with": {
        ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"), ("Event", "Vehicle"),
        ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"), ("Organization", "Vehicle"),
        ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"), ("Vehicle", "Vehicle"),
        ("Person", "Organization"), ("Person", "Person"), ("Person", "Place"),
    },
    # C4: military_involvement (deployed_in, casualty_of)
    "military_involvement": {
        ("Vehicle", "Place"), ("Organization", "Place"), ("Person", "Event"),
    },
    # C5: party_to_legal (signed, ratifies, issued, party_to)
    "party_to_legal": {
        ("Person", "LegalDocument"), ("Organization", "LegalDocument"), ("Place", "LegalDocument"),
    },
    # C6: legal_governs (governs_subject)
    "legal_governs": {
        ("LegalDocument", "Place"), ("LegalDocument", "Person"),
        ("LegalDocument", "Organization"), ("LegalDocument", "Event"),
    },
    # C7: participates_in_event (participated_in, organized)
    "participates_in_event": {
        ("Person", "Event"), ("Organization", "Event"), ("Vehicle", "Event"),
    },
    # C8: event_at_place (occurred_in, hosted — direction-normalized)
    "event_at_place": {
        ("Event", "Place"), ("Place", "Event"),  # both directions valid
    },
    # C9: mentions
    "mentions": {
        ("Event", "Person"), ("Event", "Place"), ("Event", "Organization"), ("Event", "Vehicle"),
        ("LegalDocument", "Person"), ("LegalDocument", "Place"), ("LegalDocument", "Organization"), ("LegalDocument", "Vehicle"),
        ("Organization", "Person"), ("Organization", "Place"), ("Organization", "Organization"), ("Organization", "Vehicle"),
    },
    # C10: sports_relation (played_for, competed_against, won)
    "sports_relation": {
        ("Person", "Organization"), ("Person", "Person"),
        ("Organization", "Person"), ("Organization", "Organization"),
        ("Person", "Event"), ("Organization", "Event"),
    },
    # C11: corporate_relation (listed_on)
    "corporate_relation": {
        ("Organization", "Place"), ("Organization", "Organization"),
    },
    # C12: located_in (located_in, capital_of)
    "located_in": {
        ("Place", "Place"), ("Organization", "Place"), ("Vehicle", "Place"),
    },
    # C13: reported
    "reported": {
        ("Organization", "Event"),
    },
    # Abstention
    "no_relation": {
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
    },
}

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
```

### Optional: Category-Level (7 labels)

```python
RELATION_SCHEMA_CATEGORY: dict[str, set[tuple[str, str]]] = {
    "governance": {
        # authority_over + affiliated_with
        ("Person", "Place"), ("Organization", "Place"),
        ("Person", "Organization"), ("Organization", "Organization"),
        ("Organization", "Vehicle"), ("Organization", "Person"),
        ("Vehicle", "Person"),
    },
    "conflict": {
        # conflict_with + military_involvement
        ("Event", "Person"), ("Event", "Organization"), ("Event", "Place"), ("Event", "Vehicle"),
        ("Organization", "Person"), ("Organization", "Organization"), ("Organization", "Place"), ("Organization", "Vehicle"),
        ("Vehicle", "Person"), ("Vehicle", "Organization"), ("Vehicle", "Place"), ("Vehicle", "Vehicle"),
        ("Person", "Organization"), ("Person", "Person"), ("Person", "Place"),
        ("Person", "Event"),
    },
    "legal": {
        # party_to_legal + legal_governs
        ("Person", "LegalDocument"), ("Organization", "LegalDocument"), ("Place", "LegalDocument"),
        ("LegalDocument", "Place"), ("LegalDocument", "Person"),
        ("LegalDocument", "Organization"), ("LegalDocument", "Event"),
    },
    "event": {
        # participates_in_event + event_at_place + mentions
        ("Person", "Event"), ("Organization", "Event"), ("Vehicle", "Event"),
        ("Event", "Place"), ("Place", "Event"),
        ("Event", "Person"), ("Event", "Organization"), ("Event", "Vehicle"),
        ("LegalDocument", "Person"), ("LegalDocument", "Place"), ("LegalDocument", "Organization"), ("LegalDocument", "Vehicle"),
        ("Organization", "Person"), ("Organization", "Place"), ("Organization", "Organization"), ("Organization", "Vehicle"),
    },
    "sports": {
        # sports_relation
        ("Person", "Organization"), ("Person", "Person"),
        ("Organization", "Person"), ("Organization", "Organization"),
        ("Person", "Event"), ("Organization", "Event"),
    },
    "financial": {
        # corporate_relation
        ("Organization", "Place"), ("Organization", "Organization"),
    },
    "spatial_media": {
        # located_in + reported
        ("Place", "Place"), ("Organization", "Place"), ("Vehicle", "Place"),
        ("Organization", "Event"),
    },
    "no_relation": {
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
    },
}

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
```

---

## Summary of Changes from Original

| Action | Relation | Rationale |
|--------|---------|-----------|
| **REMOVE** | `subsidiary_of` | Never explicitly stated with named entities in bulletins |
| **REMOVE** | `owns` | Never explicitly stated; `operates` covers Organization→Vehicle |
| **REMOVE** | `acquired` | Never observed; financial bulletins discuss stock prices, not M&A |
| **REMOVE** | `headquartered_in` | Never explicitly stated in bulletins |
| **KEEP** | All 29 remaining | All attested with named entities in the bulletins |
| **NOTE** | `no_relation` | Defined for all 36 possible type pairs (6×6) so classifier can always abstain |
| **NOTE** | C8 `event_at_place` | Includes both `("Event","Place")` and `("Place","Event")` — direction-normalized per your design |
| **NOTE** | `member_of`, `leads` | Include `("Organization","Organization")` in addition to `("Person","Organization")` |