from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="video",
    name="Video",
    description="Script, scenes, voice-over, subtitles and visual ideas for a short video.",
    allowed_kinds=("heading", "paragraph", "scene"),
    prompt_fragment="""Produce a VIDEO PACKAGE for a 60 to 120 second explainer. This is the
production brief, not a video.

- optionally one `paragraph` first: the video's purpose and core message in
  one or two sentences
- 4 to 8 `scene` nodes in order, forming the storyboard. For each:
  - `title`: a short scene label, for example "Opening: what happened"
  - `text`: the voice-over narration for this scene, spoken aloud, 15 to 45
    words. Subtitles are generated from this narration, so write it exactly
    as it should be heard and read.
  - `items`: 0 to 2 short on-screen text overlays, each under 8 words, taken
    from the narration's facts
  - `notes`: the visual recommendation -- shot, footage, graphic or animation
    to show while the narration plays. Never introduce a figure in `notes`
    that is not in the narration.

Open with the most important fact, end with the action or source the facts
give. Calm, factual delivery; never dramatise.""",
    renderers=("docx", "markdown", "html", "srt"),
    max_nodes=10,
    options=(
        FormatOption(
            key="length",
            label="Length",
            default="60",
            choices=(
                FormatChoice(
                    "30",
                    "30 sec",
                    "Target 30 seconds: 3 to 4 scenes of 15-25 words.",
                    max_nodes=6,
                ),
                FormatChoice("60", "1 min", "Target 60 seconds: 4 to 6 scenes."),
                FormatChoice("120", "2 min", "Target 120 seconds: 7 to 9 scenes.", max_nodes=11),
            ),
        ),
        FormatOption(
            key="screen",
            label="Screen",
            default="wide",
            choices=(
                FormatChoice("wide", "Wide (YouTube)", "Frame visuals for a wide 16:9 screen."),
                FormatChoice(
                    "vertical",
                    "Vertical (Reels)",
                    "Frame visuals for a vertical 9:16 phone screen, such as Reels or Shorts.",
                ),
            ),
        ),
    ),
    defaults={
        "audience": "public",
        "tone": "conversational",
        "objective": "awareness",
        "style": "plain_language",
    },
)
