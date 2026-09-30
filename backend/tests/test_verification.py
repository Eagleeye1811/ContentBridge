"""Verification tests.

Layer 1 is the headline feature and runs live in front of an audience, so a
false alarm matters as much as a miss. Most of these tests exist to pin down
when the checker must stay quiet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.schemas.content_ir import ContentIR, Node
from app.services.verification.atomizer import atomize
from app.services.verification.claims import (
    ClaimVerdict,
    EvidenceRef,
    VerificationBatch,
    evidence_fingerprint,
    verify_claims,
)
from app.services.verification.consistency import analyze
from app.services.verification.mentions import extract_mentions
from app.services.verification.scoring import blocking_reasons, trust_score


@dataclass
class F:
    id: uuid.UUID
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None = None


def mkfact(key, statement, value, ftype="metric"):
    return F(uuid.uuid4(), key, ftype, statement, value)


def node(text, fact_ids, kind="paragraph", **kw):
    return Node(id=kw.pop("id", "n1"), kind=kind, text=text, fact_ids=fact_ids, **kw)


def ir(*nodes, title="T"):
    return ContentIR(title=title, nodes=list(nodes))


# --- mention extraction ----------------------------------------------------


def test_extracts_plain_numbers():
    got = {(m.canonical, m.kind) for m in extract_mentions("37 credentials across 4 offices.")}
    assert got == {("37", "number"), ("4", "number")}


def test_extracts_indian_scale_words():
    m = extract_mentions("The impact is 18.4 lakh rupees.")
    assert [x.canonical for x in m] == ["1840000"]


def test_extracts_devanagari_digits():
    assert [m.canonical for m in extract_mentions("३७ accounts")] == ["37"]


def test_dates_take_precedence_over_their_component_numbers():
    m = extract_mentions("Confirmed on 11 March 2026.")
    assert [(x.canonical, x.kind) for x in m] == [("2026-03-11", "date")]


@pytest.mark.parametrize(
    "text",
    [
        "Reference: CB/IR/2026/0412",  # reference code
        "Detection rule AUTH-114",  # alphanumeric identifier
        "Timestamp 02:14 IST",  # clock time
        "Offset UTC+05:30",  # timezone
        "Version v1.2.3 deployed",  # version string
    ],
)
def test_ambiguous_tokens_are_never_treated_as_checkable_figures(text):
    """A false alarm on demo day is worse than a missed one."""
    assert extract_mentions(text) == []


def test_percent_written_both_ways():
    assert [m.canonical for m in extract_mentions("62 percent")] == ["62"]
    assert [m.canonical for m in extract_mentions("62% coverage")] == ["62"]


def test_empty_text():
    assert extract_mentions("") == []


# --- layer 1: agreement ----------------------------------------------------


def test_matching_value_agrees():
    f = mkfact("creds", "37 credentials were compromised.", "37")
    result = analyze([f], [("a", ir(node("37 credentials were compromised.", [str(f.id)])))])
    assert len(result.rows) == 1
    assert result.rows[0].cells[0].agrees is True
    assert result.mismatches == []


def test_differing_value_is_a_mismatch():
    """The headline: source says 37, an output says 42."""
    f = mkfact("creds", "37 credentials were compromised.", "37")
    result = analyze([f], [("summary", ir(node("42 credentials were compromised.", [str(f.id)])))])
    assert len(result.mismatches) == 1
    cell = result.mismatches[0].cells[0]
    assert (cell.stated, cell.agrees) == ("42", False)


def test_the_cross_output_matrix():
    """37 / 37 / 42 across three outputs, from one comparison per cell."""
    f = mkfact("creds", "37 credentials were compromised.", "37")
    fid = str(f.id)
    result = analyze(
        [f],
        [
            ("advisory", ir(node("37 credentials were compromised.", [fid]))),
            ("ppt", ir(node("37 credentials compromised.", [fid]))),
            ("summary", ir(node("42 credentials were compromised.", [fid]))),
        ],
    )
    row = result.rows[0]
    by_output = {c.output_id: (c.stated, c.agrees) for c in row.cells}
    assert by_output == {
        "advisory": ("37", True),
        "ppt": ("37", True),
        "summary": ("42", False),
    }
    assert row.has_mismatch


def test_date_mismatch_is_caught():
    f = mkfact("when", "Confirmed on 11 March 2026.", "2026-03-11", ftype="date")
    result = analyze([f], [("email", ir(node("Confirmed on 12 March 2026.", [str(f.id)])))])
    assert result.mismatches[0].cells[0].stated == "2026-03-12"


def test_layer_one_uses_no_llm():
    """Pure computation: nothing here can fail on a flaky network."""
    f = mkfact("creds", "37 credentials.", "37")
    out = [("a", ir(node("37 credentials.", [str(f.id)])))]
    assert analyze([f], out).rows == analyze([f], out).rows


# --- layer 1: staying quiet ------------------------------------------------


def test_no_mismatch_when_attribution_is_ambiguous():
    """Two unaccounted figures: we cannot tell which was meant, so say nothing."""
    f1 = mkfact("creds", "37 credentials were compromised.", "37")
    f2 = mkfact("offices", "4 offices were affected.", "4")
    result = analyze(
        [f1, f2],
        [("a", ir(node("99 credentials across 88 offices.", [str(f1.id), str(f2.id)])))],
    )
    assert result.mismatches == []


def test_mismatch_attributed_when_only_one_figure_is_unaccounted():
    f1 = mkfact("creds", "37 credentials were compromised.", "37")
    f2 = mkfact("offices", "4 offices were affected.", "4")
    result = analyze(
        [f1, f2],
        [("a", ir(node("42 credentials across 4 offices.", [str(f1.id), str(f2.id)])))],
    )
    assert len(result.mismatches) == 1
    assert result.mismatches[0].key == "creds"
    assert result.mismatches[0].cells[0].stated == "42"


def test_value_hidden_inside_a_date_is_not_a_mismatch():
    """`11` inside `11 March 2026` is present, even though the date consumes it."""
    f = mkfact("day", "Containment on day 11.", "11")
    result = analyze([f], [("a", ir(node("11 March 2026 - containment confirmed.", [str(f.id)])))])
    assert result.mismatches == []


def test_value_hidden_inside_a_clock_time_is_not_a_mismatch():
    f = mkfact("hour", "Reset at hour 11.", "11")
    result = analyze([f], [("a", ir(node("Reset completed at 11:00 hours.", [str(f.id)])))])
    assert result.mismatches == []


def test_qualitative_sentence_citing_a_numeric_fact_is_not_a_mismatch():
    f = mkfact("creds", "37 credentials were compromised.", "37")
    result = analyze([f], [("a", ir(node("Credentials were compromised.", [str(f.id)])))])
    assert result.mismatches == []
    assert result.rows == []  # nothing stated, so nothing to show


def test_uncited_nodes_contribute_nothing():
    f = mkfact("creds", "37 credentials.", "37")
    assert analyze([f], [("a", ir(node("Some prose.", [])))]).rows == []


def test_facts_without_a_canonical_value_are_skipped():
    f = mkfact("advice", "Enforce multi-factor authentication.", None, ftype="recommendation")
    assert analyze([f], [("a", ir(node("Enforce MFA.", [str(f.id)])))]).rows == []


# --- layer 1: unsourced figures -------------------------------------------


def test_invented_figure_is_reported_as_unsourced():
    f = mkfact("creds", "37 credentials were compromised.", "37")
    result = analyze(
        [f], [("a", ir(node("37 credentials were compromised, costing 99 crore.", [str(f.id)])))]
    )
    assert [(u.output_id, u.value) for u in result.unsourced] == [("a", "990000000")]


def test_a_figure_present_in_the_fact_statement_is_sourced():
    f = mkfact("creds", "37 credentials across 4 offices.", "37")
    result = analyze([f], [("a", ir(node("37 credentials across 4 offices.", [str(f.id)])))])
    assert result.unsourced == []


def test_unsourced_is_reported_once_per_output():
    f = mkfact("creds", "37 credentials.", "37")
    result = analyze(
        [f],
        [
            (
                "a",
                ir(
                    node("37 credentials and 99 others.", [str(f.id)], id="n1"),
                    node("Again 99 others.", [str(f.id)], id="n2"),
                ),
            )
        ],
    )
    assert len([u for u in result.unsourced if u.value == "99"]) == 1


# --- atomizer --------------------------------------------------------------


def test_headings_are_not_claims():
    assert atomize(ir(Node(id="n0", kind="heading", text="Background", level=2))) == []


def test_paragraph_splits_into_sentences():
    claims = atomize(ir(node("37 were compromised. All were reset.", ["f"])))
    assert [c.text for c in claims] == ["37 were compromised.", "All were reset."]


def test_each_bullet_is_a_claim():
    claims = atomize(
        ir(
            Node(
                id="n1",
                kind="bullets",
                items=["Enforce MFA everywhere", "Extend retention to 180 days"],
                fact_ids=["f"],
            )
        )
    )
    assert len(claims) == 2


def test_table_header_row_is_skipped():
    claims = atomize(
        ir(
            Node(
                id="n1",
                kind="table",
                rows=[["Metric", "Value"], ["Credentials compromised", "37"]],
                fact_ids=["f"],
            )
        )
    )
    assert len(claims) == 1
    assert "37" in claims[0].text


def test_claims_carry_their_node_and_citations():
    claims = atomize(ir(node("37 credentials were compromised.", ["fa", "fb"], id="n7")))
    assert claims[0].node_id == "n7"
    assert claims[0].fact_ids == ["fa", "fb"]


def test_very_short_fragments_are_not_claims():
    assert atomize(ir(node("Yes.", ["f"]))) == []


# --- scoring ---------------------------------------------------------------


def test_trust_score_rewards_support_and_punishes_contradiction():
    assert trust_score(["supported"] * 4) == 1.0
    assert trust_score(["contradicted"] * 4) == 0.0
    assert 0.0 < trust_score(["supported", "contradicted"]) < 1.0


def test_open_issues_reduce_trust():
    assert trust_score(["supported"], open_high_issues=2) == 0.8


def test_trust_score_is_floored_at_zero():
    assert trust_score(["contradicted"], open_high_issues=5) == 0.0


def test_no_claims_means_no_trust():
    assert trust_score([]) == 0.0


def test_contradiction_blocks_approval():
    assert blocking_reasons(["supported", "contradicted"]) == ["1 claim contradicted by the source"]


def test_open_high_severity_issue_blocks_approval():
    reasons = blocking_reasons(["supported"], open_high_issues=1)
    assert reasons == ["1 unresolved high-severity consistency issue"]


def test_clean_output_is_approvable():
    assert blocking_reasons(["supported", "partial"]) == []


# --- layer 2 plumbing ------------------------------------------------------


class FakeJudge:
    name = "fake"

    def __init__(self, *, omit: set[int] = frozenset()):
        self.omit = omit
        self.prompts: list[str] = []

    async def complete_structured(self, *, system, prompt, schema, temperature=None):
        self.prompts.append(prompt)
        import re

        verdicts = [
            ClaimVerdict(
                claim_number=int(n),
                verdict="supported",
                score=0.9,
                rationale="ok",
                supporting_labels=[f"e{n}.0"],
            )
            for n in re.findall(r"^CLAIM (\d+):", prompt, re.MULTILINE)
            if int(n) not in self.omit
        ]
        return VerificationBatch(verdicts=verdicts)


def _evidence():
    return [
        EvidenceRef(
            block_id=uuid.uuid4(), text="37 credentials.", page_no=3, section_path="Findings"
        )
    ]


async def test_claims_are_adjudicated_against_their_evidence(monkeypatch):
    judge = FakeJudge()
    monkeypatch.setattr("app.services.verification.claims.get_llm", lambda: judge)

    claims = atomize(ir(node("37 credentials were compromised.", ["f0"])))
    results = await verify_claims(claims, lambda c: _async(_evidence()))

    assert [r.verdict for r in results] == ["supported"]
    assert "CLAIM 1:" in judge.prompts[0]
    assert "[e1.0]" in judge.prompts[0]


async def test_a_claim_the_model_skips_is_not_silently_passed(monkeypatch):
    """A missing verdict must never read as support."""
    monkeypatch.setattr("app.services.verification.claims.get_llm", lambda: FakeJudge(omit={1}))
    claims = atomize(ir(node("37 credentials were compromised.", ["f0"])))
    results = await verify_claims(claims, lambda c: _async(_evidence()))
    assert results[0].verdict == "unsupported"
    assert results[0].score == 0.0


async def test_no_claims_means_no_llm_call(monkeypatch):
    judge = FakeJudge()
    monkeypatch.setattr("app.services.verification.claims.get_llm", lambda: judge)
    assert await verify_claims([], lambda c: _async([])) == []
    assert judge.prompts == []


def test_fingerprint_changes_with_text_and_evidence():
    ev = _evidence()
    base = evidence_fingerprint("claim", ev)
    assert base == evidence_fingerprint("claim", ev)
    assert base != evidence_fingerprint("other claim", ev)
    assert base != evidence_fingerprint("claim", ev + _evidence())


async def _async(value):
    return value


# --- issue identity --------------------------------------------------------


def _identity(kind, fact_id, expected, observed):
    """Mirror of the identity function in the persistence layer.

    Regression guard: read and write once used different keys for unsourced
    figures, so accepting an issue was silently undone by the next run.
    """
    if kind == "unsourced_number":
        return (kind, tuple(sorted((observed or {}).items())))
    return (kind, str(fact_id), expected)


def test_unsourced_issue_identity_is_stable_across_runs():
    observed = {"out-1": "42"}
    first = _identity("unsourced_number", None, None, observed)
    second = _identity("unsourced_number", None, None, dict(observed))
    assert first == second


def test_unsourced_issues_with_different_values_are_different_issues():
    assert _identity("unsourced_number", None, None, {"a": "42"}) != _identity(
        "unsourced_number", None, None, {"a": "99"}
    )


def test_value_mismatch_identity_tracks_fact_and_expected():
    fid = uuid.uuid4()
    assert _identity("value_mismatch", fid, "37", {}) == _identity("value_mismatch", fid, "37", {})
    assert _identity("value_mismatch", fid, "37", {}) != _identity("value_mismatch", fid, "42", {})
