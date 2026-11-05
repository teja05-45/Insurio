from conftest import POLICY_TEXT, build_pdf


def test_upload_rejects_non_pdf_bytes(client, account):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", b"this is not a pdf", "application/pdf")},
        headers=account["headers"],
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_pdf_type"


def test_upload_rejects_empty_file(client, account):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=account["headers"],
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_upload_processing_and_workspace_endpoints(client, account, ready_document):
    headers = account["headers"]

    detail = client.get(f"/api/v1/documents/{ready_document}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "ready"
    assert body["page_count"] == 1
    assert body["chunk_count"] >= 1
    assert body["has_insights"] is True
    assert body["latest_job"]["status"] == "ready"

    pages = client.get(f"/api/v1/documents/{ready_document}/pages", headers=headers)
    assert pages.status_code == 200
    assert "Cosmetic surgery" in pages.json()[0]["text"]

    single_page = client.get(f"/api/v1/documents/{ready_document}/pages/1", headers=headers)
    assert single_page.status_code == 200
    missing_page = client.get(f"/api/v1/documents/{ready_document}/pages/99", headers=headers)
    assert missing_page.status_code == 404


def test_owner_can_download_pdf(client, account, ready_document):
    response = client.get(f"/api/v1/documents/{ready_document}/file", headers=account["headers"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert "no-store" in response.headers["cache-control"]


def test_insights_are_structured_with_evidence(client, account, ready_document):
    response = client.get(
        f"/api/v1/documents/{ready_document}/insights", headers=account["headers"]
    )
    assert response.status_code == 200
    body = response.json()
    field = next(item for item in body["fields"] if item["key"] == "sum_insured")
    assert field["status"] == "found"
    assert "500000" in field["value"]
    assert field["page"] == 1
    assert field["quote"]


def test_duplicate_upload_is_rejected(client, account, upload):
    data = build_pdf([POLICY_TEXT])
    upload(account["headers"], data)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("again.pdf", data, "application/pdf")},
        headers=account["headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_document"


def test_documents_are_isolated_between_users(client, account, other_account, ready_document):
    response = client.get(f"/api/v1/documents/{ready_document}", headers=other_account["headers"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"

    listing = client.get("/api/v1/documents", headers=other_account["headers"])
    assert listing.json()["total"] == 0


def test_document_library_pagination(client, account, ready_document):
    response = client.get("/api/v1/documents?page=1&page_size=10", headers=account["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == ready_document


def test_delete_document_removes_it_and_its_file(client, account, ready_document):
    headers = account["headers"]
    deleted = client.delete(f"/api/v1/documents/{ready_document}", headers=headers)
    assert deleted.status_code == 200

    gone = client.get(f"/api/v1/documents/{ready_document}", headers=headers)
    assert gone.status_code == 404
    file_response = client.get(f"/api/v1/documents/{ready_document}/file", headers=headers)
    assert file_response.status_code == 404


def test_meta_and_usage_endpoints(client, account, ready_document):
    meta = client.get("/api/v1/meta")
    assert meta.status_code == 200
    assert meta.json()["llm_configured"] is True
    assert meta.json()["embeddings_mode"] == "hashing"

    usage = client.get("/api/v1/usage", headers=account["headers"])
    assert usage.status_code == 200
    assert usage.json()["documents"] == 1
