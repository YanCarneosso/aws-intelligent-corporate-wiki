from services.processing.normalization import normalize_text, split_preserving_boundaries


def test_normalization_removes_noise_without_flattening_paragraphs() -> None:
    text = " First   line \r\n\r\n\r\n Second\tline "
    assert normalize_text(text) == "First line\n\nSecond line"


def test_chunking_is_bounded_and_overlaps() -> None:
    text = "\n\n".join(["alpha " * 25, "beta " * 25, "gamma " * 25])
    chunks = split_preserving_boundaries(text, target_chars=180, overlap_chars=30)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 215 for chunk in chunks)
    assert "beta" in chunks[0] or "beta" in chunks[1]
