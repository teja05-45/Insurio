TEXT_A = "INSURIO HEALTH POLICY\nSum Insured: Rs. 500000\nEXCLUSIONS\nCosmetic surgery.\n"
TEXT_B = "INSURIO HEALTH POLICY\nSum Insured: Rs. 1000000\nEXCLUSIONS\nMaternity care.\n"


def test_compare_two_policies(client, account, make_ready):
    headers = account["headers"]
    first = make_ready(headers, TEXT_A)
    second = make_ready(headers, TEXT_B)

    response = client.post(
        "/api/v1/comparisons",
        json={"document_ids": [first, second]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert len(body["documents"]) == 2
    sum_field = next(field for field in body["fields"] if field["key"] == "sum_insured")
    assert sum_field["differs"] is True
    assert {value["value"] for value in sum_field["values"]} == {"500000", "1000000"}
    assert all(value["quote"] for value in sum_field["values"])
    assert body["summary"]["differences"] >= 1


def test_comparison_requires_at_least_two_policies(client, account, make_ready):
    headers = account["headers"]
    first = make_ready(headers, TEXT_A)
    response = client.post("/api/v1/comparisons", json={"document_ids": [first]}, headers=headers)
    assert response.status_code == 422


def test_comparison_rejects_foreign_documents(client, account, other_account, make_ready):
    mine = make_ready(account["headers"], TEXT_A)
    theirs = make_ready(other_account["headers"], TEXT_B)

    response = client.post(
        "/api/v1/comparisons",
        json={"document_ids": [mine, theirs]},
        headers=account["headers"],
    )
    assert response.status_code == 404


def test_comparison_library(client, account, make_ready):
    headers = account["headers"]
    first = make_ready(headers, TEXT_A)
    second = make_ready(headers, TEXT_B)
    created = client.post(
        "/api/v1/comparisons",
        json={"document_ids": [first, second], "title": "Health plans"},
        headers=headers,
    ).json()

    listing = client.get("/api/v1/comparisons", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    detail = client.get(f"/api/v1/comparisons/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["title"] == "Health plans"

    deleted = client.delete(f"/api/v1/comparisons/{created['id']}", headers=headers)
    assert deleted.status_code == 200
