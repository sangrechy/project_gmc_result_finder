from typing import Dict, Any, List

def parse_grade_preview_response(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    result_container = raw_data.get("result", {})
    students = result_container.get("student", [])
    if not students:
        raise ValueError("No student records found in university response.")

    student = students[0]
    subjects: List[Dict[str, Any]] = []
    all_passed = True
    overall_percentage = ""

    raw_subjects = student.get("subject", [])
    for subj in raw_subjects:
        subject_name = subj.get("subject_name", "").replace("\n", " ").strip()
        subject_code = subj.get("subject_code", "").replace("\n", " ").strip()
        subject_result = subj.get("result", "N/A").strip().upper()

        if subject_result != "PASS":
            all_passed = False

        papers: List[Dict[str, str]] = []
        for paper in subj.get("paper", []):
            paper_name = paper.get("paper_name", "").strip()
            obtained_mark = paper.get("obtained_mark", "").strip()
            min_marks = paper.get("min_marks", "").strip()
            max_marks = paper.get("max_marks", "").strip()
            words = paper.get("words", "").strip()

            papers.append({
                "paper_name": paper_name,
                "obtained_mark": obtained_mark,
                "min_marks": min_marks,
                "max_marks": max_marks,
                "words": words
            })

            if "%" in paper_name and not overall_percentage and obtained_mark:
                overall_percentage = obtained_mark

        subjects.append({
            "subject_code": subject_code,
            "subject_name": subject_name,
            "papers": papers,
            "result": subject_result
        })

    overall_status = "PASS" if (all_passed and len(subjects) > 0) else "FAIL"

    return {
        "registration_no": str(student.get("registration_no", "")).strip(),
        "student_name": str(student.get("student_name", "")).strip(),
        "course": str(student.get("course", "")).strip(),
        "institution_name": str(student.get("institution_name", "")).strip(),
        "exam_session": str(student.get("exam_session_name", "")).strip(),
        "regulation": str(student.get("regulation", "")).strip(),
        "term_name": str(student.get("term_name", "")).strip(),
        "result_published_date": str(student.get("result_publish_from_date", "")).strip(),
        "subjects": subjects,
        "overall_result": overall_status,
        "overall_marks": overall_percentage,
        "source": "live"
    }
