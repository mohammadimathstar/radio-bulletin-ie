from dataclasses import dataclass
from typing import Optional


@dataclass
class Mention:
    """
    One entity mention detected by the NER pipeline.

    mention_id identifies the occurrence, not the real-world entity.
    Character offsets refer to the original bulletin text.
    """

    mention_id: str
    text: str
    entity_type: str
    start: int
    end: int

    # Assigned by spaCy after NER.
    sentence_id: Optional[int] = None


@dataclass
class CandidatePair:
    """
    A pair of distinct mentions eligible for relation classification.

    entity1 and entity2 are always kept in textual order.
    Semantic relation direction is determined separately by JEV.
    """

    pair_id: str
    entity1: Mention
    entity2: Mention

    # Compatible semantic relation types.
    candidate_relations: list[str]

    # Context boundaries in the original bulletin.
    context_start: int
    context_end: int


@dataclass
class ContextGroup:
    """
    Candidate pairs sharing the same text context.
    """

    context_id: str
    context_start: int
    context_end: int
    pairs: list[CandidatePair]


@dataclass
class JEVBatch:
    """
    A group of classification questions sent in one API request.
    """

    state: dict
    questions: dict
    option_maps: dict
    pair_metadata: dict