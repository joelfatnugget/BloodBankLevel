import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from fetch_blood import (
    parse_blood_levels,
    fetch_blood_levels,
    fetch_blood_data,
    write_to_markdown,
)

SAMPLE_ELEMENTOR_HTML = """
<div class="blood-level-list">
    <div class="elementor-element blood-level-card" blood-type="A+" blood-level="Healthy">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="B+" blood-level="High">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="O+" blood-level="Healthy">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="AB+" blood-level="Healthy">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="A-" blood-level="Healthy">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="B-" blood-level="Moderate">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="O-" blood-level="Moderate">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
    <div class="elementor-element blood-level-card" blood-type="AB-" blood-level="Moderate">
        <div class="blood-level-label"><p>Blood Level:</p></div>
    </div>
</div>
"""

SAMPLE_LEGACY_HTML = """
<div class="blood-grp-text">
    <h3>A+</h3>
    <h5>Healthy</h5>
</div>
<div class="blood-grp-text">
    <h3>B+</h3>
    <h5>Low</h5>
</div>
"""

def test_parse_blood_levels_elementor_markup():
    levels = parse_blood_levels(SAMPLE_ELEMENTOR_HTML)
    assert len(levels) == 8
    assert levels["A+"] == "Healthy"
    assert levels["B+"] == "High"
    assert levels["O+"] == "Healthy"
    assert levels["AB+"] == "Healthy"
    assert levels["A-"] == "Healthy"
    assert levels["B-"] == "Moderate"
    assert levels["O-"] == "Moderate"
    assert levels["AB-"] == "Moderate"

def test_parse_blood_levels_legacy_markup():
    levels = parse_blood_levels(SAMPLE_LEGACY_HTML)
    assert len(levels) == 2
    assert levels["A+"] == "Healthy"
    assert levels["B+"] == "Low"

def test_parse_blood_levels_unrecognized_markup_raises():
    with pytest.raises(ValueError, match="No blood level data could be extracted"):
        parse_blood_levels("<html><body><div>No blood information here</div></body></html>")

@patch("fetch_blood.requests.get")
def test_fetch_blood_levels_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_ELEMENTOR_HTML
    mock_response.content = SAMPLE_ELEMENTOR_HTML.encode("utf-8")
    mock_get.return_value = mock_response

    levels = fetch_blood_levels()
    assert len(levels) == 8
    assert levels["A+"] == "Healthy"
    mock_get.assert_called_once()
    assert "headers" in mock_get.call_args[1]
    assert "User-Agent" in mock_get.call_args[1]["headers"]

@patch("fetch_blood.requests.get")
def test_fetch_blood_levels_http_error(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("Internal Server Error")
    mock_get.return_value = mock_response

    with pytest.raises(Exception):
        fetch_blood_levels()

def test_write_to_markdown_valid(tmp_path):
    output_file = tmp_path / "README.md"
    sample_levels = {
        "A+": "Healthy",
        "B+": "High",
        "O+": "Healthy",
        "AB+": "Healthy",
        "A-": "Healthy",
        "B-": "Moderate",
        "O-": "Moderate",
        "AB-": "Moderate",
    }

    write_to_markdown(sample_levels, output_path=str(output_file))
    assert output_file.exists()

    content = output_file.read_text()
    assert "Singapore Blood Levels" in content
    assert "| Blood Type | Level     |" in content
    assert "| A+     | Healthy |" in content
    assert "| B+     | High |" in content
    assert "| AB-     | Moderate |" in content

def test_write_to_markdown_empty_raises(tmp_path):
    output_file = tmp_path / "README.md"
    with pytest.raises(ValueError, match="blood_levels cannot be empty"):
        write_to_markdown({}, output_path=str(output_file))
    assert not output_file.exists()

def test_default_url_is_www_redcross_sg():
    from fetch_blood import DEFAULT_URL
    assert DEFAULT_URL == "https://www.redcross.sg/"

def test_parse_last_update_date():
    from fetch_blood import parse_last_update_date
    html = '<p class="blood-stock-last-update-text">Last blood stock update: 25 September 2026</p>'
    date_str = parse_last_update_date(html)
    assert date_str == "25 September 2026"

def test_write_to_markdown_includes_source_update(tmp_path):
    output_file = tmp_path / "README.md"
    sample_levels = {"A+": "Healthy"}
    write_to_markdown(sample_levels, output_path=str(output_file), source_last_updated="25 September 2026")
    content = output_file.read_text()
    assert "Red Cross Singapore official update: 25 September 2026" in content
    assert "| A+     | Healthy |" in content

@patch("fetch_blood.time.sleep")
@patch("fetch_blood.requests.get")
def test_fetch_blood_data_retries_on_read_timeout_then_succeeds(mock_get, mock_sleep):
    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.text = (
        SAMPLE_ELEMENTOR_HTML
        + '<p class="blood-stock-last-update-text">Last blood stock update: 25 Nov 2026</p>'
    )
    mock_get.side_effect = [
        requests.exceptions.ReadTimeout("timed out"),
        ok_response,
    ]

    levels, last_update = fetch_blood_data()
    assert len(levels) == 8
    assert last_update == "25 Nov 2026"
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(5.0)

@patch("fetch_blood.time.sleep")
@patch("fetch_blood.requests.get")
def test_fetch_blood_data_exhausts_retries_on_timeout(mock_get, mock_sleep):
    mock_get.side_effect = requests.exceptions.ReadTimeout("timed out")

    with pytest.raises(requests.exceptions.ReadTimeout):
        fetch_blood_data(max_retries=2, backoff_seconds=5.0)

    assert mock_get.call_count == 3
    assert [call.args[0] for call in mock_sleep.call_args_list] == [5.0, 10.0]

@patch("fetch_blood.time.sleep")
@patch("fetch_blood.requests.get")
def test_fetch_blood_data_retries_on_retryable_http_status(mock_get, mock_sleep):
    err_response = MagicMock()
    err_response.status_code = 524
    err_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "524 Origin Time-out", response=err_response
    )

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.text = SAMPLE_ELEMENTOR_HTML
    mock_get.side_effect = [err_response, ok_response]

    levels, _ = fetch_blood_data()
    assert len(levels) == 8
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(5.0)

@patch("fetch_blood.time.sleep")
@patch("fetch_blood.requests.get")
def test_fetch_blood_data_does_not_retry_on_404(mock_get, mock_sleep):
    err_response = MagicMock()
    err_response.status_code = 404
    err_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found", response=err_response
    )
    mock_get.return_value = err_response

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_blood_data()

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()

@patch("fetch_blood.time.sleep")
@patch("fetch_blood.requests.get")
def test_fetch_blood_data_retries_on_transient_empty_markup(mock_get, mock_sleep):
    empty_response = MagicMock()
    empty_response.status_code = 200
    empty_response.text = "<html><body>Maintenance in progress</body></html>"

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.text = SAMPLE_ELEMENTOR_HTML
    mock_get.side_effect = [empty_response, ok_response]

    levels, _ = fetch_blood_data()
    assert len(levels) == 8
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(5.0)

def test_parse_blood_levels_normalizes_casing():
    html = """
    <div class="blood-level-card" blood-type="a-" blood-level="low"></div>
    <div class="blood-level-card" blood-type="B-" blood-level="healthy"></div>
    <div class="blood-level-card" blood-type="o-" blood-level="very low"></div>
    """
    levels = parse_blood_levels(html)
    assert levels == {
        "A-": "Low",
        "B-": "Healthy",
        "O-": "Very Low",
    }

def test_parse_last_update_date_normalizes_nbsp_whitespace():
    from fetch_blood import parse_last_update_date
    html = '<p class="blood-stock-last-update-text">Last blood stock update:&nbsp;25  Nov\xa02026</p>'
    assert parse_last_update_date(html) == "25 Nov 2026"

