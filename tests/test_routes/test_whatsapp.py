from unittest.mock import patch, AsyncMock


@patch("routes.whatsapp.langchain_svc.process_message", new_callable=AsyncMock)
@patch(
    "services.twilio_service.TwilioService.send_text_message", new_callable=AsyncMock
)
def test_twilio_webhook_post(mock_send, mock_gemini, client):
    """Test Twilio Form Data payload with mocked services."""

    # Add 'raw_response' to the mock return value.
    # Our LangChain service now includes this for the final WhatsApp text.
    mock_gemini.return_value = {
        "action": "answer",
        "data": {"message": "Sure, I can help you book for tomorrow!"},
        "raw_response": "Sure, I can help you book for tomorrow!",
    }

    payload = {
        "From": "whatsapp:+14155238886",  # Standard Twilio Sandbox number
        "Body": "I want to book for tomorrow",
        "ProfileName": "John Doe",
    }

    # Execute the post
    response = client.post("/webhook/twilio", data=payload)

    # Verify the results
    assert response.status_code == 200
    mock_gemini.assert_called_once()

    # Ensure the assertion looks for the content of 'raw_response'
    mock_send.assert_called_once_with(
        to="14155238886", body="Sure, I can help you book for tomorrow!"
    )
