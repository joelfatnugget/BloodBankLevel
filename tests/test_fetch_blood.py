import os
import pytest
from unittest.mock import patch, MagicMock
from fetch_blood import parse_blood_levels, fetch_blood_levels, write_to_markdown

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

