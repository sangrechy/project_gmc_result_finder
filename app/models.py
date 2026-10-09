from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class BatchRequest(BaseModel):
    registration_numbers: Optional[List[str]] = None
    start_reg_no: Optional[int] = None
    end_reg_no: Optional[int] = None
    force_refresh: bool = False

class BatchStudentItem(BaseModel):
    registration_no: str
    student_name: str
    institution_name: Optional[str] = ""
    term_name: Optional[str] = ""
    overall_result: str
    overall_marks: Optional[str] = ""
    source: str
    error: Optional[str] = None

class BatchResponse(BaseModel):
    total_requested: int
    successful_count: int
    failed_count: int
    progress_text: str
    results: List[Dict[str, Any]]
