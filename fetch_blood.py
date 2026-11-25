import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

DEFAULT_URL = "https://www.redcross.sg/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT: tuple[int, int] = (15, 60)
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_SECONDS: float = 5.0
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset(
    {429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
)


def _build_headers(user_agent: str) -> dict[str, str]:
    """Build browser-like request headers for Red Cross Singapore."""
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

def parse_blood_levels(html_content: str) -> dict[str, str]:
    """Parse blood stock levels from HTML markup supporting both current Elementor and legacy structures."""
    soup = BeautifulSoup(html_content, "html.parser")
    blood_levels = {}

    # Primary strategy: Current Red Cross markup with blood-level-card or blood-type attribute
    cards = soup.find_all(class_="blood-level-card") or soup.find_all(attrs={"blood-type": True})
    for card in cards:
        blood_type = card.get("blood-type")
        blood_level = card.get("blood-level")

        if not blood_type:
            text_el = card.find(class_="blood-level-text") or card.find("h3")
            if text_el:
                blood_type = text_el.text.strip()

        if not blood_level:
            status_el = card.find(class_="blood-level-status") or card.find("h5")
            if status_el:
                blood_level = status_el.text.strip()

        if blood_type and blood_level:
            blood_levels[blood_type.strip()] = blood_level.strip()

    # Fallback strategy: Legacy markup with blood-grp-text class
    if not blood_levels:
        legacy_elements = soup.find_all(class_="blood-grp-text")
        for element in legacy_elements:
            h3 = element.find("h3")
            h5 = element.find("h5")
            if h3 and h5:
                blood_type = h3.text.strip()
                blood_level = h5.text.strip()
                if blood_type and blood_level:
                    blood_levels[blood_type] = blood_level

    if not blood_levels:
        raise ValueError("No blood level data could be extracted from page markup.")

    return blood_levels

def parse_last_update_date(html_content: str) -> str | None:
    """Extract official last update date published on Red Cross Singapore website."""
    soup = BeautifulSoup(html_content, "html.parser")
    update_el = soup.find(class_="blood-stock-last-update-text")
    text_to_check = update_el.text if update_el else html_content

    match = re.search(r"Last blood stock update:\s*([^<\n\r]+)", text_to_check, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def fetch_blood_levels(
    url: str = DEFAULT_URL,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int | float | tuple[int | float, int | float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> dict[str, str]:
    """Fetch and parse live blood levels from Red Cross Singapore."""
    levels, _ = fetch_blood_data(
        url=url,
        user_agent=user_agent,
        timeout=timeout,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )
    return levels

def fetch_blood_data(
    url: str = DEFAULT_URL,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int | float | tuple[int | float, int | float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> tuple[dict[str, str], str | None]:
    """Fetch blood levels and official publication timestamp with exponential backoff retries."""
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    headers = _build_headers(user_agent)
    total_attempts = max_retries + 1

    for attempt in range(1, total_attempts + 1):
        response = None
        retry_error: Exception | None = None
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            levels = parse_blood_levels(response.text)
            last_update = parse_last_update_date(response.text)
            return levels, last_update
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code not in RETRYABLE_STATUS_CODES or attempt > max_retries:
                raise
            retry_error = exc
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ContentDecodingError,
            ValueError,
        ) as exc:
            if attempt > max_retries:
                if isinstance(exc, ValueError) and response is not None:
                    print(
                        f"Parse failed on final attempt (status={response.status_code}, "
                        f"body_length={len(response.text)}).",
                        flush=True,
                    )
                raise
            retry_error = exc

        delay = backoff_seconds * (2 ** (attempt - 1))
        print(
            f"Attempt {attempt}/{total_attempts} failed "
            f"({type(retry_error).__name__}: {retry_error}). "
            f"Retrying in {delay:.1f}s...",
            flush=True,
        )
        time.sleep(delay)

    raise RuntimeError("Unreachable: fetch_blood_data exited retry loop without returning or raising.")

def write_to_markdown(
    blood_levels: dict[str, str],
    output_path: str = "README.md",
    timezone_str: str = "Asia/Singapore",
    source_last_updated: str | None = None
) -> None:
    """Format extracted blood levels as a Markdown table and save to disk."""
    if not blood_levels:
        raise ValueError("blood_levels cannot be empty")

    sg_timezone = pytz.timezone(timezone_str)
    current_time = datetime.now(sg_timezone)
    formatted_time = current_time.strftime("%d %b %Y %H:%M:%S GMT+8")

    markdown_content = "Singapore Blood Levels\n Please donate to the Blood Bank if you are able to do so!\n"
    markdown_content += "================================================================================================================================\n\n"
    markdown_content += f"### Blood Levels (Updated: {formatted_time})\n"
    if source_last_updated:
        markdown_content += f"> Red Cross Singapore official update: {source_last_updated}\n\n"
    markdown_content += "| Blood Type | Level     |\n"
    markdown_content += "|------------|-----------|\n"
    for blood_type, level in blood_levels.items():
        markdown_content += f"| {blood_type}     | {level} |\n"

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(markdown_content)

if __name__ == "__main__":
    levels, source_update = fetch_blood_data()
    print("Scraped blood levels:", levels)
    print("Official update date:", source_update)
    write_to_markdown(levels, source_last_updated=source_update)
