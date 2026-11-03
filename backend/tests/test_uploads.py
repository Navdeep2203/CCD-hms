from datetime import date, timedelta
from types import SimpleNamespace

from app.database import fetch_one
from app.routers import uploads as uploads_router
PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-payload"
PDF_BYTES = b"%PDF-1.4\nfake-pdf-payload\n%%EOF"


def upload(client, headers, purpose, record_id, data=PNG_BYTES, content_type="image/png"):
    return client.post(
        f"/api/uploads/{purpose}/{record_id}",
        headers=headers,
        files={"file": ("test-file", data, content_type)},
    )


def test_room_image_upload_and_replacement(client, H, fake_storage):
    room_types = client.get("/api/rooms/types", headers=H("admin")).json()
    room_type_id = room_types[0]["room_type_id"]

    # First upload.
    first = upload(
        client, H("admin"), "room_image", room_type_id
    )

    assert first.status_code == 200, first.text
    assert "image_key" not in first.json()

    row = fetch_one(
        "SELECT image_key FROM room_types WHERE room_type_id = :id",
        {"id": room_type_id},
    )

    old_key = row["image_key"]
    assert old_key in fake_storage.objects

    # Second upload replaces the existing image.
    second = upload(
        client, H("admin"), "room_image", room_type_id,
        data=PNG_BYTES + b"-replacement",
    )

    assert second.status_code == 200, second.text

    row = fetch_one(
        "SELECT image_key FROM room_types WHERE room_type_id = :id",
        {"id": room_type_id},
    )

    new_key = row["image_key"]

    assert new_key != old_key
    assert new_key in fake_storage.objects
    assert old_key not in fake_storage.objects
    assert old_key in fake_storage.deleted

    # API response exposes a signed URL, never the raw key.
    listed = client.get(
        "/api/rooms/types",
        headers=H("admin"),
    ).json()

    result = next(
        item for item in listed
        if item["room_type_id"] == room_type_id
    )

    assert result["image_url"]
    assert "image_key" not in result
    assert result.get("image_key") is None
    assert result["image_url"] != new_key
    assert result["image_url"].startswith(
        "https://fake-storage.test/"
    )

def test_upload_validation_rejects_bad_signature_and_size(
    client, H, monkeypatch, fake_storage
):
    room_types = client.get("/api/rooms/types", headers=H("admin")).json()
    room_type_id = room_types[0]["room_type_id"]

    # Invalid file signature.
    invalid = upload(
        client,
        H("admin"),
        "room_image",
        room_type_id,
        data=b"this is not a PNG",
        content_type="image/png",
    )

    assert invalid.status_code == 415

    # Conflicting declared MIME type.
    mismatch = upload(
        client,
        H("admin"),
        "room_image",
        room_type_id,
        data=PNG_BYTES,
        content_type="image/jpeg",
    )

    assert mismatch.status_code == 415

    # Force a small limit to test size enforcement.
    monkeypatch.setattr(
        uploads_router,
        "settings",
        SimpleNamespace(upload_max_bytes=8),
)

    oversized = upload(
        client,
        H("admin"),
        "room_image",
        room_type_id,
        data=PNG_BYTES,
        content_type="image/png",
    )

    assert oversized.status_code == 413


def test_room_image_requires_management(client, H, new_room):
    room_types = client.get("/api/rooms/types", headers=H("admin")).json()
    room_type_id = room_types[0]["room_type_id"]

    customer_attempt = upload(
        client,
        H("customer"),
        "room_image",
        room_type_id,
    )

    assert customer_attempt.status_code == 403

    staff_attempt = upload(
        client,
        H("staff"),
        "room_image",
        room_type_id,
    )

    assert staff_attempt.status_code == 403

    unknown = upload(
        client,
        H("admin"),
        "unknown_purpose",
        1,
    )

    assert unknown.status_code == 404

    unauthorized = client.post(
        f"/api/uploads/room_image/{room_type_id}",
        files={"file": ("test.png", PNG_BYTES, "image/png")},
    )

    assert unauthorized.status_code == 401


def test_customer_can_upload_only_own_id_proof(
    client, H, customer_id, fake_storage
):
    response = upload(
        client,
        H("customer"),
        "id_proof",
        customer_id,
        data=PDF_BYTES,
        content_type="application/pdf",
    )

    assert response.status_code == 200, response.text
    assert response.json()["content_type"] == "application/pdf"
    assert "id_proof_key" not in response.json()

    row = fetch_one(
        "SELECT id_proof_key FROM customers WHERE customer_id = :id",
        {"id": customer_id},
    )

    key = row["id_proof_key"]

    assert key in fake_storage.objects

    # A customer cannot upload another customer's ID proof.
    another_customer = upload(
        client,
        H("customer"),
        "id_proof",
        customer_id + 999,
        data=PDF_BYTES,
        content_type="application/pdf",
    )

    assert another_customer.status_code == 404

    # Managers receive a signed URL.
    manager_rows = client.get(
        "/api/customers",
        headers=H("manager"),
    ).json()

    customer_row = next(
        item for item in manager_rows
        if item["customer_id"] == customer_id
    )

    assert customer_row["id_proof_url"]
    assert "id_proof_key" not in customer_row

    # Staff never receive ID proof keys or URLs.
    staff_rows = client.get(
        "/api/customers",
        headers=H("staff"),
    ).json()

    assert staff_rows

    assert all(
        "id_proof_key" not in item
        and "id_proof_url" not in item
        and "id_proof" not in item
        for item in staff_rows
    )


def test_maintenance_photo_only_for_assigned_staff(
    client, H, tokens, new_room, fake_storage
):
    room_id = new_room()
    staff_id = tokens["staff"]["user"]["staff_id"]

    created = client.post(
        "/api/maintenance",
        headers=H("manager"),
        json={
            "room_id": room_id,
            "description": "Test maintenance task",
            "staff_id": staff_id,
        },
    )

    assert created.status_code == 201, created.text
    maintenance_id = created.json()["maintenance_id"]

    # Assigned staff member can upload.
    allowed = upload(
        client,
        H("staff"),
        "maintenance_photo",
        maintenance_id,
    )

    assert allowed.status_code == 200, allowed.text

    row = fetch_one(
        "SELECT photo_key FROM room_maintenance WHERE maintenance_id = :id",
        {"id": maintenance_id},
    )

    assert row["photo_key"] in fake_storage.objects

    # Create a task without assigning it to the staff member.
    unassigned = client.post(
        "/api/maintenance",
        headers=H("manager"),
        json={
            "room_id": new_room(),
            "description": "Unassigned task",
        },
    )

    assert unassigned.status_code == 201, unassigned.text
    unassigned_id = unassigned.json()["maintenance_id"]

    denied = upload(
        client,
        H("staff"),
        "maintenance_photo",
        unassigned_id,
    )

    assert denied.status_code == 404

    # Management can also access the task.
    manager_upload = upload(
        client,
        H("manager"),
        "maintenance_photo",
        maintenance_id,
    )

    assert manager_upload.status_code == 200


def test_delete_upload_and_storage_disabled(
    client, H, fake_storage
):
    room_types = client.get("/api/rooms/types", headers=H("admin")).json()
    room_type_id = room_types[0]["room_type_id"]

    created = upload(
        client,
        H("admin"),
        "room_image",
        room_type_id,
    )

    assert created.status_code == 200

    row = fetch_one(
        "SELECT image_key FROM room_types WHERE room_type_id = :id",
        {"id": room_type_id},
    )

    key = row["image_key"]

    deleted = client.delete(
        f"/api/uploads/room_image/{room_type_id}",
        headers=H("admin"),
    )

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] is True
    assert key not in fake_storage.objects
    assert key in fake_storage.deleted

    row = fetch_one(
        "SELECT image_key FROM room_types WHERE room_type_id = :id",
        {"id": room_type_id},
    )

    assert row["image_key"] is None

    # Storage disabled must produce a clean 503 response.
    fake_storage.enabled_value = False

    try:
        disabled = upload(
            client,
            H("admin"),
            "room_image",
            room_type_id,
        )

        assert disabled.status_code == 503
    finally:
        fake_storage.enabled_value = True


def test_invoice_pdf_generation_and_storage(
    client, H, customer_id, new_room, fake_storage
):
    room_id = new_room()

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Staff creates a walk-in booking for the seeded customer.
    booking_response = client.post(
        "/api/bookings",
        headers=H("staff"),
        json={
            "room_id": room_id,
            "customer_id": customer_id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
        },
    )

    assert booking_response.status_code == 201, booking_response.text

    booking_id = booking_response.json()["booking_id"]

    # Check the guest in so the booking becomes billable.
    check_in = client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=H("staff"),
        json={"status": "CHECKED_IN"},
    )

    assert check_in.status_code == 200, check_in.text

    # Generate and store the invoice PDF.
    generated = client.post(
        f"/api/billing/invoices/{booking_id}/pdf",
        headers=H("staff"),
    )

    assert generated.status_code == 200, generated.text

    result = generated.json()

    assert result["booking_id"] == booking_id
    assert result["filename"].endswith(".pdf")
    assert result["content_type"] == "application/pdf"
    assert result["pdf_url"]
    assert "pdf_key" not in result

    invoice_id = result["invoice_id"]

    row = fetch_one(
        "SELECT pdf_key FROM invoices WHERE invoice_id = :id",
        {"id": invoice_id},
    )

    pdf_key = row["pdf_key"]

    assert pdf_key == f"invoice_pdf/{invoice_id}.pdf"
    assert pdf_key in fake_storage.objects
    assert fake_storage.objects[pdf_key].startswith(b"%PDF")

    # Invoice listing exposes the URL, not the key.
    invoices = client.get(
        "/api/billing/invoices",
        headers=H("staff"),
    ).json()

    invoice_row = next(
        item for item in invoices
        if item["invoice_id"] == invoice_id
    )

    assert invoice_row["pdf_url"]
    assert "pdf_key" not in invoice_row

    # The customer can generate/download their own invoice.
    customer_result = client.post(
        f"/api/billing/invoices/{booking_id}/pdf",
        headers=H("customer"),
    )

    assert customer_result.status_code == 200, customer_result.text
    assert customer_result.json()["pdf_url"]
