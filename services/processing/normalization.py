"""Conservative text normalization that preserves evidence boundaries."""

from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    compact: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line
        if blank and previous_blank:
            continue
        compact.append(line)
        previous_blank = blank
    return "\n".join(compact).strip()


def split_preserving_boundaries(
    text: str, *, target_chars: int = 2_800, overlap_chars: int = 420
) -> list[str]:
    """Split at paragraphs/lines with bounded overlap (about 700/105 tokens in Portuguese)."""
    if target_chars <= 0 or not 0 <= overlap_chars < target_chars:
        raise ValueError("invalid chunking configuration")
    normalized = normalize_text(text)
    if not normalized:
        return []
    blocks = [block.strip() for block in re.split(r"\n{2,}", normalized) if block.strip()]
    if len(blocks) == 1:
        blocks = [line for line in normalized.splitlines() if line]

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for block in _bounded_blocks(blocks, target_chars):
        separator_size = 2 if current else 0
        if current and current_size + separator_size + len(block) > target_chars:
            completed = "\n\n".join(current)
            chunks.append(completed)
            overlap = _tail(completed, overlap_chars)
            current = [overlap, block] if overlap else [block]
            current_size = sum(map(len, current)) + 2 * (len(current) - 1)
        else:
            current.append(block)
            current_size += separator_size + len(block)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _bounded_blocks(blocks: list[str], maximum: int) -> list[str]:
    bounded: list[str] = []
    for block in blocks:
        remainder = block
        while len(remainder) > maximum:
            cut = remainder.rfind(" ", 0, maximum)
            cut = cut if cut >= maximum // 2 else maximum
            bounded.append(remainder[:cut].strip())
            remainder = remainder[cut:].strip()
        if remainder:
            bounded.append(remainder)
    return bounded


def _tail(text: str, size: int) -> str:
    if not size or len(text) <= size:
        return text if size else ""
    tail = text[-size:]
    first_space = tail.find(" ")
    return tail[first_space + 1 :] if first_space >= 0 else tail
