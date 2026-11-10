
from dataclasses import dataclass, field

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------



@dataclass
class CandidateConfig:
    max_sentence_distance: int = 0           # 0 = same sentence, 1 = same or adjacent sentences
    max_character_distance: int = 200        # characters between the two mentions
    similarity_threshold: float = 0.85       # same type and a name at least this similar: same entity
    short_name_length: int = 4               # names up to this long must match exactly (after normalization)
    context_padding: int = 40                # characters added on both sides, snapped to word boundaries
    max_context_chars: int = 700             # a longer context is cut to a window around the two mentions
    skip_nested_same_type: bool = True
    max_pairs: int | None = None             # safety cap per bulletin


@dataclass
class DecisionConfig:
    min_probability: float = 0.5
    min_margin: float = 0.0


@dataclass
class PipelineConfig:
    level: str = "fine"                                   # "fine" | "coarse" | "category"
    candidate: CandidateConfig = field(default_factory=CandidateConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    max_questions_per_request: int = 20
    model: str = "jev-1.14.0" # "jev-latest"
    shared_instructions: bool = True                      # general instructions once in the state instead of in every question
    compact_options: bool = False                         # short option glosses + a relation glossary in the state (about half the request size)
    save_pairs: bool = True                               # keep the probabilities of every pair in the output
    merge_duplicates: bool = False                        # also write `relations_merged` (one record per entity pair)
    retries: int = 2
