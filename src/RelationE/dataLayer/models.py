"""Data classes of the relation pipeline. Plain dataclasses; nothing here depends on JEV."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Mention:
    """One entity mention from the NER output. mention_id identifies the occurrence, not the real-world entity. Offsets refer to the bulletin text."""
    mention_id: str
    text: str
    entity_type: str
    start: int
    end: int
    normalized_name: Optional[str] = None
    confidence: Optional[float] = None
    sentence_id: Optional[int] = None          # assigned after sentence segmentation


@dataclass
class Bulletin:
    bulletin_id: str
    date: Optional[str]
    text: str
    mentions: list[Mention]
    load_stats: dict[str, int] = field(default_factory=dict)      # what was dropped or repaired while loading


@dataclass
class CandidatePair:
    """Two distinct mentions that may be related. entity1 is the earlier one in the text; the semantic direction is decided by the classifier."""
    pair_id: str
    entity1: Mention
    entity2: Mention
    candidate_relations: list[str]
    context_start: int
    context_end: int
    sentence_distance: Optional[int] = None
    character_distance: int = 0


@dataclass
class ContextGroup:
    """Candidate pairs that share the same text context (shown once in the JEV state)."""
    context_id: str
    context_start: int
    context_end: int
    pairs: list[CandidatePair]


@dataclass
class JEVBatch:
    """A group of questions sent in one request."""
    state: dict[str, Any]
    questions: dict[str, Any]
    option_maps: dict[str, dict[str, dict[str, Any]]]
    pair_metadata: dict[str, dict[str, Any]]


@dataclass
class PairPrediction:
    """JEV's answer for one pair, before any decision rule."""
    pair_id: str
    context_id: str
    entity1: str
    entity2: str
    selected_option: str
    confidence: float                                  # JEV's own confidence in the selected option
    probabilities: dict[str, float]                    # over ALL options (directional options, symmetric ones, no_relation)
    option_map: dict[str, dict[str, Any]]              # option -> {relation, head, tail}
