"""Grounded answer pipeline: retrieval, structured output, citation validation."""

import json
from collections.abc import Iterator
from dataclasses import dataclass

from app.ai.citations import validate_citations
from app.ai.embeddings import Embedder
from app.ai.prompts import build_answer_messages, build_sources, source_is_suspicious
from app.ai.retrieval import retrieve
from app.ai.types import LLM, GroundedAnswer, RetrievedChunk

INSUFFICIENT_MESSAGE = (
    "I could not find enough evidence in this policy to answer that.\n\n"
    "The document may not address this situation, or it may use different wording. "
    "Try rephrasing with the procedure name, or check the exclusions and waiting-period sections. "
    "For a definitive answer, confirm with your insurer."
)


def parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _string_list(value: object, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:500] for item in value if str(item).strip()][:limit]


def _clamp_confidence(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def build_grounded_answer(raw: str, sources: list[RetrievedChunk]) -> GroundedAnswer:
    data = parse_json_object(raw)
    unparsed = not data
    answer_text = str(data.get("answer_markdown") or "").strip()
    if unparsed:
        answer_text = raw.strip()

    citations, invalid = validate_citations(data.get("citations"), sources)
    insufficient = bool(data.get("insufficient_evidence", False))
    if unparsed:
        citation_status = "unparsed"
    elif insufficient and not citations:
        citation_status = "not_applicable"
    elif not citations:
        citation_status = "missing"
    elif invalid:
        citation_status = "partial"
    else:
        citation_status = "valid"

    return GroundedAnswer(
        answer_markdown=answer_text or INSUFFICIENT_MESSAGE,
        citations=citations,
        confidence=_clamp_confidence(data.get("confidence")),
        insufficient_evidence=insufficient,
        stated=_string_list(data.get("stated")),
        inferred=_string_list(data.get("inferred")),
        not_in_document=_string_list(data.get("not_in_document")),
        citation_status=citation_status,
        invalid_citations=invalid,
        metadata={"unparsed": unparsed},
    )


@dataclass
class PreparedContext:
    sources: list[RetrievedChunk]
    retrieval_mode: str
    suspicious_sources: int


class AnswerPipeline:
    def __init__(
        self,
        *,
        llm: LLM,
        embedder: Embedder | None,
        top_k: int,
        candidates: int,
        min_score: float,
    ) -> None:
        self.llm = llm
        self.embedder = embedder
        self.top_k = top_k
        self.candidates = candidates
        self.min_score = min_score

    def prepare(self, chunks: list[object], question: str) -> PreparedContext:
        sources, mode = retrieve(
            chunks,
            question,
            embedder=self.embedder,
            top_k=self.top_k,
            candidates=self.candidates,
            min_score=self.min_score,
        )
        suspicious = sum(1 for source in sources if source_is_suspicious(source.content))
        return PreparedContext(sources, mode, suspicious)

    def messages(
        self, question: str, sources: list[RetrievedChunk], history: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[RetrievedChunk]]:
        """Build messages and return the sources that actually fit the budget."""
        sources_text, included = build_sources(sources)
        return build_answer_messages(question, sources_text, history), included

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        return self.llm.stream(messages)

    @staticmethod
    def no_evidence_answer() -> GroundedAnswer:
        return GroundedAnswer(
            answer_markdown=INSUFFICIENT_MESSAGE,
            citations=[],
            confidence=0.0,
            insufficient_evidence=True,
            stated=[],
            inferred=[],
            not_in_document=["The retrieved pages do not contain a relevant clause."],
            citation_status="not_applicable",
        )


class AnswerFieldExtractor:
    """Incrementally decode the `answer_markdown` string from streamed JSON.

    The model is asked to emit that key first. Streaming the decoded field gives
    real token streaming while citations and flags are only trusted after the
    complete JSON has been parsed and validated.
    """

    def __init__(self, field: str = "answer_markdown") -> None:
        self.key = f'"{field}"'
        self.raw = ""
        self.pos = 0
        self.state = "search"
        self.escaping = False
        self.unicode_buffer = ""
        self.emitted_any = False

    def feed(self, delta: str) -> str:
        self.raw += delta
        output: list[str] = []
        while self.pos < len(self.raw) and self.state != "done":
            char = self.raw[self.pos]
            if self.state == "search":
                index = self.raw.find(self.key, self.pos)
                if index == -1:
                    # Keep enough tail to match a key split across deltas.
                    self.pos = max(self.pos, len(self.raw) - len(self.key))
                    break
                self.pos = index + len(self.key)
                self.state = "colon"
                continue
            if self.state == "colon":
                if char == ":":
                    self.state = "quote"
                elif not char.isspace():
                    self.state = "search"
                    continue
                self.pos += 1
                continue
            if self.state == "quote":
                if char == '"':
                    self.state = "body"
                elif not char.isspace():
                    self.state = "search"
                self.pos += 1
                continue
            if self.state == "body":
                if self.escaping:
                    if self.unicode_buffer or char == "u":
                        self.unicode_buffer += char
                        if len(self.unicode_buffer) == 5:
                            try:
                                output.append(json.loads(f'"\\{self.unicode_buffer}"'))
                            except json.JSONDecodeError:
                                pass
                            self.unicode_buffer = ""
                            self.escaping = False
                        self.pos += 1
                        continue
                    decoded = {
                        "n": "\n",
                        "t": "\t",
                        "r": "\r",
                        "b": "\b",
                        "f": "\f",
                        '"': '"',
                        "\\": "\\",
                        "/": "/",
                    }.get(char)
                    if decoded is not None:
                        output.append(decoded)
                    self.escaping = False
                    self.pos += 1
                    continue
                if char == "\\":
                    self.escaping = True
                elif char == '"':
                    self.state = "done"
                else:
                    output.append(char)
                self.pos += 1
                continue
        text = "".join(output)
        if text:
            self.emitted_any = True
        return text
