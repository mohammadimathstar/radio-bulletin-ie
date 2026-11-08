import re
import unicodedata
from difflib import SequenceMatcher
from bisect import bisect_left, bisect_right


_WS_RE = re.compile(r"\s+")
_NONWORD_RE = re.compile(r"[^\w\s]", re.UNICODE)


# ============================================================
# Normalization
# ============================================================

def _normalize_char(ch: str) -> str:
    """
    Normalize one character.

    - lowercase
    - strip accents
    - punctuation is removed
    - whitespace is represented as a space
    """

    if ch.isspace():
        return " "

    decomposed = unicodedata.normalize("NFKD", ch)

    base = "".join(
        c for c in decomposed
        if not unicodedata.combining(c)
    )

    base = base.lower()
    base = _NONWORD_RE.sub("", base)

    return base


def _normalize_text_with_map(text: str):
    """
    Normalize document text while maintaining a mapping from
    normalized character positions back to original character positions.

    Returns
    -------
    normalized_text : str

    orig_map : list[int]

        orig_map[i] gives the original-text character position
        corresponding to normalized_text[i].
    """

    norm_chars = []
    orig_map = []

    pending_space = None

    for i, ch in enumerate(text):

        if ch.isspace():

            if norm_chars and norm_chars[-1] != " ":
                pending_space = i

            continue

        normalized = _normalize_char(ch)

        if not normalized:
            continue

        if pending_space is not None:

            norm_chars.append(" ")
            orig_map.append(pending_space)

            pending_space = None

        norm_chars.append(normalized)
        orig_map.append(i)

    return "".join(norm_chars), orig_map


def _normalize_name(text: str) -> str:
    """
    Normalize an entity name.

    Unlike the document normalization, this function does not
    preserve original offsets.
    """

    norm_chars = []
    pending_space = False

    for ch in str(text):

        if ch.isspace() or ch == "\\":
            pending_space = bool(norm_chars)
            continue

        normalized = _normalize_char(ch)

        if not normalized:
            continue

        if pending_space:
            norm_chars.append(" ")
            pending_space = False

        norm_chars.append(normalized)

    return "".join(norm_chars).strip()


# ============================================================
# Helpers
# ============================================================

def _normalized_position(orig_map, original_position):
    """
    Approximate an original-text position in normalized space.
    """

    return bisect_left(
        orig_map,
        original_position
    )


def _map_norm_span_to_original(
    norm_start,
    norm_end,
    orig_map,
    original_text
):
    """
    Convert normalized [start, end) span into original-text offsets.
    """

    if not orig_map:
        return None

    if norm_start < 0:
        return None

    if norm_end <= norm_start:
        return None

    if norm_start >= len(orig_map):
        return None

    if norm_end - 1 >= len(orig_map):
        return None

    start = orig_map[norm_start]

    end = orig_map[norm_end - 1] + 1

    if start >= end:
        return None

    return (
        start,
        end,
        original_text[start:end]
    )


def _is_word_boundary(text, start, end):
    """
    Prevent matching inside a larger alphanumeric word.

    Example:
        'Obama' should not match the 'Obama' substring inside
        'Obama123'.
    """

    if start > 0 and text[start - 1].isalnum():
        return False

    if end < len(text) and text[end].isalnum():
        return False

    return True


# ============================================================
# Exact / normalized matching
# ============================================================

def _find_exact_matches(
    norm_ent,
    norm_text
):
    """
    Find all exact normalized occurrences.
    """

    matches = []

    pos = norm_text.find(norm_ent)

    while pos != -1:

        matches.append(
            (
                pos,
                pos + len(norm_ent)
            )
        )

        pos = norm_text.find(
            norm_ent,
            pos + 1
        )

    return matches


# ============================================================
# Fuzzy matching
# ============================================================

def _fuzzy_find(
    norm_ent,
    norm_text,
    min_ratio=0.90,
    lo=0,
    hi=None
):
    """
    Fuzzy search for norm_ent inside norm_text[lo:hi].

    Returns:
        {
            "start": ...,
            "end": ...,
            "score": ...
        }

    or None.
    """

    if hi is None:
        hi = len(norm_text)

    m = len(norm_ent)

    if m < 3:
        return None

    best = None
    best_ratio = 0.0

    # Allow modest boundary noise.
    window_sizes = range(
        max(3, m - 6),
        m + 7
    )

    for window_size in window_sizes:

        if window_size > hi - lo:
            continue

        for start in range(
            lo,
            hi - window_size + 1
        ):

            candidate = norm_text[
                start:start + window_size
            ]

            ratio = SequenceMatcher(
                None,
                norm_ent,
                candidate,
                autojunk=False
            ).ratio()

            if ratio < min_ratio:
                continue

            # Require word boundaries.
            if not _is_word_boundary(
                norm_text,
                start,
                start + window_size
            ):
                continue

            if ratio > best_ratio:

                best_ratio = ratio

                best = {
                    "start": start,
                    "end": start + window_size,
                    "score": ratio,
                }

                if ratio >= 0.999:
                    return best

    return best


# ============================================================
# Main correction
# ============================================================

def correct_llm_offsets(
    text,
    entities,
    fuzzy_threshold=0.90,
    window=150,
    min_fuzzy_length=5,
):
    """
    Correct and validate offsets of LLM-extracted entities.

    Matching strategy:

        1. exact raw text
        2. exact normalized text
        3. fuzzy matching near the LLM offset hint
        4. full-document fuzzy matching if no usable hint exists

    IMPORTANT:
        The original text slice is ALWAYS used as the final
        entity text.

    Each returned entity contains:

        text
        start
        end
        label
        offset_method
        offset_score

    If an entity cannot be located confidently, it is returned
    with:

        start = None
        end = None
        offset_method = "unresolved"
        offset_score = 0.0

    This makes it possible to decide later whether to drop it
    or attempt another recovery method.
    """

    if not text:
        return []

    norm_text, orig_map = (
        _normalize_text_with_map(text)
    )

    corrected = []

    for entity in entities:

        entity_text = str(
            entity.get("text", "")
        ).strip()

        if not entity_text:
            continue

        norm_entity = _normalize_name(
            entity_text
        )

        if len(norm_entity) < 3:
            corrected.append({
                **entity,
                "start": None,
                "end": None,
                "offset_method": "unresolved",
                "offset_score": 0.0,
            })
            continue

        # ----------------------------------------------------
        # 1. Exact raw-text match
        # ----------------------------------------------------

        raw_matches = []

        pos = text.find(entity_text)

        while pos != -1:

            raw_matches.append(
                (
                    pos,
                    pos + len(entity_text)
                )
            )

            pos = text.find(
                entity_text,
                pos + 1
            )

        if raw_matches:

            hint = entity.get("start")

            if (
                hint is not None
                and isinstance(hint, int)
                and 0 <= hint <= len(text)
            ):
                best = min(
                    raw_matches,
                    key=lambda span:
                    abs(span[0] - hint)
                )
            else:
                best = raw_matches[0]

            start, end = best

            corrected.append({
                **entity,
                "text": text[start:end],
                "start": start,
                "end": end,
                "offset_method": "exact_raw",
                "offset_score": 1.0,
            })

            continue

        # ----------------------------------------------------
        # 2. Exact normalized match
        # ----------------------------------------------------

        normalized_matches = _find_exact_matches(
            norm_entity,
            norm_text
        )

        if normalized_matches:

            hint = entity.get("start")

            if (
                hint is not None
                and isinstance(hint, int)
                and 0 <= hint <= len(text)
            ):

                norm_hint = (
                    _normalized_position(
                        orig_map,
                        hint
                    )
                )

                best = min(
                    normalized_matches,
                    key=lambda span:
                    abs(span[0] - norm_hint)
                )

            else:

                # No offset hint.
                #
                # If there is exactly one occurrence,
                # it is safe to use.
                #
                # If there are multiple occurrences,
                # do NOT arbitrarily choose one.
                if len(normalized_matches) > 1:

                    corrected.append({
                        **entity,
                        "start": None,
                        "end": None,
                        "offset_method": "ambiguous_exact",
                        "offset_score": 0.0,
                    })

                    continue

                best = normalized_matches[0]

            mapped = _map_norm_span_to_original(
                best[0],
                best[1],
                orig_map,
                text
            )

            if mapped is not None:

                start, end, original_slice = mapped

                corrected.append({
                    **entity,
                    "text": original_slice,
                    "start": start,
                    "end": end,
                    "offset_method": "exact_normalized",
                    "offset_score": 0.99,
                })

                continue

        # ----------------------------------------------------
        # 3. Fuzzy matching
        # ----------------------------------------------------

        hint = entity.get("start")

        usable_hint = (
            isinstance(hint, int)
            and 0 <= hint <= len(text)
        )

        if usable_hint:

            norm_hint = (
                _normalized_position(
                    orig_map,
                    hint
                )
            )

            lo = max(
                0,
                norm_hint - window
            )

            hi = min(
                len(norm_text),
                norm_hint
                + window
                + len(norm_entity)
                + 10
            )

        else:

            lo = 0
            hi = len(norm_text)

        # Short names are dangerous.
        # Do not fuzzy-match them aggressively.
        threshold = fuzzy_threshold

        if len(norm_entity) < min_fuzzy_length:
            threshold = max(
                threshold,
                0.95
            )

        fuzzy_hit = _fuzzy_find(
            norm_entity,
            norm_text,
            min_ratio=threshold,
            lo=lo,
            hi=hi,
        )

        if fuzzy_hit is not None:

            mapped = _map_norm_span_to_original(
                fuzzy_hit["start"],
                fuzzy_hit["end"],
                orig_map,
                text
            )

            if mapped is not None:

                start, end, original_slice = mapped

                corrected.append({
                    **entity,
                    "text": original_slice,
                    "start": start,
                    "end": end,
                    "offset_method": "fuzzy",
                    "offset_score": fuzzy_hit["score"],
                })

                continue

        # ----------------------------------------------------
        # 4. Could not confidently locate entity
        # ----------------------------------------------------

        corrected.append({
            **entity,
            "start": None,
            "end": None,
            "offset_method": "unresolved",
            "offset_score": 0.0,
        })

    return corrected