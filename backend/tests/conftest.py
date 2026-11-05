"""Test fixtures.

The suite runs fully offline: SQLite instead of PostgreSQL, the deterministic
hashing embedder instead of a downloaded model, and an injected fake LLM instead
of Groq. No paid API call is made by these tests.
"""

import json
import os
import tempfile
import uuid

import fitz
import pytest

_TMP = tempfile.mkdtemp(prefix="insurio-test-")
os.environ.update(
    {
        "APP_ENV": "test",
        "SECRET_KEY": "test-secret-key-0123456789abcdef0123456789abcdef",
        "DATABASE_URL": "sqlite+pysqlite:///" + (_TMP + "/test.db").replace("\\", "/"),
        "UPLOAD_DIR": (_TMP + "/uploads").replace("\\", "/"),
        "EMBEDDING_PROVIDER": "hashing",
        "EMBEDDINGS_ENABLED": "true",
        "GROQ_API_KEY": "test-groq-key",
        "INSIGHTS_LLM_ENRICHMENT": "false",
        "RATE_LIMIT_ENABLED": "false",
        "RETRIEVAL_TOP_K": "6",
    }
)

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services import documents as document_service  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PASSWORD = "StrongPass123"
POLICY_TEXT = (
    "INSURIO HEALTH POLICY SCHEDULE\n"
    "Policy Holder: Asha Rao\n"
    "Sum Insured: Rs. 500000\n"
    "EXCLUSIONS\n"
    "Cosmetic surgery is excluded from coverage.\n"
    "War and nuclear risks are excluded.\n"
    "WAITING PERIOD\n"
    "An initial waiting period of 30 days applies."
)
CITATION_QUOTE = "Cosmetic surgery is excluded from coverage"


def build_pdf(pages: list[str]) -> bytes:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 545, 790), text, fontsize=11)
    data = document.tobytes()
    document.close()
    return data


def parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event = ""
        data = ""
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if event:
            events.append((event, json.loads(data) if data else {}))
    return events


def canned_answer(**overrides) -> str:
    payload = {
        "answer_markdown": (
            f"Cosmetic surgery is excluded from coverage [S1].\n\n" f"> {CITATION_QUOTE}"
        ),
        "citations": [{"source_id": "S1", "quote": CITATION_QUOTE}],
        "stated": [CITATION_QUOTE],
        "inferred": [],
        "not_in_document": [],
        "confidence": 0.9,
        "insufficient_evidence": False,
    }
    payload.update(overrides)
    return json.dumps(payload)


class FakeLLM:
    """Streams a canned response in small pieces, like a provider would."""

    model_name = "fake-llm"

    def __init__(self, raw: str, chunk_size: int = 32) -> None:
        self.raw = raw
        self.chunk_size = chunk_size

    def stream(self, messages: list[dict[str, str]]):
        for index in range(0, len(self.raw), self.chunk_size):
            yield self.raw[index : index + self.chunk_size]

    def complete(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        return self.raw


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, label: str) -> dict:
    email = f"{label}-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": label.title()},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "email": email,
        "password": PASSWORD,
        "token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "user": body["user"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


@pytest.fixture
def account(client):
    return register(client, "primary")


@pytest.fixture
def other_account(client):
    return register(client, "secondary")


@pytest.fixture
def upload(client):
    def _upload(headers: dict, data: bytes, filename: str = "policy.pdf") -> dict:
        response = client.post(
            "/api/v1/documents",
            files={"file": (filename, data, "application/pdf")},
            headers=headers,
        )
        assert response.status_code == 202, response.text
        return response.json()

    return _upload


def ensure_ready(client: TestClient, headers: dict, document_id: str) -> str:
    status = client.get(f"/api/v1/documents/{document_id}/status", headers=headers).json()
    if status["status"] != "ready":
        # Background tasks normally complete inside TestClient; this makes the
        # fixture deterministic if one is delayed.
        document_service.process_document(uuid.UUID(document_id))
        status = client.get(f"/api/v1/documents/{document_id}/status", headers=headers).json()
    assert status["status"] == "ready", status
    return document_id


@pytest.fixture
def make_ready(client, upload):
    def _make(headers: dict, text: str) -> str:
        document = upload(headers, build_pdf([text]))
        return ensure_ready(client, headers, document["id"])

    return _make


@pytest.fixture
def ready_document(make_ready, account) -> str:
    return make_ready(account["headers"], POLICY_TEXT)


@pytest.fixture
def fake_llm(monkeypatch):
    def _install(raw: str) -> FakeLLM:
        import app.services.answering as answering
        from app.ai.embeddings import HashingEmbedder
        from app.ai.pipeline import AnswerPipeline

        fake = FakeLLM(raw)

        def _build(settings, top_k: int | None = None) -> AnswerPipeline:
            return AnswerPipeline(
                llm=fake,
                embedder=HashingEmbedder(384),
                top_k=top_k or settings.RETRIEVAL_TOP_K,
                candidates=settings.RETRIEVAL_CANDIDATES,
                min_score=settings.RETRIEVAL_MIN_SCORE,
            )

        monkeypatch.setattr(answering, "build_pipeline", _build)
        return fake

    return _install
