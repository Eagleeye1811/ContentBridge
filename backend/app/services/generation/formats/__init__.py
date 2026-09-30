"""Format registry. Output types are configuration, not code paths."""

from __future__ import annotations

from app.services.generation.formats import (
    advisory,
    email,
    ppt,
    press_release,
    report,
    social,
    summary,
)
from app.services.generation.formats.base import FormatSpec

FORMATS: dict[str, FormatSpec] = {
    spec.key: spec
    # Order matters only for the Studio listing.
    for spec in (
        advisory.SPEC,
        ppt.SPEC,
        summary.SPEC,
        email.SPEC,
        social.SPEC,
        press_release.SPEC,
        report.SPEC,
    )
}


class UnknownFormat(ValueError):
    pass


def get_format(key: str) -> FormatSpec:
    spec = FORMATS.get(key)
    if spec is None:
        raise UnknownFormat(f"Unknown output type {key!r}. Available: {', '.join(sorted(FORMATS))}")
    return spec


__all__ = ["FORMATS", "FormatSpec", "UnknownFormat", "get_format"]
