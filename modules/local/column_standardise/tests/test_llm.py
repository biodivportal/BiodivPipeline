from unittest.mock import patch, MagicMock
from app.services.llm_service import get_llm_prediction


@patch("app.services.llm_service.anthropic.Anthropic")
def test_llm_prediction_anthropic(MockAnthropic):
    # Setup mock response
    mock_client = MockAnthropic.return_value
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"llm_prediction": "LatitudeDecimal"}')]
    mock_client.messages.create.return_value = mock_response

    term_descriptions = {"LatitudeDecimal": "Latitude", "LongitudeDecimal": "Longitude"}

    # Call function properly with new arguments
    prediction = get_llm_prediction(
        "fake_key",
        "anthropic",
        "claude-haiku-4-5",
        "Lat",
        "1.0",
        ["LatitudeDecimal"],
        term_descriptions,
    )

    # Verify mock was called correctly
    mock_client.messages.create.assert_called_once()
    assert prediction is not None
    assert prediction.get("prediction") == "LatitudeDecimal"


@patch("app.services.llm_service.openai.OpenAI")
def test_llm_prediction_openai(MockOpenAI):
    mock_client = MockOpenAI.return_value
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"llm_prediction": "LongitudeDecimal"}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    term_descriptions = {"LatitudeDecimal": "Latitude", "LongitudeDecimal": "Longitude"}

    prediction = get_llm_prediction(
        "fake_key",
        "openai",
        "gpt-4o",
        "Lon",
        "2.0",
        ["LongitudeDecimal"],
        term_descriptions,
    )

    mock_client.chat.completions.create.assert_called_once()
    assert prediction is not None
    assert prediction.get("prediction") == "LongitudeDecimal"


@patch("app.services.llm_service.anthropic.Anthropic")
def test_llm_prediction_error(MockAnthropic):
    mock_client = MockAnthropic.return_value
    mock_client.messages.create.side_effect = Exception("API Error")

    prediction = get_llm_prediction(
        "fake_key", "anthropic", "claude-haiku-4-5", "Lat", "1.0", [], {}
    )

    # Should gracefully return None on exception
    assert prediction is None
