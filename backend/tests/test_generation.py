"""Generation tests.

The value of one shared generator is that these guarantees hold for every
output type at once: nothing unattributable reaches a reviewer, and renderers
are pure functions of ContentIR.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.schemas.content_ir import ContentIR, Node, iter_text, node_word_count
from app.services.generation.audiences import UnknownAudience, get_audience, language_name
from app.services.generation.formats import FORMATS, UnknownFormat, get_format
from app.services.generation.generator import (
    GenerationError,
    _sanitize,
    _validate,
    generate,
)
from app.services.generation.prompt_builder import build_prompt, render_facts
from app.services.rendering import UnknownRenderer, render


@dataclass
class FakeFact:
    id: uuid.UUID
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None


def fact(statement="37 user credentials were compromised.", value="37", unit=None):
    return FakeFact(uuid.uuid4(), "credentials", "metric", statement, value, unit)


FACTS = [
    fact(),
    fact("MFA covered only 62 percent of accounts.", "62", "percent"),
    fact("The intrusion was confirmed on 11 March 2026.", "2026-03-11"),
]


class ScriptedProvider:
    """Returns a queued list of ContentIR payloads, one per call."""

    name = "scripted"

    def __init__(self, *payloads: dict) -> None:
        self.payloads = list(payloads)
        self.calls: list[str] = []

    async def complete_structured(self, *, system, prompt, schema, temperature=None):
        self.calls.append(prompt)
        payload = self.payloads.pop(0) if self.payloads else self.payloads
        return schema.model_validate(payload)


def use(provider, monkeypatch):
    monkeypatch.setattr("app.services.generation.generator.get_llm", lambda: provider)


# --- registries ------------------------------------------------------------


def test_format_registry_exposes_the_phase_three_formats():
    assert {"advisory", "summary"} <= set(FORMATS)
    assert get_format("advisory").allowed_kinds
    with pytest.raises(UnknownFormat):
        get_format("hologram")


def test_audience_registry():
    assert get_audience("officer").prompt_fragment
    with pytest.raises(UnknownAudience):
        get_audience("martian")
    assert language_name("mr").startswith("Marathi")


# --- prompt ----------------------------------------------------------------


def test_facts_are_labelled_and_real_ids_are_never_shown():
    rendered, label_map = render_facts(FACTS)
    assert set(label_map) == {"f0", "f1", "f2"}
    assert "[f0]" in rendered and "value=37" in rendered
    # A model that never sees a UUID cannot invent a valid one.
    assert all(str(f.id) not in rendered for f in FACTS)


def test_prompt_states_the_constraints_the_validator_enforces():
    spec = get_format("advisory")
    prompt, _ = build_prompt(
        facts=FACTS,
        spec=spec,
        audience=get_audience("officer"),
        language="en",
        source_name="incident_report.pdf",
    )
    assert "Allowed node kinds:" in prompt
    assert f"Maximum nodes: {spec.max_nodes}" in prompt
    assert "incident_report.pdf" in prompt


def test_non_english_prompt_protects_digits_and_proper_nouns():
    prompt, _ = build_prompt(
        facts=FACTS,
        spec=get_format("advisory"),
        audience=get_audience("public"),
        language="mr",
        source_name="doc.pdf",
    )
    assert "Marathi" in prompt
    assert "Latin numerals" in prompt


def test_violations_are_fed_back_verbatim_on_retry():
    prompt, _ = build_prompt(
        facts=FACTS,
        spec=get_format("advisory"),
        audience=get_audience("officer"),
        language="en",
        source_name="doc.pdf",
        violations=["Node 'n1' cited 'f99'"],
    )
    assert "previous attempt was rejected" in prompt
    assert "Node 'n1' cited 'f99'" in prompt


# --- validation ------------------------------------------------------------


def _ir(*nodes: dict, title="T") -> ContentIR:
    return ContentIR(title=title, nodes=[Node(**n) for n in nodes])


def test_validate_accepts_a_well_formed_output():
    spec = get_format("advisory")
    ir = _ir(
        {"id": "n0", "kind": "heading", "text": "Impact", "level": 2},
        {"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f0"]},
    )
    assert _validate(ir, spec, {"f0", "f1"}) == []


def test_validate_rejects_a_disallowed_node_kind():
    # A summary may not contain slides.
    ir = _ir({"id": "n1", "kind": "slide", "title": "S", "fact_ids": ["f0"]})
    problems = _validate(ir, get_format("summary"), {"f0"})
    assert any("not allowed" in p for p in problems)


def test_validate_rejects_an_invented_citation():
    ir = _ir({"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f99"]})
    problems = _validate(ir, get_format("advisory"), {"f0"})
    assert any("do not exist" in p for p in problems)


def test_validate_rejects_an_uncited_non_heading_node():
    ir = _ir({"id": "n1", "kind": "paragraph", "text": "Unattributed claim."})
    problems = _validate(ir, get_format("advisory"), {"f0"})
    assert any("cited no facts" in p for p in problems)


def test_validate_allows_an_uncited_heading():
    """Headings are navigation, not claims."""
    ir = _ir({"id": "n0", "kind": "heading", "text": "Background", "level": 2})
    assert _validate(ir, get_format("advisory"), {"f0"}) == []


def test_validate_rejects_too_many_nodes():
    spec = get_format("summary")
    ir = _ir(
        *[
            {"id": f"n{i}", "kind": "paragraph", "text": "x", "fact_ids": ["f0"]}
            for i in range(spec.max_nodes + 3)
        ]
    )
    assert any("at most" in p for p in _validate(ir, spec, {"f0"}))


def test_validate_flags_an_empty_output():
    assert _validate(_ir(), get_format("advisory"), {"f0"})


# --- sanitize --------------------------------------------------------------


def _label_map(facts=FACTS) -> dict:
    return {f"f{i}": f for i, f in enumerate(facts)}


def test_sanitize_remaps_labels_to_real_fact_ids():
    ir = _ir({"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f0"]})
    cleaned, dropped = _sanitize(ir, get_format("advisory"), _label_map())
    assert dropped == []
    assert cleaned.nodes[0].fact_ids == [str(FACTS[0].id)]


def test_sanitize_drops_a_node_whose_only_citation_is_invented():
    """The last line of defence: an unattributable claim never reaches review."""
    ir = _ir({"id": "n1", "kind": "paragraph", "text": "Invented.", "fact_ids": ["f99"]})
    cleaned, dropped = _sanitize(ir, get_format("advisory"), _label_map())
    assert cleaned.nodes == []
    assert any("no resolvable citation" in d for d in dropped)


def test_sanitize_keeps_the_real_citations_of_a_partly_invented_node():
    ir = _ir({"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f0", "f99", "f1"]})
    cleaned, dropped = _sanitize(ir, get_format("advisory"), _label_map())
    assert cleaned.nodes[0].fact_ids == [str(FACTS[0].id), str(FACTS[1].id)]
    assert any("f99" in d for d in dropped)


def test_sanitize_drops_disallowed_kinds():
    ir = _ir({"id": "n1", "kind": "slide", "title": "S", "fact_ids": ["f0"]})
    cleaned, dropped = _sanitize(ir, get_format("summary"), _label_map())
    assert cleaned.nodes == []
    assert any("disallowed kind" in d for d in dropped)


def test_sanitize_makes_node_ids_unique():
    ir = _ir(
        {"id": "n1", "kind": "paragraph", "text": "A", "fact_ids": ["f0"]},
        {"id": "n1", "kind": "paragraph", "text": "B", "fact_ids": ["f1"]},
    )
    cleaned, _ = _sanitize(ir, get_format("advisory"), _label_map())
    ids = [n.id for n in cleaned.nodes]
    assert len(ids) == len(set(ids))


def test_sanitize_keeps_an_uncited_heading():
    ir = _ir({"id": "n0", "kind": "heading", "text": "Background", "level": 2})
    cleaned, _ = _sanitize(ir, get_format("advisory"), _label_map())
    assert len(cleaned.nodes) == 1


# --- generate --------------------------------------------------------------


async def test_generate_retries_once_when_the_first_attempt_is_invalid(monkeypatch):
    bad = {
        "title": "T",
        "nodes": [{"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f99"]}],
    }
    good = {
        "title": "T",
        "nodes": [{"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f0"]}],
    }
    provider = ScriptedProvider(bad, good)
    use(provider, monkeypatch)

    result = await generate(
        facts=FACTS,
        spec=get_format("advisory"),
        audience=get_audience("officer"),
        language="en",
        source_name="doc.pdf",
    )

    assert result.attempts == 2
    assert len(provider.calls) == 2
    # The retry must name the violation so the model can act on it.
    assert "previous attempt was rejected" in provider.calls[1]
    assert result.content_ir.nodes[0].fact_ids == [str(FACTS[0].id)]


async def test_generate_sanitizes_when_the_retry_also_misbehaves(monkeypatch):
    bad = {
        "title": "T",
        "nodes": [
            {"id": "n1", "kind": "paragraph", "text": "Grounded.", "fact_ids": ["f0"]},
            {"id": "n2", "kind": "paragraph", "text": "Invented.", "fact_ids": ["f99"]},
        ],
    }
    use(ScriptedProvider(bad, bad), monkeypatch)

    result = await generate(
        facts=FACTS,
        spec=get_format("advisory"),
        audience=get_audience("officer"),
        language="en",
        source_name="doc.pdf",
    )

    texts = [n.text for n in result.content_ir.nodes]
    assert "Grounded." in texts
    assert "Invented." not in texts
    assert result.dropped_citations


async def test_generate_refuses_when_nothing_is_attributable(monkeypatch):
    bad = {
        "title": "T",
        "nodes": [{"id": "n1", "kind": "paragraph", "text": "All invented.", "fact_ids": ["f99"]}],
    }
    use(ScriptedProvider(bad, bad), monkeypatch)

    with pytest.raises(GenerationError, match="attributable"):
        await generate(
            facts=FACTS,
            spec=get_format("advisory"),
            audience=get_audience("officer"),
            language="en",
            source_name="doc.pdf",
        )


async def test_generate_refuses_an_empty_source_of_truth():
    with pytest.raises(GenerationError, match="empty Source of Truth"):
        await generate(
            facts=[],
            spec=get_format("advisory"),
            audience=get_audience("officer"),
            language="en",
            source_name="doc.pdf",
        )


def _payload_for(spec):
    """A minimal valid node for whatever kinds this format allows."""
    kind = spec.allowed_kinds[0]
    node = {"id": "n1", "kind": kind, "fact_ids": ["f0"]}
    if kind in {"bullets", "post"}:
        node["items"] = ["A grounded point"]
    elif kind == "slide":
        node["title"] = "Overview"
        node["items"] = ["A grounded point"]
    elif kind == "table":
        node["rows"] = [["Metric", "Value"], ["Accounts", "37"]]
    else:
        node["text"] = "Body."
    return {"title": "T", "nodes": [node]}


async def test_one_generator_serves_every_format(monkeypatch):
    """The point of the architecture: same call, different FormatSpec."""
    for key, spec in FORMATS.items():
        payload = _payload_for(spec)
        use(ScriptedProvider(payload, payload), monkeypatch)
        result = await generate(
            facts=FACTS,
            spec=spec,
            audience=get_audience("officer"),
            language="en",
            source_name="doc.pdf",
        )
        assert result.content_ir.nodes, key
        assert result.content_ir.nodes[0].kind in spec.allowed_kinds


async def test_a_format_rejects_node_kinds_it_does_not_allow(monkeypatch):
    """A deck may not contain paragraphs: the FormatSpec is enforced, not advisory."""
    paragraph = {
        "title": "T",
        "nodes": [{"id": "n1", "kind": "paragraph", "text": "Body.", "fact_ids": ["f0"]}],
    }
    use(ScriptedProvider(paragraph, paragraph), monkeypatch)
    with pytest.raises(GenerationError):
        await generate(
            facts=FACTS,
            spec=get_format("ppt"),
            audience=get_audience("officer"),
            language="en",
            source_name="doc.pdf",
        )


# --- renderers -------------------------------------------------------------


FULL_IR = ContentIR(
    title="Advisory",
    nodes=[
        Node(
            id="n0",
            kind="callout",
            title="High severity",
            text="Credentials exposed.",
            severity="high",
            fact_ids=["x"],
        ),
        Node(id="n1", kind="heading", text="Impact", level=2),
        Node(id="n2", kind="paragraph", text="37 credentials were compromised.", fact_ids=["x"]),
        Node(id="n3", kind="bullets", items=["Enforce MFA", "Extend retention"], fact_ids=["x"]),
        Node(id="n4", kind="table", rows=[["Metric", "Value"], ["Accounts", "37"]], fact_ids=["x"]),
        Node(id="n5", kind="quote", text="Contained within 6 hours.", fact_ids=["x"]),
        Node(
            id="n6",
            kind="slide",
            title="Overview",
            items=["37 credentials"],
            notes="Speak slowly",
            fact_ids=["x"],
        ),
    ],
)


def test_markdown_renders_every_node_kind():
    out = render(FULL_IR, "markdown")
    assert out.startswith("# Advisory")
    assert "## Impact" in out
    assert "- Enforce MFA" in out
    assert "| Metric | Value |" in out
    assert "> **High severity**" in out
    assert "> Contained within 6 hours." in out
    assert "### Overview" in out


def test_text_renders_every_node_kind():
    out = render(FULL_IR, "text")
    assert "Advisory" in out
    assert "* Enforce MFA" in out
    assert "[High severity]" in out


def test_renderers_are_pure_functions():
    """Export must be reproducible: no LLM call, no hidden state."""
    assert render(FULL_IR, "markdown") == render(FULL_IR, "markdown")
    assert render(FULL_IR, "text") == render(FULL_IR, "text")


def test_citation_annotation_is_opt_in():
    assert "<!-- facts:" not in render(FULL_IR, "markdown")
    assert "<!-- facts: x -->" in render(FULL_IR, "markdown", include_citations=True)


def test_unknown_renderer_is_rejected():
    with pytest.raises(UnknownRenderer):
        render(FULL_IR, "hologram")


def test_markdown_skips_empty_nodes():
    ir = ContentIR(title="T", nodes=[Node(id="n1", kind="bullets", items=[], fact_ids=["x"])])
    assert render(ir, "markdown").strip() == "# T"


# --- content ir helpers ----------------------------------------------------


def test_iter_text_collects_every_string_for_verification():
    node = FULL_IR.nodes[6]
    texts = iter_text(node)
    assert "Overview" in texts and "37 credentials" in texts and "Speak slowly" in texts


def test_node_word_count():
    assert node_word_count(FULL_IR) > 20
