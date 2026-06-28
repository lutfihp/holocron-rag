"""LLM-as-judge prompt for citation accuracy."""

CITATION_JUDGE_PROMPT = """You are an evaluation judge. Given a question, an answer
with inline citation markers like [1], [2], and the source snippets those markers
refer to, decide whether the citations are appropriate.

Score 1.0 if every cited snippet directly supports the sentence containing its
marker. Score 0.0 if any cited snippet is unrelated or contradicts the sentence.
Use intermediate values (0.5) when citations are partially supported.

Reply ONLY with JSON: {{"score": <float in [0,1]>, "reason": "<one short sentence>"}}

QUESTION: {question}

ANSWER: {answer}

CITED SNIPPETS:
{snippets}
"""
