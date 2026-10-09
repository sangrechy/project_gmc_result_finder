import asyncio
from typing import Dict, Any, List
import httpx
from .endpoints import (
    build_login_url,
    build_course_term_url,
    build_result_url,
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://cms2api.tnmgrmu.ac.in/",
    "Connection": "keep-alive"
}

async def _send_request_with_retry(
    client: httpx.AsyncClient,
    url: str,
    action_name: str,
    headers: Dict[str, str] = None,
    timeout: float = 35.0,
    max_retries: int = 3,
    retry_backoff: float = 1.5
) -> httpx.Response:
    req_headers = headers or DEFAULT_HEADERS
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            response = await client.get(url, headers=req_headers, timeout=timeout)
            if response.status_code == 200:
                return response
            last_exc = ValueError(f"{action_name} failed with status {response.status_code}")
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt < max_retries:
                await asyncio.sleep(retry_backoff * attempt)
    raise ValueError(f"{action_name} failed: {last_exc}")

async def fetch_login_session(
    client: httpx.AsyncClient,
    registration_no: str,
    headers: Dict[str, str] = None,
    timeout: float = 35.0,
    max_retries: int = 3,
    retry_backoff: float = 1.5
) -> Dict[str, Any]:
    url = build_login_url(registration_no)
    response = await _send_request_with_retry(
        client, url, "Login session request", headers, timeout, max_retries, retry_backoff
    )
    data = response.json()
    if data.get("resultcode") != "200":
        msg = data.get("resultmessage") or "Registration number not found or not published."
        raise ValueError(msg)
    return data.get("result", {})

async def fetch_course_terms(
    client: httpx.AsyncClient,
    registration_no: str,
    exam_session: str,
    headers: Dict[str, str] = None,
    timeout: float = 35.0,
    max_retries: int = 3,
    retry_backoff: float = 1.5
) -> List[str]:
    url = build_course_term_url(registration_no, exam_session)
    response = await _send_request_with_retry(
        client, url, "Course term request", headers, timeout, max_retries, retry_backoff
    )
    data = response.json()
    terms: List[str] = []
    if data.get("resultcode") == "200" and isinstance(data.get("result"), list):
        for item in data.get("result"):
            term_val = item.get("course_term")
            if term_val and term_val not in terms:
                terms.append(term_val)
    return terms

async def fetch_grade_preview(
    client: httpx.AsyncClient,
    registration_no: str,
    term_code: str,
    headers: Dict[str, str] = None,
    timeout: float = 35.0,
    max_retries: int = 3,
    retry_backoff: float = 1.5
) -> Dict[str, Any]:
    url = build_result_url(registration_no, term_code)
    response = await _send_request_with_retry(
        client, url, "Result preview request", headers, timeout, max_retries, retry_backoff
    )
    data = response.json()
    if data.get("resultcode") != "200":
        msg = data.get("resultmessage") or "No exam results found for this registration number."
        raise ValueError(msg)
    return data
