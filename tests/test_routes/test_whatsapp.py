import pytest


def test_meta_webhook_verification(client):
    """Test the GET handshake from Meta."""
    verify_token = "your_secret_token"  # Should match settings
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": verify_token,
        "hub.challenge": "12345",
    }
    response = client.get("/webhook/meta", params=params)
    assert response.status_code == 200
    assert response.text == "12345"


def test_twilio_webhook_post(client):
    """Test Twilio Form Data payload."""
    payload = {
        "From": "whatsapp:+123456789",
        "Body": "I want to book for tomorrow",
        "ProfileName": "John Doe",
    }
    # Note: Twilio sends data as Form, not JSON
    response = client.post("/webhook/twilio", data=payload)
    assert response.status_code == 200
