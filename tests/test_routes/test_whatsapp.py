from unittest.mock import patch, AsyncMock


@patch("routes.whatsapp.gemini_svc.process_message", new_callable=AsyncMock)
@patch(
    "services.twilio_service.TwilioService.send_text_message", new_callable=AsyncMock
)
def test_twilio_webhook_post(mock_send, mock_gemini, client):
    """Test Twilio Form Data payload with mocked services."""

    # 1. Mock the AI response so we don't call Gemini
    mock_gemini.return_value = {
        "action": "answer",
        "data": {"message": "Sure, I can help you book for tomorrow!"},
    }

    # 2. Use a realistic WhatsApp-formatted number
    payload = {
        "From": "whatsapp:+14155238886",  # Standard Twilio Sandbox number
        "Body": "I want to book for tomorrow",
        "ProfileName": "John Doe",
    }

    # 3. Execute the post
    # FastAPI's TestClient will wait for BackgroundTasks to finish before returning
    response = client.post("/webhook/twilio", data=payload)

    # 4. Verify the results
    assert response.status_code == 200

    # Ensure our services were actually triggered in the background
    mock_gemini.assert_called_once()
    mock_send.assert_called_once_with(
        to="14155238886", body="Sure, I can help you book for tomorrow!"
    )
