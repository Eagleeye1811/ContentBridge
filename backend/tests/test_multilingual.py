"""Audience and multilingual tests.

The property that matters: the same facts rendered into English, Hindi and
Marathi must reduce to the same canonical values, so the consistency checker
reports agreement across scripts rather than noise.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.schemas.content_ir import ContentIR, Node
from app.services.generation.audiences import (
    AUDIENCES,
    DEVANAGARI_LANGUAGES,
    LANGUAGES,
    get_audience,
    language_name,
)
from app.services.generation.formats import get_format
from app.services.generation.generator import _validate
from app.services.generation.prompt_builder import build_prompt
from app.services.sot.normalizer import canonical_date, canonical_number, normalize_digits
from app.services.verification.atomizer import atomize
from app.services.verification.claims import SYSTEM as JUDGE_SYSTEM
from app.services.verification.consistency import analyze
from app.services.verification.mentions import extract_mentions

# Devanagari fixtures, written out so the intent is readable.
DEV_37 = "३७"  # ३७
DEV_42 = "४२"  # ४२
DEV_DATE = "११ मार्च २०२६"  # ११ मार्च २०२६
DANDA = "।"


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


def para(text, fact_ids, **kw):
    return Node(id=kw.pop("id", "n1"), kind="paragraph", text=text, fact_ids=fact_ids)


def ir(*nodes, title="T"):
    return ContentIR(title=title, nodes=list(nodes))


# --- audiences -------------------------------------------------------------


def test_all_five_audiences_are_registered():
    assert set(AUDIENCES) == {"officer", "management", "technical", "public", "social"}


@pytest.mark.parametrize("key", sorted(AUDIENCES))
def test_each_audience_says_something_substantive(key):
    fragment = get_audience(key).prompt_fragment
    assert len(fragment) > 120, f"{key} profile is too thin to change anything"
    assert "Audience:" in fragment


def test_audience_profiles_are_distinct():
    fragments = {a.prompt_fragment for a in AUDIENCES.values()}
    assert len(fragments) == len(AUDIENCES)


@pytest.mark.parametrize("key", sorted(AUDIENCES))
def test_every_audience_is_told_not_to_change_the_facts(key):
    """Register may change; a figure may not."""
    assert "Never drop a figure" in get_audience(key).prompt_fragment


def test_public_and_technical_pull_in_opposite_directions():
    public = get_audience("public").prompt_fragment
    technical = get_audience("technical").prompt_fragment
    assert "no jargon" in public.lower()
    assert "terminology is expected" in technical.lower()


# --- language registry -----------------------------------------------------


def test_the_three_launch_languages():
    assert set(LANGUAGES) == {"en", "hi", "mr"}
    assert DEVANAGARI_LANGUAGES == {"hi", "mr"}
    assert language_name("mr").startswith("Marathi")


# --- normalization across scripts -----------------------------------------


def test_devanagari_digits_reduce_to_the_same_value():
    assert canonical_number(DEV_37) == canonical_number("37") == "37"
    assert normalize_digits(f"{DEV_37} accounts") == "37 accounts"


def test_devanagari_dates_reduce_to_iso():
    assert canonical_date(DEV_DATE) == "2026-03-11"
    assert canonical_date(DEV_DATE) == canonical_date("11 March 2026")


def test_mixed_script_dates_parse():
    marathi_month = "मार्च"
    assert canonical_date(f"11 {marathi_month} 2026") == "2026-03-11"


def test_mentions_found_in_devanagari_text():
    text = f"{DEV_37} खाते {DEV_DATE}"
    found = {m.canonical for m in extract_mentions(text)}
    assert "37" in found
    assert "2026-03-11" in found


# --- the multilingual consistency property ---------------------------------


def test_the_same_fact_agrees_across_all_three_languages():
    """The Phase 6 property: one source, three scripts, no mismatches."""
    fact = mkfact("creds", "37 user credentials were compromised.", "37")
    fid = str(fact.id)

    result = analyze(
        [fact],
        [
            ("advisory_en", ir(para("37 user credentials were compromised.", [fid]))),
            ("advisory_hi", ir(para(f"{DEV_37} खाते{DANDA}", [fid]))),
            ("advisory_mr", ir(para(f"{DEV_37} खाती{DANDA}", [fid]))),
        ],
    )

    assert result.mismatches == []
    assert {c.output_id: c.agrees for c in result.rows[0].cells} == {
        "advisory_en": True,
        "advisory_hi": True,
        "advisory_mr": True,
    }


def test_a_wrong_figure_is_caught_even_in_devanagari():
    """Normalization must not become a way to smuggle a wrong number through."""
    fact = mkfact("creds", "37 user credentials were compromised.", "37")
    fid = str(fact.id)

    result = analyze(
        [fact],
        [
            ("advisory_en", ir(para("37 credentials were compromised.", [fid]))),
            ("advisory_hi", ir(para(f"{DEV_42} खाते{DANDA}", [fid]))),
        ],
    )

    assert len(result.mismatches) == 1
    cells = {c.output_id: c.stated for c in result.mismatches[0].cells}
    assert cells == {"advisory_en": "37", "advisory_hi": "42"}


def test_devanagari_dates_agree_with_an_english_source():
    fact = mkfact("when", "Confirmed on 11 March 2026.", "2026-03-11", ftype="date")
    result = analyze(
        [fact],
        [
            ("en", ir(para("Confirmed on 11 March 2026.", [str(fact.id)]))),
            ("hi", ir(para(f"{DEV_DATE} को{DANDA}", [str(fact.id)]))),
        ],
    )
    assert result.mismatches == []


# --- atomizing Devanagari --------------------------------------------------


def test_danda_splits_devanagari_sentences():
    """Without this a Hindi paragraph arrives as one unverifiable claim."""
    hindi = f"{DEV_37} प्रमाण पत्र समाहित हुए{DANDA} सभी खाते रीसेट किए गए{DANDA}"
    claims = atomize(ir(para(hindi, ["f0"])))
    assert len(claims) == 2
    assert all(c.text.endswith(DANDA) for c in claims)


def test_danda_without_a_following_space_still_splits():
    hindi = f"पहला वाक्य यहाँ{DANDA}दूसरा वाक्य यहाँ{DANDA}"
    assert len(atomize(ir(para(hindi, ["f0"])))) == 2


def test_english_sentence_splitting_is_unchanged():
    claims = atomize(ir(para("37 were compromised. All were reset.", ["f0"])))
    assert [c.text for c in claims] == ["37 were compromised.", "All were reset."]


# --- script validation -----------------------------------------------------


ENGLISH_OUTPUT = ir(para("37 user credentials were compromised.", ["f0"]))
HINDI_OUTPUT = ir(para(f"{DEV_37} खाते समाहित{DANDA}", ["f0"]))


@pytest.mark.parametrize("language", ["hi", "mr"])
def test_english_text_requested_as_devanagari_is_rejected(language):
    """Shipping English labelled as Marathi is a silent failure worth catching."""
    problems = _validate(ENGLISH_OUTPUT, get_format("advisory"), {"f0"}, language)
    assert any("Devanagari" in p for p in problems)


@pytest.mark.parametrize("language", ["hi", "mr"])
def test_devanagari_text_passes_its_own_language_check(language):
    assert _validate(HINDI_OUTPUT, get_format("advisory"), {"f0"}, language) == []


def test_english_output_is_not_asked_for_devanagari():
    assert _validate(ENGLISH_OUTPUT, get_format("advisory"), {"f0"}, "en") == []


def test_script_check_ignores_an_empty_output():
    """An empty output fails for being empty, not for its script."""
    problems = _validate(ir(), get_format("advisory"), {"f0"}, "hi")
    assert not any("Devanagari" in p for p in problems)


# --- prompts ---------------------------------------------------------------


@pytest.mark.parametrize(("language", "expected"), [("hi", "Hindi"), ("mr", "Marathi")])
def test_prompt_requests_the_language_and_protects_figures(language, expected):
    prompt, _ = build_prompt(
        facts=[mkfact("creds", "37 credentials.", "37")],
        spec=get_format("advisory"),
        audience=get_audience("officer"),
        language=language,
        source_name="doc.pdf",
    )
    assert expected in prompt
    assert "Latin numerals" in prompt
    assert "proper nouns" in prompt


def test_english_prompt_has_no_script_instruction():
    prompt, _ = build_prompt(
        facts=[mkfact("creds", "37 credentials.", "37")],
        spec=get_format("advisory"),
        audience=get_audience("officer"),
        language="en",
        source_name="doc.pdf",
    )
    assert "Latin numerals" not in prompt


def test_the_judge_is_told_claims_may_be_in_another_language():
    assert "different languages" in JUDGE_SYSTEM
    assert "whatever script" in JUDGE_SYSTEM


def test_audience_fragment_reaches_the_prompt():
    prompt, _ = build_prompt(
        facts=[mkfact("creds", "37 credentials.", "37")],
        spec=get_format("linkedin"),
        audience=get_audience("public"),
        language="en",
        source_name="doc.pdf",
    )
    assert "member of the public" in prompt
