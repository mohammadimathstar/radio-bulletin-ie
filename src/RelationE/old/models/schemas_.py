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

RELATION_DESCRIPTIONS_FINE: dict[str, str] = {
    # Governance & Authority
    "governs": "Subject holds political or executive office over a Place (e.g., a Prime Minister over a country, a mayor over a city). Look for titles like 'burgemeester van [Place]', 'president van [Place]'.",
    "leads": "Subject is the head, director, commander, or chairman of an Organization. Look for 'chef van [Org]', 'voorzitter van [Org]', 'directeur van [Org]'.",
    "member_of": "Subject belongs to an Organization as a member, official, or affiliate. Look for 'lid van [Org]', 'afgevaardigde van [Org]'.",
    "employs": "Subject Organization employs the Object Person as staff, official, or soldier. Look for 'werknemers van [Org]', 'personeel van [Org]'.",
    "controls": "Subject Organization has operational, political, or military control over another Organization or Place. Look for 'beheerst [Place/Org]', 'onder gezag van [Org]', 'bezette [Place]'.",
    # Military & Conflict
    "commanded_by": "Subject (a military Organization or Vehicle) is under the command of the Object Person. Look for 'onder leiding van [Person]', 'onder bevel van [Person]'.",
    "attacked": "Subject (Event, military Organization, or Vehicle) attacked the Object. Look for 'viel [Object] aan', 'beschoten [Object]', 'gebombardeerd [Object]'.",
    "sunk_by": "Subject Vehicle (Ship or Submarine) was destroyed or sunk by the Object. Look for 'tot zinken gebracht door [Object]', 'getorpedeerd door [Object]'.",
    "defeated": "Subject (Event, Organization, or Person) defeated the Object in battle. Look for 'versloeg [Object]', 'overwinning op [Object]'.",
    "casualty_of": "Subject Person died, was wounded, or was missing as a result of the Object Event. Look for 'kwam om bij [Event]', 'gewond bij [Event]'.",
    "operates": "Subject Organization operates or owns the Object Vehicle. Look for '[Org] liet [Vehicle] varen/vliegen', '[Vehicle] van [Org]'.",
    "deployed_in": "Subject (Vehicle or Organization) is stationed, operating, or deployed in the Object Place. Look for 'gestationeerd in [Place]', 'uitgevaren naar [Place]'.",
    # Diplomacy & Legal
    "signed": "Subject (Person or Organization) signed the Object LegalDocument. Look for 'onderteekend door [Person/Org]', 'getekend door [Person/Org]'.",
    "ratifies": "Subject (Place = country, or Organization) ratifies or formally approves the Object LegalDocument. Look for 'geratificeerd door [Place/Org]', 'goedgekeurd door [Place/Org]'.",
    "issued": "Subject (Person or Organization) issued or promulgated the Object LegalDocument. Look for 'uitgevaardigd door [Person/Org]', 'afgekondigd door [Person/Org]'.",
    "governs_subject": "Subject LegalDocument governs, regulates, or applies to the Object. Look for 'betreffende [Object]', 'inzake [Object]', 'met betrekking tot [Object]'.",
    "party_to": "Subject (Person, Organization, or Place) is a party, signatory, or participant to the Object LegalDocument. Look for '[Person/Org/Place] was vertegenwoordigd bij [LegalDoc]'.",
    # Events & Participation
    "participated_in": "Subject (Person, Organization, or Vehicle) took part in the Object Event. Look for 'deelnemer aan [Event]', 'nam deel aan [Event]'.",
    "organized": "Subject (Person or Organization) organized, convened, or arranged the Object Event. Look for 'georganiseerd door [Person/Org]', 'bijeengeroepen door [Person/Org]'.",
    "hosted": "Subject Place hosted or was the venue for the Object Event. Look for '[Event] in [Place]', '[Place] was het toneel van [Event]'.",
    "occurred_in": "Subject Event took place at or in the Object Place. Look for 'gebeurde in [Place]', 'vond plaats in [Place]', 'te [Place]'.",
    "mentions": "Subject (Event, LegalDocument, or Organization) explicitly mentions or references the Object, but no more specific relation holds. Use only when no other relation applies.",
    # Sports & Competition
    "played_for": "Subject Person (athlete) played for the Object Organization. Look for '[Person] van [Org]', '[Person] speelde voor [Org]'.",
    "competed_against": "Subject (Person or Organization) competed against the Object (Person or Organization). Look for '[Subject] vs [Object]', '[Subject] tegen [Object]'.",
    "won": "Subject (Person or Organization) won the Object Event. Look for '[Subject] won [Event]', 'overwinning voor [Subject]'.",
    # Financial & Commercial
    "listed_on": "Subject Organization is listed on the Object (stock exchange). Look for '[Org] op de beurs van [Place]', '[Org] noteerde op [Place/Org]'.",
    # Spatial & Media
    "capital_of": "Subject Place (a settlement) is the capital of the Object Place (a country). Look for '[Place], de hoofdstad van [Place]'.",
    "located_in": "Subject (Place, Organization, or Vehicle) is physically located in the Object Place. Look for 'in [Place]', 'te [Place]', 'gelegen in [Place]'.",
    "reported": "Subject Organization (media outlet or broadcaster) reports on the Object Event. Look for '[Org] meldt', '[Org] deelt mede', '[Org] verneemt'.",
    # Abstention
    "no_relation": "No specific relation holds between the two entities. Use when entities co-occur but no defined relation applies.",
}

RELATION_DESCRIPTIONS_COARSE: dict[str, str] = {
    "authority_over": "Subject governs, leads, controls, operates, or employs the Object. The Subject holds power, authority, or ownership over the Object.",
    "affiliated_with": "Subject is a member of, or under the command of, the Object. The Subject is subordinate to or belongs to the Object Organization.",
    "conflict_with": "Subject attacked, defeated, or destroyed the Object in a military or armed-conflict context. Look for military aggression, battles, sinking, or surrender.",
    "military_involvement": "Subject is deployed in, or suffered casualties in, the Object (an Event or Place). Look for troop deployments, stationing, or persons killed/wounded.",
    "party_to_legal": "Subject signs, ratifies, issues, or is otherwise a party to the Object LegalDocument. Look for diplomatic or legal acts involving treaties, laws, decrees.",
    "legal_governs": "Subject LegalDocument governs, regulates, or applies to the Object. The LegalDocument is about, or applies to, the Object entity.",
    "participates_in_event": "Subject participates in or organizes the Object Event. The Subject is actively involved in making the Event happen or taking part in it.",
    "event_at_place": "Subject Event took place at, or was hosted by, the Object Place. Direction-normalized: works in both (Event, Place) and (Place, Event) directions.",
    "mentions": "Subject mentions or references the Object, with no more specific relation holding. Use only when no governance, conflict, legal, or participation relation applies.",
    "sports_relation": "Subject (Person or Organization) plays for, competes against, or won the Object. Look for athletic competition, team membership, or match results.",
    "corporate_relation": "Subject Organization is corporately tied to the Object: listed on a stock exchange or headquartered there.",
    "located_in": "Subject is physically located in, or is the capital of, the Object Place. Captures spatial containment and capital-city relations.",
    "reported": "Subject Organization (media outlet or broadcaster) reports on the Object Event. Look for '[Org] meldt', '[Org] deelt mede'.",
    "no_relation": "No specific relation holds between the two entities. Use when entities co-occur but no defined relation applies.",
}