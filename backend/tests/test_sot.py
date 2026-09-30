"""Source-of-Truth tests.

The hallucinated-citation guard is the single most important behaviour in this
phase: a fact that cannot be traced to a real block must never reach the sheet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.services.indexing.chunker import chunk_blocks, estimate_tokens
from app.services.llm.stub import StubProvider
from app.services.sot.fact_extractor import (
    ExtractedFact,
    ExtractionResult,
    _dedupe,
    _locate,
    _render_excerpt,
    _resolve,
    extract_facts,
)
from app.services.sot.normalizer import (
    canonical_date,
    canonical_number,
    canonicalize,
    normalize_digits,
    slugify_key,
)


@dataclass
class FakeBlock:
    id: uuid.UUID
    page_no: int
    section_path: str
    order_idx: int
    text: str


def block(idx: int, text: str, section: str = "S", page: int = 1) -> FakeBlock:
    return FakeBlock(uuid.uuid4(), page, section, idx, text)


# --- normalizer ------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("37", "37"),
        ("1,234", "1234"),
        ("18.4 lakh", "1840000"),
        ("2 crore", "20000000"),
        ("1.2 million", "1200000"),
        ("62 percent", "62"),
        ("Rs 5,00,000", "500000"),
        ("३७", "37"),  # Devanagari 37
        ("no digits here", None),
    ],
)
def test_canonical_number(raw, expected):
    assert canonical_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("11 March 2026", "2026-03-11"),
        ("2026-03-11", "2026-03-11"),
        ("March 11, 2026", "2026-03-11"),
        ("11/03/2026", "2026-03-11"),  # day-first
        ("20 Mar 2026", "2026-03-20"),
        ("31 February 2026", None),  # invalid dates must not be invented
        ("sometime soon", None),
    ],
)
def test_canonical_date(raw, expected):
    assert canonical_date(raw) == expected


def test_devanagari_digits_compare_equal_to_source():
    """Hindi/Marathi outputs must reduce to the same value as the English source."""
    assert normalize_digits("३७ credentials") == "37 credentials"
    assert canonical_number("३७") == canonical_number("37")


def test_canonicalize_picks_up_units_the_model_omitted():
    value, unit = canonicalize(None, "MFA was enforced on only 62 percent of accounts.", "metric")
    assert (value, unit) == ("62", "percent")

    value, unit = canonicalize("18.4 lakh rupees", "Impact is 18.4 lakh rupees", "metric")
    assert (value, unit) == ("1840000", "currency")


def test_slugify_key():
    assert slugify_key("Credentials Compromised!") == "credentials_compromised"
    assert slugify_key("") == "fact"


# --- chunker ---------------------------------------------------------------


def test_chunks_never_cross_a_section_boundary():
    blocks = [
        block(0, "alpha text", "Findings"),
        block(1, "beta text", "Findings"),
        block(2, "gamma text", "Recommendations"),
    ]
    chunks = chunk_blocks(blocks)
    assert len(chunks) == 2
    assert chunks[0].section_path == "Findings"
    assert chunks[1].section_path == "Recommendations"
    # Overlap must not smuggle a block across the boundary.
    assert set(chunks[0].block_ids).isdisjoint(chunks[1].block_ids)


def test_chunks_respect_the_token_budget():
    blocks = [block(i, "word " * 200, "S") for i in range(6)]
    chunks = chunk_blocks(blocks, max_tokens=300, overlap_blocks=0)
    assert len(chunks) > 1
    assert all(c.token_count <= 400 for c in chunks)


def test_chunks_preserve_block_provenance():
    blocks = [block(i, f"text {i}", "S") for i in range(3)]
    chunks = chunk_blocks(blocks, max_tokens=10_000)
    assert len(chunks) == 1
    assert chunks[0].block_ids == [b.id for b in blocks]
    assert chunks[0].page_no == 1


def test_chunker_skips_blank_blocks():
    chunks = chunk_blocks([block(0, "   ", "S"), block(1, "real", "S")])
    assert len(chunks) == 1
    assert chunks[0].text == "real"


def test_estimate_tokens_is_never_zero():
    assert estimate_tokens("") >= 1


# --- citation guard --------------------------------------------------------


def _fact(**kw) -> ExtractedFact:
    base = dict(
        key="credentials_compromised",
        type="metric",
        statement="37 user credentials were compromised.",
        value="37",
        unit=None,
        evidence_block_ids=["b0"],
        confidence=0.9,
    )
    return ExtractedFact(**{**base, **kw})


def test_fact_citing_a_real_block_is_kept_and_canonicalized():
    b = block(0, "37 user credentials were compromised.", "Findings", page=3)
    _, id_map = _render_excerpt([b])

    resolved = _resolve(_fact(), id_map)

    assert resolved is not None
    assert resolved.canonical_value == "37"
    assert [e.block_id for e in resolved.evidence] == [b.id]


def test_fact_citing_an_invented_block_is_dropped():
    """The hallucination guard. A citation we cannot resolve kills the fact."""
    b = block(0, "37 user credentials were compromised.", "Findings")
    _, id_map = _render_excerpt([b])

    assert _resolve(_fact(evidence_block_ids=["b99"]), id_map) is None
    assert _resolve(_fact(evidence_block_ids=[]), id_map) is None
    assert _resolve(_fact(evidence_block_ids=["not-a-label"]), id_map) is None


def test_partially_invented_citations_keep_only_the_real_ones():
    b0 = block(0, "37 user credentials were compromised.", "Findings")
    b1 = block(1, "All 37 accounts were reset.", "Findings")
    _, id_map = _render_excerpt([b0, b1])

    resolved = _resolve(_fact(evidence_block_ids=["b0", "b42", "b1"]), id_map)

    assert resolved is not None
    assert {e.block_id for e in resolved.evidence} == {b0.id, b1.id}


def test_blank_statement_is_dropped():
    b = block(0, "text", "S")
    _, id_map = _render_excerpt([b])
    assert _resolve(_fact(statement="   "), id_map) is None


def test_excerpt_labels_are_short_and_unguessable_as_uuids():
    blocks = [block(i, f"text {i}", "S") for i in range(3)]
    excerpt, id_map = _render_excerpt(blocks)
    assert set(id_map) == {"b0", "b1", "b2"}
    assert "[b0]" in excerpt and 'section "S"' in excerpt
    # The real UUIDs must not be exposed to the model at all.
    assert all(str(b.id) not in excerpt for b in blocks)


def test_locate_returns_exact_offsets_when_the_statement_is_verbatim():
    text = "Preamble. 37 user credentials were compromised. Tail."
    quote, start, end = _locate("37 user credentials were compromised.", text)
    assert quote == "37 user credentials were compromised."
    assert text[start:end] == quote


def test_locate_falls_back_to_the_best_matching_sentence():
    text = "Unrelated opener. 37 user credentials were compromised across 4 offices."
    quote, _, _ = _locate("37 user credentials were compromised", text)
    assert "37 user credentials" in quote


def test_dedupe_merges_evidence_for_the_same_fact():
    b0 = block(0, "37 user credentials were compromised.", "Findings")
    b1 = block(1, "37 user credentials were compromised.", "Summary")
    _, map0 = _render_excerpt([b0])
    _, map1 = _render_excerpt([b1])

    merged = _dedupe([_resolve(_fact(), map0), _resolve(_fact(), map1)])

    assert len(merged) == 1
    assert {e.block_id for e in merged[0].evidence} == {b0.id, b1.id}


def test_dedupe_keeps_facts_that_disagree_on_value():
    b = block(0, "37 user credentials were compromised.", "Findings")
    _, id_map = _render_excerpt([b])
    merged = _dedupe([_resolve(_fact(value="37"), id_map), _resolve(_fact(value="42"), id_map)])
    # Different canonical values are different facts -- Phase 4 will flag them.
    assert len(merged) == 2


# --- end to end through the stub provider ----------------------------------


async def test_extract_facts_end_to_end_with_stub(monkeypatch):
    import app.services.llm as llm_module

    monkeypatch.setattr(llm_module, "get_llm", lambda: StubProvider())
    monkeypatch.setattr("app.services.sot.fact_extractor.get_llm", lambda: StubProvider())

    blocks = [
        block(0, "37 user credentials were compromised across 4 offices.", "Findings", page=3),
        block(1, "Logs were retained for 30 days against a 180 day policy.", "Findings", page=3),
    ]
    facts = await extract_facts(blocks)

    assert facts, "stub should produce facts"
    valid_ids = {b.id for b in blocks}
    for fact in facts:
        assert fact.evidence, "every fact must be cited"
        assert all(e.block_id in valid_ids for e in fact.evidence)
        assert fact.key


async def test_stub_returns_the_requested_schema():
    result = await StubProvider().complete_structured(
        system="",
        prompt='[b0] (page 1, section "S")\n37 user credentials were compromised.',
        schema=ExtractionResult,
    )
    assert isinstance(result, ExtractionResult)
    assert result.facts and result.facts[0].evidence_block_ids == ["b0"]
