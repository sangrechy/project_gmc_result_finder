import os
import urllib.parse

BASE_API_URL = os.getenv("API_BASE_URL", "https://cms2api.tnmgrmu.ac.in/Api/index.php")

LOGIN_ENDPOINT = f"{BASE_API_URL}/Login/appLogin"
COURSE_TERM_ENDPOINT = f"{BASE_API_URL}/Login/loadCourseTerm"
RESULT_ENDPOINT = f"{BASE_API_URL}/StudentPreview/previewGradeMarkAllCourse"
AVAILABLE_RESULTS_ENDPOINT = f"{BASE_API_URL}/Login/loadResultData"

def build_login_url(registration_no: str, login_type: str = "result") -> str:
    encoded_reg = urllib.parse.quote(str(registration_no).strip())
    encoded_type = urllib.parse.quote(str(login_type).strip())
    return f"{LOGIN_ENDPOINT}?registration_no={encoded_reg}&login_type={encoded_type}"

def build_course_term_url(registration_no: str, exam_session: str) -> str:
    encoded_reg = urllib.parse.quote(str(registration_no).strip())
    encoded_session = urllib.parse.quote(str(exam_session).strip())
    return f"{COURSE_TERM_ENDPOINT}?registration_no={encoded_reg}&exam_session={encoded_session}"

def build_result_url(registration_no: str, term_code: str) -> str:
    encoded_reg = urllib.parse.quote(str(registration_no).strip())
    encoded_term = urllib.parse.quote(str(term_code).strip())
    return f"{RESULT_ENDPOINT}?registration_no={encoded_reg}&term_code={encoded_term}"
