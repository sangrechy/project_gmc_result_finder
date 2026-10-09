import asyncio
import io
import csv
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import xlsxwriter

from app import config
from app.cache import cache
from app.client import api_client
from app.models import BatchRequest

router = APIRouter(prefix="/api")

@router.get("/result/{reg_no}")
async def get_student_result(
    reg_no: str,
    refresh: bool = Query(False),
    term: Optional[str] = Query(None)
):
    reg_clean = str(reg_no).strip()
    if not reg_clean:
        raise HTTPException(status_code=400, detail="Registration number is required.")

    if not refresh:
        cached_data = cache.get(reg_clean, term)
        if cached_data:
            return cached_data

    try:
        result_data = await api_client.fetch_result(reg_clean, term_code=term)
        cache.set(
            reg_no=reg_clean,
            data=result_data,
            term_code=term or result_data.get("term_name"),
            student_name=result_data.get("student_name", ""),
            result_status=result_data.get("overall_result", ""),
            total_marks=str(result_data.get("overall_marks", ""))
        )
        return result_data
    except Exception as e:
        err_msg = str(e)
        status_code = 404 if "not found" in err_msg.lower() or "invalid" in err_msg.lower() else 502
        raise HTTPException(status_code=status_code, detail=f"Query error: {err_msg}")

@router.post("/batch")
async def batch_fetch_results(payload: BatchRequest):
    reg_list: List[str] = []
    if payload.registration_numbers:
        reg_list = [str(r).strip() for r in payload.registration_numbers if str(r).strip()]
    elif payload.start_reg_no and payload.end_reg_no:
        if payload.end_reg_no < payload.start_reg_no:
            raise HTTPException(status_code=400, detail="End roll number cannot be less than start roll number.")
        if (payload.end_reg_no - payload.start_reg_no) > 500:
            raise HTTPException(status_code=400, detail="Batch range exceeds maximum limit of 500 numbers.")
        reg_list = [str(r) for r in range(payload.start_reg_no, payload.end_reg_no + 1)]

    if not reg_list:
        raise HTTPException(status_code=400, detail="No registration numbers provided.")

    sem = asyncio.Semaphore(config.BATCH_CONCURRENCY)

    async def _query_single(r: str) -> Dict[str, Any]:
        async with sem:
            if not payload.force_refresh:
                cached = cache.get(r)
                if cached:
                    return cached
            try:
                res = await api_client.fetch_result(r)
                cache.set(
                    reg_no=r,
                    data=res,
                    student_name=res.get("student_name", ""),
                    result_status=res.get("overall_result", ""),
                    total_marks=str(res.get("overall_marks", ""))
                )
                return res
            except Exception as e:
                return {
                    "registration_no": r,
                    "student_name": "Not Found / Error",
                    "overall_result": "FAIL",
                    "overall_marks": "-",
                    "source": "error",
                    "error": str(e)
                }

    tasks = [_query_single(r) for r in reg_list]
    results = await asyncio.gather(*tasks)

    success_cnt = sum(1 for item in results if item.get("overall_result") in ("PASS", "FAIL") and item.get("student_name") != "Not Found / Error")
    failed_cnt = len(results) - success_cnt
    total_cnt = len(reg_list)

    return {
        "total_requested": total_cnt,
        "successful_count": success_cnt,
        "failed_count": failed_cnt,
        "progress_text": f"100% ({total_cnt} out of {total_cnt} data collected)",
        "results": results
    }

@router.get("/batch/stream")
async def batch_fetch_stream(
    start: int = Query(...),
    end: int = Query(...),
    refresh: bool = Query(False)
):
    if end < start:
        raise HTTPException(status_code=400, detail="End roll cannot be less than start roll.")
    if (end - start) > 500:
        raise HTTPException(status_code=400, detail="Batch limit exceeded (max 500).")

    reg_list = [str(r) for r in range(start, end + 1)]
    total_count = len(reg_list)
    sem = asyncio.Semaphore(config.BATCH_CONCURRENCY)

    async def event_generator():
        collected = 0
        success_cnt = 0
        failed_cnt = 0

        async def _fetch_item(reg: str):
            async with sem:
                if not refresh:
                    cached = cache.get(reg)
                    if cached:
                        return cached
                try:
                    res = await api_client.fetch_result(reg)
                    cache.set(
                        reg_no=reg,
                        data=res,
                        student_name=res.get("student_name", ""),
                        result_status=res.get("overall_result", ""),
                        total_marks=str(res.get("overall_marks", ""))
                    )
                    return res
                except Exception as e:
                    return {
                        "registration_no": reg,
                        "student_name": "Not Found / Error",
                        "overall_result": "FAIL",
                        "overall_marks": "-",
                        "source": "error",
                        "error": str(e)
                    }

        tasks = [asyncio.create_task(_fetch_item(r)) for r in reg_list]
        for coro in asyncio.as_completed(tasks):
            res = await coro
            collected += 1
            if res.get("overall_result") in ("PASS", "FAIL") and res.get("student_name") != "Not Found / Error":
                success_cnt += 1
            else:
                failed_cnt += 1

            percent = round((collected / total_count) * 100, 1)
            event_payload = {
                "type": "progress",
                "collected": collected,
                "total": total_count,
                "percent": percent,
                "progress_text": f"{percent}% ({collected} out of {total_count} data collected)",
                "item": res
            }
            yield f"data: {json.dumps(event_payload)}\n\n"

        done_payload = {
            "type": "complete",
            "collected": collected,
            "total": total_count,
            "percent": 100.0,
            "progress_text": f"100% ({collected} out of {total_count} data collected)",
            "successful_count": success_cnt,
            "failed_count": failed_cnt
        }
        yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/batch/export/csv")
async def export_batch_csv(results: List[Dict[str, Any]]):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll No", "Student Name", "Institution", "Course",
        "Term", "Exam Session", "Result", "Marks %", "Source"
    ])

    for r in results:
        writer.writerow([
            r.get("registration_no", ""),
            r.get("student_name", ""),
            r.get("institution_name", ""),
            r.get("course", ""),
            r.get("term_name", ""),
            r.get("exam_session", ""),
            r.get("overall_result", ""),
            r.get("overall_marks", ""),
            r.get("source", "")
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"}
    )

@router.post("/batch/export/excel")
async def export_batch_excel(results: List[Dict[str, Any]]):
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet("Batch Results")

    fmt_header = wb.add_format({
        'bold': True, 'bg_color': '#2f5597', 'font_color': '#ffffff',
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    fmt_pass = wb.add_format({
        'bold': True, 'bg_color': '#e2efda', 'font_color': '#276a3c',
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    fmt_fail = wb.add_format({
        'bold': True, 'bg_color': '#ffc7ce', 'font_color': '#9c0006',
        'border': 1, 'align': 'center', 'valign': 'vcenter'
    })
    fmt_center = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
    fmt_left = wb.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})

    headers = [
        "S.No", "Register No", "Student Name", "Institution",
        "Course", "Term", "Exam Session", "Overall Result", "Marks %"
    ]
    for col_idx, h in enumerate(headers):
        ws.write(0, col_idx, h, fmt_header)

    ws.set_column(0, 0, 8)
    ws.set_column(1, 1, 16)
    ws.set_column(2, 2, 26)
    ws.set_column(3, 3, 35)
    ws.set_column(4, 4, 30)
    ws.set_column(5, 6, 20)
    ws.set_column(7, 8, 14)

    for row_idx, r in enumerate(results, start=1):
        ws.write(row_idx, 0, row_idx, fmt_center)
        ws.write(row_idx, 1, r.get("registration_no", ""), fmt_center)
        ws.write(row_idx, 2, r.get("student_name", ""), fmt_left)
        ws.write(row_idx, 3, r.get("institution_name", ""), fmt_left)
        ws.write(row_idx, 4, r.get("course", ""), fmt_left)
        ws.write(row_idx, 5, r.get("term_name", ""), fmt_center)
        ws.write(row_idx, 6, r.get("exam_session", ""), fmt_center)

        res_status = r.get("overall_result", "")
        if res_status == "PASS":
            ws.write(row_idx, 7, res_status, fmt_pass)
        elif res_status == "FAIL":
            ws.write(row_idx, 7, res_status, fmt_fail)
        else:
            ws.write(row_idx, 7, res_status, fmt_center)

        ws.write(row_idx, 8, r.get("overall_marks", ""), fmt_center)

    wb.close()
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=results.xlsx"}
    )
