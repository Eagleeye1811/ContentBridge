"""PS 26154 alignment: communication controls, the LinkedIn / infographic /
video packages, and text and image sources.

Everything here rides the existing spine. These tests pin that down: the new
outputs come out of the same generator, the new sources come out as the same
blocks, and nothing new can carry an unverified claim past the checks.
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass

import pytest

from app.schemas.content_ir import ContentIR, Node
from app.services.generation.audiences import get_audience
from app.services.generation.controls import (
    CONTROL_REGISTRIES,
    DEFAULT_CONTROLS,
    UnknownControl,
    control_fragments,
    resolve_controls,
)
from app.services.generation.formats import get_format
from app.services.generation.generator import generate
from app.services.generation.prompt_builder import build_prompt
from app.services.ingestion import SUPPORTED, mime_for, parse_document
from app.services.ingestion.image import parse_tsv
from app.services.llm.stub import StubProvider
from app.services.rendering import render_bytes, render_text
from app.services.rendering.srt import cues_for, estimate_seconds
from app.services.verification.atomizer import atomize


@dataclass
class FakeFact:
    id: uuid.UUID
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None


FACTS = [
    FakeFact(uuid.uuid4(), "creds", "metric", "37 staff credentials were compromised.", "37", None),
    FakeFact(uuid.uuid4(), "mfa", "metric", "MFA covered only 62 percent of accounts.", "62", "%"),
    FakeFact(
        uuid.uuid4(), "date", "date", "The intrusion was confirmed on 11 March 2026.", None, None
    ),
]


def _prompt(**controls: str) -> str:
    prompt, _ = build_prompt(
        facts=FACTS,
        spec=get_format("advisory"),
        audience=get_audience("officer"),
        language="en",
        source_name="incident_report.pdf",
        controls=controls or None,
    )
    return prompt


# --- communication controls -------------------------------------------------


def test_defaults_fill_every_dimension():
    assert resolve_controls(None) == DEFAULT_CONTROLS
    assert set(DEFAULT_CONTROLS) == {"tone", "detail_level", "objective", "style"}


def test_every_default_exists_in_its_registry():
    for name, value in DEFAULT_CONTROLS.items():
        assert value in CONTROL_REGISTRIES[name]


def test_partial_controls_keep_the_other_defaults():
    resolved = resolve_controls({"tone": "urgent"})
    assert resolved["tone"] == "urgent"
    assert resolved["style"] == DEFAULT_CONTROLS["style"]


@pytest.mark.parametrize(
    "values", [{"tone": "sarcastic"}, {"mood": "formal"}, {"detail_level": "epic"}]
)
def test_unknown_controls_are_rejected(values):
    with pytest.raises(UnknownControl):
        resolve_controls(values)


def test_every_option_has_a_prompt_fragment():
    for registry in CONTROL_REGISTRIES.values():
        for option in registry.values():
            assert option.prompt_fragment.strip() and option.description.strip()


def test_controls_reach_the_prompt():
    prompt = _prompt(tone="urgent", detail_level="brief", objective="instruct", style="narrative")
    assert "Tone: urgent" in prompt
    assert "Detail level: brief" in prompt
    assert "Communication objective: instruct" in prompt
    assert "Content style: narrative" in prompt


def test_controls_never_displace_the_hard_rules():
    prompt = _prompt(tone="conversational")
    assert "the hard rules above still apply" in prompt
    assert "Allowed node kinds:" in prompt


def test_one_fragment_per_dimension():
    assert len(control_fragments({"tone": "neutral"})) == len(CONTROL_REGISTRIES)


# --- new output types through the one generator ------------------------------


@pytest.fixture
def stub(monkeypatch):
    monkeypatch.setattr("app.services.generation.generator.get_llm", lambda: StubProvider())


@pytest.mark.parametrize(
    ("key", "kind"), [("linkedin", "post"), ("infographic", "panel"), ("video", "scene")]
)
async def test_new_types_come_out_of_the_same_generator(stub, key, kind):
    result = await generate(
        facts=FACTS,
        spec=get_format(key),
        audience=get_audience("public"),
        language="en",
        source_name="incident_report.pdf",
        controls={"tone": "empathetic"},
    )
    body = [n for n in result.content_ir.nodes if n.kind != "heading"]
    assert body and all(n.kind == kind for n in body)
    # Every non-heading node still resolves to a real fact id.
    real = {str(f.id) for f in FACTS}
    assert all(set(n.fact_ids) <= real and n.fact_ids for n in body)


def test_video_package_promises_subtitles():
    assert "srt" in get_format("video").renderers


def test_infographic_package_exports_a_visual_layout():
    assert "html" in get_format("infographic").renderers


# --- panels and scenes: what is a claim -------------------------------------


PANEL = Node(
    id="p1",
    kind="panel",
    title="Exposure",
    items=["37 staff credentials compromised"],
    text="Most were reset within a day.",
    notes="Single big number with a key icon",
    fact_ids=["f0"],
)
SCENE = Node(
    id="s1",
    kind="scene",
    title="Opening",
    text="On 11 March 2026, 37 staff credentials were compromised. All were reset.",
    items=["37 credentials compromised"],
    notes="Slow pan across an empty office",
    fact_ids=["f0"],
)


def test_visual_direction_is_not_judged_as_a_claim():
    claims = [c.text for c in atomize(ContentIR(title="t", nodes=[PANEL, SCENE]))]
    assert "37 staff credentials compromised" in claims
    assert any(c.startswith("On 11 March 2026") for c in claims)
    assert not any("icon" in c or "office" in c for c in claims)


# --- video subtitles ----------------------------------------------------------


def test_subtitles_are_derived_from_narration_only():
    srt = render_text(ContentIR(title="Video", nodes=[SCENE]), "srt")
    assert srt.startswith("1\n00:00:00,000 --> ")
    assert "37 staff credentials" in srt
    assert "office" not in srt  # visual notes never become subtitles


def test_subtitle_cues_are_short():
    long = " ".join(["word"] * 60) + "."
    for cue in cues_for(long):
        lines = cue.split("\n")
        assert len(lines) <= 2 and all(len(line) <= 42 for line in lines)


def test_subtitles_split_hindi_on_the_danda():
    assert len(cues_for("पहला वाक्य है। दूसरा वाक्य है।")) == 2


def test_timing_estimate_has_a_floor():
    assert estimate_seconds("Hi") == pytest.approx(1.5)
    assert estimate_seconds("") == 0.0


def test_infographic_html_groups_panels_into_one_grid():
    html = render_bytes(ContentIR(title="I", nodes=[PANEL, PANEL]), "html").decode()
    assert html.count('class="panels"') == 1
    assert "Visual: Single big number" in html


def test_linkedin_text_keeps_paragraphs_not_bullets():
    post = Node(id="n1", kind="post", items=["First line.", "Second para."], fact_ids=["f0"])
    out = render_text(ContentIR(title="Post", nodes=[post]), "text")
    assert "First line.\n\nSecond para." in out
    assert "* First" not in out


# --- text and image sources -----------------------------------------------------


def test_text_and_image_are_supported_sources():
    for ext in (".txt", ".md", ".png", ".jpg", ".jpeg"):
        assert ext in SUPPORTED
    assert mime_for("brief.txt") == "text/plain"
    assert mime_for("scan.JPG") == "image/jpeg"


PASTED = """Incident Summary

On 11 March 2026, 37 staff credentials were compromised
in a phishing campaign.

Actions

- Reset all affected passwords.
- Enforce MFA on every account.
"""


def test_pasted_text_becomes_citable_blocks_with_sections():
    parsed = parse_document("pasted.txt", PASTED.encode())
    kinds = [b.block_type for b in parsed.blocks]
    assert kinds == ["heading", "paragraph", "heading", "list_item", "list_item"]
    assert parsed.blocks[1].text.startswith("On 11 March 2026, 37 staff")
    assert parsed.blocks[1].section_path == "Incident Summary"
    assert parsed.blocks[3].section_path == "Actions"
    assert all(b.page_no == 1 and b.bbox is None for b in parsed.blocks)


def test_markdown_headings_nest():
    parsed = parse_document("brief.md", b"# Report\n## Findings\nMFA covered 62 percent.\n")
    assert parsed.blocks[-1].section_path == "Report > Findings"


def test_a_lone_last_line_is_not_mistaken_for_a_heading():
    parsed = parse_document("note.txt", b"First paragraph here.\n\nSigned by the CISO")
    assert parsed.blocks[-1].block_type == "paragraph"


TSV = "\n".join(
    [
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
        "1\t1\t0\t0\t0\t0\t0\t0\t1000\t800\t-1\t",
        "4\t1\t1\t1\t1\t0\t80\t80\t400\t52\t-1\t",
        "5\t1\t1\t1\t1\t1\t80\t80\t180\t50\t96\tIncident",
        "5\t1\t1\t1\t1\t2\t280\t80\t200\t52\t96\tSummary",
        "4\t1\t2\t1\t1\t0\t80\t200\t600\t24\t-1\t",
        "5\t1\t2\t1\t1\t1\t80\t200\t30\t22\t95\tOn",
        "5\t1\t2\t1\t1\t2\t120\t200\t40\t22\t95\t11",
        "5\t1\t2\t1\t1\t3\t170\t200\t80\t22\t95\tMarch",
        "5\t1\t2\t1\t1\t4\t260\t200\t40\t22\t10\t~~",
        "4\t1\t2\t1\t2\t0\t80\t230\t500\t24\t-1\t",
        "5\t1\t2\t1\t2\t1\t80\t230\t30\t22\t95\t37",
        "5\t1\t2\t1\t2\t2\t120\t230\t200\t22\t95\tcompromised.",
        "4\t1\t3\t1\t1\t0\t80\t300\t500\t24\t-1\t",
        "5\t1\t3\t1\t1\t1\t80\t300\t200\t22\t95\tReset",
        "5\t1\t3\t1\t1\t2\t290\t300\t200\t22\t95\tpasswords.",
    ]
)


def test_ocr_paragraphs_keep_their_box_on_the_image():
    parsed = parse_tsv(TSV)
    assert [b.block_type for b in parsed.blocks] == ["heading", "paragraph", "paragraph"]
    body = parsed.blocks[1]
    assert body.text == "On 11 March 37 compromised."  # low-confidence noise dropped
    assert body.section_path == "Incident Summary"
    assert body.bbox == {
        "x0": 80,
        "y0": 200,
        "x1": 320,
        "y1": 252,
        "page_width": 1000,
        "page_height": 800,
    }


def test_an_image_with_no_words_yields_no_blocks():
    assert parse_tsv(TSV.split("\n")[0]).blocks == []


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_real_ocr_round_trip():
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=600, height=300)
    page.insert_text((40, 60), "Incident Summary", fontsize=26)
    page.insert_text((40, 120), "On 11 March 2026, 37 credentials were compromised.", fontsize=14)
    png = page.get_pixmap(dpi=150).tobytes("png")

    parsed = parse_document("scan.png", png)
    text = " ".join(b.text for b in parsed.blocks)
    assert "37" in text and "Incident" in text
    assert parsed.blocks[0].block_type == "heading"
    assert all(b.bbox for b in parsed.blocks)


# --- format-specific options --------------------------------------------------

from app.services.generation.formats import FORMATS  # noqa: E402
from app.services.generation.formats.base import (  # noqa: E402
    UnknownFormatOption,
    apply_options,
    resolve_options,
)


@pytest.mark.parametrize("key", sorted(FORMATS))
def test_every_format_offers_options_with_valid_defaults(key):
    spec = FORMATS[key]
    assert spec.options, f"{key} offers no options"
    for option in spec.options:
        assert option.choice(option.default) is not None
        assert len({c.key for c in option.choices}) == len(option.choices)


def test_defaults_leave_the_prompt_close_to_the_base_spec():
    spec = FORMATS["ppt"]
    applied = apply_options(spec, None)
    assert applied.prompt_fragment.startswith(spec.prompt_fragment)


def test_a_choice_adds_its_instruction_and_budget():
    applied = apply_options(FORMATS["ppt"], {"slides": "5"})
    assert applied.max_nodes == 5
    assert "Produce up to 5 slides." in applied.prompt_fragment
    # The registry entry itself is never mutated.
    assert FORMATS["ppt"].max_nodes == 10


@pytest.mark.parametrize("values", [{"slides": "99"}, {"colour": "blue"}])
def test_unknown_options_are_rejected(values):
    with pytest.raises(UnknownFormatOption):
        resolve_options(FORMATS["ppt"], values)


def test_video_length_shapes_the_scene_budget():
    assert apply_options(FORMATS["video"], {"length": "30"}).max_nodes == 6
    assert apply_options(FORMATS["video"], {"length": "120"}).max_nodes == 11


@pytest.mark.parametrize("key", sorted(FORMATS))
def test_every_format_keeps_options_few_and_valid_defaults(key):
    from app.services.generation.audiences import AUDIENCES
    from app.services.generation.controls import resolve_controls

    spec = FORMATS[key]
    assert 1 <= len(spec.options) <= 2, "keep the create form simple"
    resolve_controls({k: v for k, v in spec.defaults.items() if k != "audience"})
    if "audience" in spec.defaults:
        assert spec.defaults["audience"] in AUDIENCES
    for option in spec.options:
        for choice in option.choices:
            assert choice.audience is None or choice.audience in AUDIENCES


def test_an_option_can_choose_the_audience():
    from app.services.generation.formats.base import chosen_audience

    assert chosen_audience(FORMATS["ppt"], {"presenting_to": "public"}) == "public"
    assert chosen_audience(FORMATS["email"], {"sending_to": "officials"}) == "management"
    assert chosen_audience(FORMATS["linkedin"], None) is None


# --- slides must show their content -------------------------------------------

from app.services.generation.generator import _sanitize, _validate  # noqa: E402


def _deck(*nodes):
    return ContentIR(title="Deck", nodes=list(nodes))


def test_a_slide_without_bullets_is_sent_back():
    slide = Node(id="s1", kind="slide", title="Overview", notes="Everything here.", fact_ids=["f0"])
    problems = _validate(_deck(slide), FORMATS["ppt"], {"f0"})
    assert any("`items`" in p for p in problems)


def test_a_slide_with_bullets_passes():
    slide = Node(
        id="s1", kind="slide", title="Overview", items=["A point", "B point"], fact_ids=["f0"]
    )
    assert _validate(_deck(slide), FORMATS["ppt"], {"f0"}) == []


def test_notes_become_bullets_rather_than_an_empty_slide():
    slide = Node(
        id="s1",
        kind="slide",
        title="Findings",
        notes="Binary search is O(log n). Linear search is O(n).",
        fact_ids=["f0"],
    )
    ir, _ = _sanitize(_deck(slide), FORMATS["ppt"], {"f0": FACTS[0]})
    assert ir.nodes[0].items == ["Binary search is O(log n).", "Linear search is O(n)."]
    assert ir.nodes[0].notes is None


def test_an_empty_scene_is_dropped():
    scene = Node(id="v1", kind="scene", title="Opening", fact_ids=["f0"])
    ir, dropped = _sanitize(_deck(scene), FORMATS["video"], {"f0": FACTS[0]})
    assert ir.nodes == [] and any("empty scene" in d for d in dropped)


# --- the model-facing schema keeps lists ------------------------------------------

from app.schemas.content_ir import DraftIR  # noqa: E402


def test_draft_schema_lists_are_never_nullable():
    """Gemini drops `list | None` fields, which emptied every slide's bullets."""
    props = DraftIR.model_json_schema()["$defs"]["DraftNode"]["properties"]
    for name in ("items", "rows"):
        assert props[name].get("type") == "array", name
        assert "anyOf" not in props[name], name


def test_draft_converts_back_to_the_stored_shape():
    draft = DraftIR.model_validate(
        {
            "title": "Deck",
            "nodes": [
                {
                    "id": "s1",
                    "kind": "slide",
                    "title": "A",
                    "items": ["x", "y"],
                    "fact_ids": ["f0"],
                },
                {"id": "h1", "kind": "heading", "text": "B", "items": None, "fact_ids": []},
            ],
        }
    )
    ir = draft.to_content_ir()
    assert ir.nodes[0].items == ["x", "y"]
    assert ir.nodes[1].items is None and ir.nodes[1].rows is None


# --- every output carries what it needs ---------------------------------------


def test_an_email_may_greet_and_sign_off_without_a_citation():
    email = _deck(
        Node(id="g", kind="paragraph", text="Dear colleagues,"),
        Node(id="b", kind="paragraph", text="412 cases were confirmed.", fact_ids=["f0"]),
        Node(id="s", kind="paragraph", text="Regards, Health Department"),
    )
    assert _validate(email, FORMATS["email"], {"f0"}) == []
    ir, _ = _sanitize(email, FORMATS["email"], {"f0": FACTS[0]})
    assert [n.id for n in ir.nodes] == ["g", "b", "s"]


def test_a_long_uncited_email_paragraph_is_still_rejected():
    long_text = "This sentence makes a claim that is long enough to need a source behind it."
    email = _deck(Node(id="x", kind="paragraph", text=long_text))
    assert _validate(email, FORMATS["email"], {"f0"})


def test_an_empty_headline_is_repaired_or_dropped():
    ir, _ = _sanitize(
        _deck(
            Node(id="h1", kind="heading", title="From title", level=1),
            Node(id="h2", kind="heading", level=1),
        ),
        FORMATS["infographic"],
        {},
    )
    assert [(n.id, n.text) for n in ir.nodes] == [("h1", "From title")]


def test_a_linkedin_download_is_just_the_post():
    post = Node(id="p", kind="post", items=["First.", "#Tag"], fact_ids=["f0"])
    out = render_text(
        ContentIR(title="Internal title", nodes=[post]), "text", output_type="linkedin"
    )
    assert out.startswith("First.") and "Internal title" not in out


def test_an_email_download_starts_with_its_subject():
    body = Node(id="b", kind="paragraph", text="Hello.", fact_ids=["f0"])
    out = render_text(ContentIR(title="Water cut", nodes=[body]), "text", output_type="email")
    assert out.startswith("Subject: Water cut")


def test_a_list_keeps_its_label():
    lst = Node(id="l", kind="bullets", title="Key Figures", items=["412 cases"], fact_ids=["f0"])
    assert "Key Figures" in render_text(ContentIR(title="S", nodes=[lst]), "markdown")
