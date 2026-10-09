from typing import Optional, Dict, Any
import httpx
from app import config
from app.api import (
    patch_socket,
    fetch_login_session,
    fetch_course_terms,
    fetch_grade_preview,
    parse_grade_preview_response,
)

patch_socket()

class TNMGRMUClient:
    def __init__(self, timeout: float = None):
        self.timeout = timeout or config.REQUEST_TIMEOUT
        self.max_retries = config.MAX_RETRIES
        self.retry_backoff = config.RETRY_BACKOFF_SECONDS

    async def fetch_result(self, reg_no: str, term_code: Optional[str] = None) -> Dict[str, Any]:
        reg_clean = str(reg_no).strip()
        if not reg_clean:
            raise ValueError("Registration number cannot be empty.")

        async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
            login_info = await fetch_login_session(
                client=client,
                registration_no=reg_clean,
                timeout=self.timeout,
                max_retries=self.max_retries,
                retry_backoff=self.retry_backoff,
            )
            exam_session = login_info.get("exam_session")
            if not exam_session:
                raise ValueError("Exam session could not be resolved from university response.")

            if not term_code:
                terms = await fetch_course_terms(
                    client=client,
                    registration_no=reg_clean,
                    exam_session=exam_session,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                    retry_backoff=self.retry_backoff,
                )
                if not terms:
                    raise ValueError(f"No course terms available for registration number {reg_clean}.")
                term_code = terms[0]

            raw_result = await fetch_grade_preview(
                client=client,
                registration_no=reg_clean,
                term_code=term_code,
                timeout=self.timeout,
                max_retries=self.max_retries,
                retry_backoff=self.retry_backoff,
            )
            return parse_grade_preview_response(raw_result)

api_client = TNMGRMUClient()
