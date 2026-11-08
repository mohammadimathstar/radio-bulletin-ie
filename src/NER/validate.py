from .models.entities import (
    PersonEntity,
    OrganizationEntity,
    PlaceEntity,
    EventEntity,
    VehicleEntity,
    LegalDocumentEntity,
)

ENTITY_MODELS = {
    "Person": PersonEntity,
    "Organization": OrganizationEntity,
    "Place": PlaceEntity,
    "Event": EventEntity,
    "Vehicle": VehicleEntity,
    "LegalDocument": LegalDocumentEntity,
}

# Fields that only make sense on Event entities. The API response schema allows
# them on every entity, so the model may emit them on non-Events; strip those.
EVENT_FIELDS = {
    "event_date",
    "event_time",
    "temporal_expression",
    "date_resolution",
    "time_resolution",
}


def validate_entity_types(entities: list[dict]) -> list[dict]:
    """Validate each entity with its specific Pydantic model.

    The parse schema (EntityStageItem) is deliberately flat — every entity
    carries every field, with the Event-only fields nullable — because OpenAI
    strict Structured Outputs rejects `oneOf`, so a discriminated union cannot
    be sent as the response schema. Here we re-validate each flat entity
    against its concrete model, stripping Event-only fields from non-Events.
    A model populating them on, say, a Person is a recoverable schema leak,
    not a reason to discard the whole bulletin.
    """
    validated = []
    for entity in entities:
        entity_type = entity.get("type")
        if entity_type not in ENTITY_MODELS:
            raise ValueError(f"Unknown entity type: {entity_type}")
        data = dict(entity)
        if entity_type != "Event":
            for key in EVENT_FIELDS:
                data.pop(key, None)
        parsed = ENTITY_MODELS[entity_type].model_validate(data)
        validated.append(parsed.model_dump(mode="json"))
    return validated


def validate_entity_mentions(text: str, entities: list[dict]):
    errors = []
    seen_ids = set()
    for e in entities:
        if e["id"] in seen_ids:
            errors.append(f"duplicate_entity_id:{e['id']}")
        seen_ids.add(e["id"])
        s, end = e["start"], e["end"]
        if s < 0 or end <= s or end > len(text):
            errors.append(f"invalid_entity_span:{e['id']}")
        elif text[s:end] != e["text"]:
            errors.append(f"entity_text_offset_mismatch:{e['id']}")
    return errors