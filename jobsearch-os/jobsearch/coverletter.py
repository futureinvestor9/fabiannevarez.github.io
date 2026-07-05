"""B7 cover letter generation: diagnosis -> 3-paragraph letter, validated
against the A11 banned-phrase blocklist and checked for a unique opening.
"""
from __future__ import annotations

from dataclasses import dataclass

from jobsearch import signals
from jobsearch.config import BANNED_PHRASES, COVER_LETTER_CONTENT
from jobsearch.diagnosis import Diagnosis, _top_categories

MAX_WORDS = 250


class CoverLetterValidationError(Exception):
    pass


def find_banned_phrases(text: str) -> list[str]:
    lowered = text.lower()
    return [p for p in BANNED_PHRASES if p.lower() in lowered]


def assert_clean(text: str) -> None:
    violations = find_banned_phrases(text)
    if violations:
        raise CoverLetterValidationError(f"Banned phrases found in generated text: {violations}")


def _render_opening(template: str, title: str, problem: str) -> str:
    return template.format(title=title, problem=problem)


def _pick_opening(title: str, problem: str, existing_openings: set[str]) -> str:
    templates = COVER_LETTER_CONTENT["opening_templates"]
    for template in templates:
        candidate = _render_opening(template, title, problem)
        if candidate.strip().lower() not in {o.strip().lower() for o in existing_openings}:
            return candidate
    raise CoverLetterValidationError(
        "Could not produce a unique opening sentence — all rotation templates already used "
        "for this problem statement. Diagnose with more specific JD detail before regenerating."
    )


@dataclass
class CoverLetter:
    opening_sentence: str
    body: str
    pasted_version: str
    word_count: int


def generate_cover_letter(
    company: str,
    title: str,
    diagnosis: Diagnosis,
    jd_text: str,
    existing_openings: set[str] | None = None,
) -> CoverLetter:
    existing_openings = existing_openings or set()
    top_cats = _top_categories(jd_text)
    top_cat = top_cats[0] if top_cats else "process"

    opening = _pick_opening(title, diagnosis.likely_struggle, existing_openings)

    value_paragraphs = COVER_LETTER_CONTENT["value_paragraphs"]
    para2 = value_paragraphs.get(top_cat, value_paragraphs["process"]).strip()

    # Bring in a second proof point's phrasing if a distinct secondary
    # category is well represented and not already covered by paragraph 2.
    if len(top_cats) > 1 and diagnosis.proof_points:
        secondary_pp = next(
            (pp for pp in diagnosis.proof_points if top_cats[1] in pp["tags"]),
            None,
        )
        if secondary_pp and secondary_pp["cover_letter_phrasing"].strip() not in para2:
            para2 = f"{para2} {secondary_pp['cover_letter_phrasing'].strip()}"

    no_bs = COVER_LETTER_CONTENT["no_bs_statement"].strip()
    ask = COVER_LETTER_CONTENT["closing_ask"].format(
        ask_topic=f"the first 90 days of the {title} role", company=company
    ).strip()
    para3 = f"{no_bs} {ask}"

    para1 = f"{opening.rstrip('.')}."

    body = "\n\n".join([para1, para2, para3])
    assert_clean(body)

    word_count = len(body.split())
    if word_count > MAX_WORDS:
        # Trim the least essential sentence (the bridged secondary proof
        # point) before falling back to a hard truncation.
        para2_trimmed = para2.split(". ")[0].strip()
        if not para2_trimmed.endswith("."):
            para2_trimmed += "."
        body = "\n\n".join([para1, para2_trimmed, para3])
        assert_clean(body)
        word_count = len(body.split())

    signature = "\n\n— Fabian"
    pasted_version = body + signature

    return CoverLetter(
        opening_sentence=opening,
        body=body,
        pasted_version=pasted_version,
        word_count=word_count,
    )
