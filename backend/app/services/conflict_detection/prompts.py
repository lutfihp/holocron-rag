from __future__ import annotations

JUDGE_PROMPT = """You are a conflict detector. Two passages from internal documents appear below.
Decide whether they make INCOMPATIBLE claims about the SAME subject.

A passage that adds detail to another, or discusses a different topic, is NOT a conflict.
Only flag genuine contradictions on the same subject.

PASSAGE_A - title: "{a_title}" - effective: {a_date} - dept: {a_dept}
{a_text}

PASSAGE_B - title: "{b_title}" - effective: {b_date} - dept: {b_dept}
{b_text}

Reply ONLY in JSON matching this schema:
{{
  "conflict": true | false,
  "subject": "short noun phrase",
  "position_a": "one-sentence summary of A's claim on the subject",
  "position_b": "one-sentence summary of B's claim on the subject"
}}"""


def render_judge_prompt(*, a_title: str, a_date: str, a_dept: str, a_text: str,
                        b_title: str, b_date: str, b_dept: str, b_text: str) -> str:
    return JUDGE_PROMPT.format(
        a_title=a_title, a_date=a_date, a_dept=a_dept, a_text=a_text,
        b_title=b_title, b_date=b_date, b_dept=b_dept, b_text=b_text,
    )
