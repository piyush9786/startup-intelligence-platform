from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import StartupProfile


def make_user(username: str):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def suggestions_by_field(response):
    return {item["field"]: item for item in response.data["suggestions"]}


def test_incorporation_certificate_returns_confirmable_suggestions(db):
    user = make_user("document-autofill-incorporation")
    document = SimpleUploadedFile(
        "incorporation.txt",
        (
            b"CERTIFICATE OF INCORPORATION\n"
            b"Name of Company: ACME CLIMATE PRIVATE LIMITED\n"
            b"Corporate Identity Number: U72900KA2025PTC123456\n"
            b"Date of Incorporation: 15/01/2025\n"
            b"This company is incorporated under the Companies Act.\n"
        ),
        content_type="text/plain",
    )

    response = authenticated_client(user).post(
        reverse("startup-profile-autofill-from-document"),
        {"file": document, "document_type": "auto"},
        format="multipart",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["requires_confirmation"] is True
    assert response.data["document_type"]["value"] == "incorporation_certificate"

    suggestions = suggestions_by_field(response)
    assert suggestions["legal_name"]["value"] == "ACME CLIMATE PRIVATE LIMITED"
    assert suggestions["startup_name"]["value"] == "ACME CLIMATE"
    assert suggestions["incorporation_type"]["value"] == "private_limited"
    assert suggestions["incorporation_date"]["value"] == "2025-01-15"
    assert suggestions["regulatory_registrations"]["value"] == [
        "U72900KA2025PTC123456"
    ]
    assert suggestions["legal_name"]["evidence"]["text"]
    assert StartupProfile.objects.count() == 0


def test_udyam_certificate_returns_registration_and_location(db):
    user = make_user("document-autofill-udyam")
    document = SimpleUploadedFile(
        "udyam.txt",
        (
            b"UDYAM REGISTRATION CERTIFICATE\n"
            b"Udyam Registration Number: UDYAM-KA-03-0123456\n"
            b"Name of Enterprise: GREEN CIRCUITS LLP\n"
            b"Date of Incorporation: 01/02/2024\n"
            b"State: Karnataka\n"
            b"District: Bengaluru Urban\n"
        ),
        content_type="text/plain",
    )

    response = authenticated_client(user).post(
        reverse("startup-profile-autofill-from-document"),
        {"file": document},
        format="multipart",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["document_type"]["value"] == "udyam_registration"

    suggestions = suggestions_by_field(response)
    assert suggestions["udyam_registered"]["value"] is True
    assert suggestions["state"]["value"] == "Karnataka"
    assert suggestions["district"]["value"] == "Bengaluru Urban"
    assert suggestions["regulatory_registrations"]["value"] == [
        "UDYAM-KA-03-0123456"
    ]
    assert StartupProfile.objects.count() == 0


def test_unsupported_document_type_is_rejected(db):
    user = make_user("document-autofill-unsupported")
    document = SimpleUploadedFile(
        "certificate.docx",
        b"not-a-supported-document",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )

    response = authenticated_client(user).post(
        reverse("startup-profile-autofill-from-document"),
        {"file": document},
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "file" in response.data


def test_document_autofill_requires_authentication(db):
    document = SimpleUploadedFile(
        "incorporation.txt",
        b"CERTIFICATE OF INCORPORATION",
        content_type="text/plain",
    )

    response = APIClient().post(
        reverse("startup-profile-autofill-from-document"),
        {"file": document},
        format="multipart",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
