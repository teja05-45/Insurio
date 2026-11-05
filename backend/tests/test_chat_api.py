import pytest

from conftest import canned_answer, parse_sse


@pytest.fixture
def conversation(client, account, ready_document):
    response = client.post(
        "/api/v1/conversations",
        json={"document_id": ready_document},
        headers=account["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def ask(client, account, conversation_id, question="Is cosmetic surgery covered?"):
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"question": question},
        headers=account["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


def test_answer_streams_and_persists_validated_citations(client, account, conversation, fake_llm):
    fake_llm(canned_answer())
    events = ask(client, account, conversation["id"])
    names = [name for name, _ in events]

    assert names[0] == "meta"
    assert "delta" in names
    assert names[-1] == "final"

    final = events[-1][1]["message"]
    assert "excluded" in final["content"].lower()
    assert final["status"] == "complete"
    assert final["citation_status"] == "valid"
    assert len(final["citations"]) == 1
    assert final["citations"][0]["page_start"] == 1
    assert final["model"] == "fake-llm"

    detail = client.get(f"/api/v1/conversations/{conversation['id']}", headers=account["headers"])
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["citations"][0]["quote"]
    assert detail.json()["message_count"] == 2


def test_invented_citation_is_dropped(client, account, conversation, fake_llm):
    fake_llm(
        canned_answer(
            citations=[{"source_id": "S1", "quote": "Dental implants are covered worldwide"}],
            stated=["Dental implants are covered worldwide."],
        )
    )
    # A question that retrieves a source, so the rejection is about the quote.
    events = ask(client, account, conversation["id"], question="Is cosmetic surgery excluded?")
    final = events[-1][1]["message"]

    assert final["citations"] == []
    assert final["citation_status"] == "missing"


def test_insufficient_evidence_is_explicit(client, account, conversation, fake_llm):
    fake_llm(
        canned_answer(
            answer_markdown="The policy does not state whether maternity care is covered.",
            citations=[],
            stated=[],
            not_in_document=["Maternity cover is not mentioned."],
            confidence=0.2,
            insufficient_evidence=True,
        )
    )
    events = ask(client, account, conversation["id"], question="Is maternity care covered?")
    final = events[-1][1]["message"]

    assert final["insufficient_evidence"] is True
    assert final["not_in_document"]
    assert final["citation_status"] == "not_applicable"


def test_conversation_is_isolated_between_users(
    client, account, other_account, conversation, fake_llm
):
    fake_llm(canned_answer())
    response = client.get(
        f"/api/v1/conversations/{conversation['id']}", headers=other_account["headers"]
    )
    assert response.status_code == 404

    ask_response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"question": "Is cosmetic surgery covered?"},
        headers=other_account["headers"],
    )
    assert ask_response.status_code == 404


def test_regenerate_reuses_the_last_question(client, account, conversation, fake_llm):
    fake_llm(canned_answer())
    ask(client, account, conversation["id"])

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/regenerate",
        headers=account["headers"],
    )
    assert response.status_code == 200, response.text
    events = parse_sse(response.text)
    assert events[-1][0] == "final"

    detail = client.get(f"/api/v1/conversations/{conversation['id']}", headers=account["headers"])
    roles = [message["role"] for message in detail.json()["messages"]]
    assert roles == ["user", "assistant"]
    assert len(detail.json()["messages"][1]["citations"]) == 1


def test_feedback_is_recorded_on_answers_only(client, account, conversation, fake_llm):
    fake_llm(canned_answer())
    events = ask(client, account, conversation["id"])
    message_id = events[-1][1]["message"]["id"]

    response = client.post(
        f"/api/v1/messages/{message_id}/feedback",
        json={"rating": "up", "comment": "Accurate"},
        headers=account["headers"],
    )
    assert response.status_code == 200

    updated = client.post(
        f"/api/v1/messages/{message_id}/feedback",
        json={"rating": "down"},
        headers=account["headers"],
    )
    assert updated.status_code == 200


def test_conversation_list_shows_counts_and_preview(client, account, conversation, fake_llm):
    fake_llm(canned_answer())
    ask(client, account, conversation["id"])

    listing = client.get("/api/v1/conversations", headers=account["headers"])
    assert listing.status_code == 200
    item = listing.json()["items"][0]
    assert item["message_count"] == 2
    assert item["preview"]


def test_conversation_rename_and_delete(client, account, conversation):
    renamed = client.patch(
        f"/api/v1/conversations/{conversation['id']}",
        json={"title": "Cosmetic surgery"},
        headers=account["headers"],
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Cosmetic surgery"

    deleted = client.delete(
        f"/api/v1/conversations/{conversation['id']}", headers=account["headers"]
    )
    assert deleted.status_code == 200
