# Relation Type Descriptions for JEV AI

Here are short, practical descriptions for each relation, designed to help a JEV (Joint Evidence Verification) model make accurate decisions. Each description is concise and focused on the **signal the model should look for** in the text.

---

## Fine-Grained Relations (29 + `no_relation`)

### Category 1 — Governance & Authority

| Relation | Short Description for JEV |
|----------|--------------------------|
| `governs` | Subject holds political or executive office over a Place (e.g. a Prime Minister over a country, a mayor over a city). Look for titles like "burgemeester van [Place]", "president van [Place]", "Koningin van [Place]". |
| `leads` | Subject is the head, director, commander, or chairman of an Organization. Look for "chef van [Org]", "voorzitter van [Org]", "directeur van [Org]", "leider van [Org]". |
| `member_of` | Subject belongs to an Organization as a member, official, or affiliate. Look for "lid van [Org]", "afgevaardigde van [Org]", "behoort tot [Org]". |
| `employs` | Subject Organization employs the Object Person as staff, official, or soldier. Look for "werknemers van [Org]", "personeel van [Org]", military units employing soldiers. |
| `controls` | Subject Organization has operational, political, or military control over another Organization or Place. Look for "beheerst [Place/Org]", "onder gezag van [Org]", "bezette [Place]". |

### Category 2 — Military & Conflict

| Relation | Short Description for JEV |
|----------|--------------------------|
| `commanded_by` | Subject (a military Organization or Vehicle) is under the command of the Object Person. Look for "onder leiding van [Person]", "onder bevel van [Person]", "[Person] voerde het bevel over [Org/Vehicle]". |
| `attacked` | Subject (Event, military Organization, or Vehicle) attacked the Object. Look for "viel [Object] aan", "beschoten [Object]", "gebombardeerd [Object]", "aanval op [Object]". |
| `sunk_by` | Subject Vehicle (Ship or Submarine) was destroyed or sunk by the Object. Look for "tot zinken gebracht door [Object]", "gezonken door [Object]", "getorpedeerd door [Object]". |
| `defeated` | Subject (Event, Organization, or Person) defeated the Object in battle. Look for "versloeg [Object]", "overwinning op [Object]", "[Object] gaf zich over". |
| `casualty_of` | Subject Person died, was wounded, or was missing as a result of the Object Event. Look for "kwam om bij [Event]", "gewond bij [Event]", "verdronken bij [Event]", "slachtoffers van [Event]". |
| `operates` | Subject Organization operates or owns the Object Vehicle (fleet operator, navy, airline). Look for "[Org] liet [Vehicle] varen/vliegen", "[Vehicle] van [Org]", "[Org] onderhoudt [Vehicle]". |
| `deployed_in` | Subject (Vehicle or Organization) is stationed, operating, or deployed in the Object Place. Look for "gestationeerd in [Place]", "uitgevaren naar [Place]", "gelegen in [Place]". |

### Category 3 — Diplomacy & Legal

| Relation | Short Description for JEV |
|----------|--------------------------|
| `signed` | Subject (Person or Organization) signed the Object LegalDocument (treaty, agreement, communique). Look for "onderteekend door [Person/Org]", "getekend door [Person/Org]". |
| `ratifies` | Subject (Place = country, or Organization) ratifies or formally approves the Object LegalDocument. Look for "geratificeerd door [Place/Org]", "goedgekeurd door [Place/Org]". |
| `issued` | Subject (Person or Organization) issued or promulgated the Object LegalDocument (decree, law, communique). Look for "uitgevaardigd door [Person/Org]", "afgekondigd door [Person/Org]", "bekendgemaakt door [Person/Org]". |
| `governs_subject` | Subject LegalDocument governs, regulates, or applies to the Object (Place, Person, Organization, or Event). Look for "betreffende [Object]", "inzake [Object]", "met betrekking tot [Object]", "van toepassing op [Object]". |
| `party_to` | Subject (Person, Organization, or Place) is a party, signatory, or participant to the Object LegalDocument (typically a treaty or agreement). Look for "[Person/Org/Place] was vertegenwoordigd bij [LegalDoc]", "namen deel aan [LegalDoc]". |

### Category 4 — Events & Participation

| Relation | Short Description for JEV |
|----------|--------------------------|
| `participated_in` | Subject (Person, Organization, or Vehicle) took part in the Object Event. Look for "deelnemer aan [Event]", "nam deel aan [Event]", "aanwezig bij [Event]". |
| `organized` | Subject (Person or Organization) organized, convened, or arranged the Object Event. Look for "georganiseerd door [Person/Org]", "bijeengeroepen door [Person/Org]". |
| `hosted` | Subject Place hosted or was the venue for the Object Event. Look for "[Event] in [Place]", "[Place] was het toneel van [Event]". |
| `occurred_in` | Subject Event took place at or in the Object Place. Look for "gebeurde in [Place]", "vond plaats in [Place]", "te [Place]". |
| `mentions` | Subject (Event, LegalDocument, or Organization) explicitly mentions or references the Object, but no more specific relation holds. Look for "[Subject] noemde [Object]", "verwees naar [Object]", "rondom [Object]". Use only when no other relation applies. |

### Category 5 — Sports & Competition

| Relation | Short Description for JEV |
|----------|--------------------------|
| `played_for` | Subject Person (athlete) played for the Object Organization (sports club or national team). Look for "[Person] van [Org]", "[Person] speelde voor [Org]", "[Person] (clubgenoot van [Org])". |
| `competed_against` | Subject (Person or Organization) competed against the Object (Person or Organization), typically in a sports Event. Look for "[Subject] vs [Object]", "[Subject] tegen [Object]", "wedstrijd [Subject]-[Object]". |
| `won` | Subject (Person or Organization) won the Object Event (sports match, race, tournament). Look for "[Subject] won [Event]", "overwinning voor [Subject]", "winst van [Subject] op [Event]". |

### Category 6 — Financial & Commercial

| Relation | Short Description for JEV |
|----------|--------------------------|
| `listed_on` | Subject Organization (typically a commercial company) is listed on the Object (Place = stock exchange city, or Organization = the exchange). Look for "[Org] op de beurs van [Place]", "[Org] noteerde op [Place/Org]". |

### Category 7 — Spatial & Media

| Relation | Short Description for JEV |
|----------|--------------------------|
| `capital_of` | Subject Place (a settlement) is the capital of the Object Place (a country or administrative division). Look for "[Place], de hoofdstad van [Place]", "[Place] is de residentie van [Place]". |
| `located_in` | Subject (Place, Organization, or Vehicle) is physically located in the Object Place. Look for "in [Place]", "te [Place]", "gelegen in [Place]". Distinguish from `originates_from` (Person's hometown) and `occurred_in` (Event location). |
| `reported` | Subject Organization (a media outlet, news agency, or radio broadcaster) reports on or covers the Object Event. Look for "[Org] meldt", "[Org] deelt mede", "[Org] verneemt", "volgens [Org]". This is one of the most frequent relations in the corpus. |

### Abstention

| Relation | Short Description for JEV |
|----------|--------------------------|
| `no_relation` | No specific relation holds between the two entities. Use when entities co-occur but no defined relation applies, or when the relation is too vague to classify. |

---

## Coarse-Grained Relations (13 + `no_relation`)

| Coarse Relation | Short Description for JEV |
|----------------|--------------------------|
| `authority_over` | Subject governs, leads, controls, operates, or employs the Object. The Subject holds power, authority, or ownership over the Object. Look for governance, leadership, command, or operational control. |
| `affiliated_with` | Subject is a member of, or under the command of, the Object. The Subject is subordinate to or belongs to the Object Organization. Look for membership, affiliation, or chain-of-command. |
| `conflict_with` | Subject attacked, defeated, or destroyed the Object in a military or armed-conflict context. Look for military aggression, battles, sinking, or surrender. |
| `military_involvement` | Subject is deployed in, or suffered casualties in, the Object (an Event or Place). Look for troop deployments, stationing, or persons killed/wounded in an Event. |
| `party_to_legal` | Subject signs, ratifies, issues, or is otherwise a party to the Object LegalDocument. Look for diplomatic or legal acts involving treaties, laws, decrees, or agreements. |
| `legal_governs` | Subject LegalDocument governs, regulates, or applies to the Object. The LegalDocument is about, or applies to, the Object entity. Look for "betreffende [Object]", "inzake [Object]". |
| `participates_in_event` | Subject participates in or organizes the Object Event. The Subject is actively involved in making the Event happen or taking part in it. Look for "deelnemer aan", "georganiseerd door". |
| `event_at_place` | Subject Event took place at, or was hosted by, the Object Place. The Event and Place are spatially linked. Direction-normalized: works in both (Event, Place) and (Place, Event) directions. |
| `mentions` | Subject mentions or references the Object, with no more specific relation holding. The Subject explicitly names or alludes to the Object, but no governance, conflict, legal, or participation relation applies. |
| `sports_relation` | Subject (Person or Organization) plays for, competes against, or won the Object (Person, Organization, or sports Event). Look for athletic competition, team membership, or match results. |
| `corporate_relation` | Subject Organization is corporately tied to the Object: listed on a stock exchange or headquartered there. Look for financial market listings or corporate locations. |
| `located_in` | Subject is physically located in, or is the capital of, the Object Place. Captures spatial containment and capital-city relations. |
| `reported` | Subject Organization (media outlet or broadcaster) reports on the Object Event. Look for "[Org] meldt", "[Org] deelt mede", "[Org] verneemt". |
| `no_relation` | No specific relation holds between the two entities. Use when entities co-occur but no defined relation applies. |

---

## Python Format with Descriptions

Here are the descriptions integrated into a Python dictionary format, ready for use in a JEV prompt or Pydantic schema:

```python
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
```

These descriptions are ready to be injected into a JEV prompt as definitions, helping the model understand exactly what linguistic signal to look for in the bulletin text when verifying a relation.