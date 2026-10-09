import os
import sys
import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import config
from app.api import patch_socket
from app.cache import cache
from app.routes import router as api_router
from app.client import api_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    patch_socket()
    yield

app = FastAPI(
    title="FastResults",
    version="2.0.0",
    lifespan=lifespan
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(api_router)

@app.get("/")
def serve_index():
    return FileResponse(static_dir / "index.html")

def run_cli_get(reg_no: str, refresh: bool = False):
    clean_reg = str(reg_no).strip()

    if not refresh:
        cached = cache.get(clean_reg)
        if cached:
            print_result_summary(cached)
            return

    async def _fetch():
        return await api_client.fetch_result(clean_reg)

    try:
        data = asyncio.run(_fetch())
        cache.set(
            reg_no=clean_reg,
            data=data,
            student_name=data.get("student_name", ""),
            result_status=data.get("overall_result", ""),
            total_marks=str(data.get("overall_marks", ""))
        )
        print_result_summary(data)
    except Exception as e:
        print(f"Error fetching result: {e}")

def print_result_summary(data: dict):
    print("=" * 65)
    print(f" Student Name : {data.get('student_name')}")
    print(f" Reg Number   : {data.get('registration_no')}")
    print(f" Institution  : {data.get('institution_name')}")
    print(f" Course       : {data.get('course')}")
    print(f" Term         : {data.get('term_name')}")
    print(f" Exam Session : {data.get('exam_session')}")
    print(f" Published On : {data.get('result_published_date')}")
    print(f" Result       : {data.get('overall_result')}")
    if data.get('overall_marks'):
        print(f" Total / Marks: {data.get('overall_marks')}%")
    print("-" * 65)
    print(f"{'Subject':<32} {'Marks Breakdown':<20} {'Status'}")
    print("-" * 65)
    for subj in data.get("subjects", []):
        s_name = subj.get("subject_name", "")[:30]
        s_res = subj.get("result", "")
        papers = subj.get("papers", [])
        p_summary = ", ".join([f"{p.get('paper_name')}: {p.get('obtained_mark')}" for p in papers[:2]])
        print(f"{s_name:<32} {p_summary:<20} {s_res}")
    print("=" * 65 + "\n")

def run_cli_batch(start_reg: int, end_reg: int, csv_out: str = None, refresh: bool = False):
    reg_list = [str(r) for r in range(start_reg, end_reg + 1)]
    total = len(reg_list)

    sem = asyncio.Semaphore(config.BATCH_CONCURRENCY)
    collected = 0
    results = []

    async def _fetch_one(r: str):
        async with sem:
            if not refresh:
                cached = cache.get(r)
                if cached:
                    return cached
            try:
                res = await api_client.fetch_result(r)
                cache.set(r, res)
                return res
            except Exception as e:
                return {
                    "registration_no": r,
                    "student_name": "Not Found / Error",
                    "overall_result": "FAIL",
                    "error": str(e)
                }

    async def _run_all():
        nonlocal collected
        tasks = [asyncio.create_task(_fetch_one(r)) for r in reg_list]
        for coro in asyncio.as_completed(tasks):
            item = await coro
            collected += 1
            pct = round((collected / total) * 100, 1)
            reg_display = item.get("registration_no", "")
            name_display = item.get("student_name", "N/A")[:24]
            status_display = item.get("overall_result", "")
            print(f"[{pct}% ({collected} out of {total} data collected)] {reg_display}: {name_display} ({status_display})", flush=True)
            results.append(item)
        return results

    asyncio.run(_run_all())

    print("\n" + "=" * 80)
    print(f"{'Roll No':<16} {'Student Name':<28} {'Term':<18} {'Result':<10} {'Marks'}")
    print("=" * 80)
    for r in results:
        reg = r.get("registration_no", "")
        name = r.get("student_name", "N/A")[:26]
        term = r.get("term_name", "")[:16]
        res = r.get("overall_result", "")
        marks = r.get("overall_marks", "-")
        print(f"{reg:<16} {name:<28} {term:<18} {res:<10} {marks}")
    print("=" * 80)

    if csv_out:
        import csv
        with open(csv_out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Roll No", "Student Name", "Institution", "Course", "Term", "Exam Session", "Result", "Marks %"])
            for r in results:
                writer.writerow([
                    r.get("registration_no", ""),
                    r.get("student_name", ""),
                    r.get("institution_name", ""),
                    r.get("course", ""),
                    r.get("term_name", ""),
                    r.get("exam_session", ""),
                    r.get("overall_result", ""),
                    r.get("overall_marks", "")
                ])
        print(f"\nResults exported to: {csv_out}")

def main():
    parser = argparse.ArgumentParser(description="FastResults - Result Query Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    serve_parser = subparsers.add_parser("serve", help="Run web server")
    serve_parser.add_argument("--host", default=config.HOST)
    serve_parser.add_argument("--port", type=int, default=config.PORT)

    get_parser = subparsers.add_parser("get", help="Query single student result")
    get_parser.add_argument("reg_no")
    get_parser.add_argument("--refresh", action="store_true")

    batch_parser = subparsers.add_parser("batch", help="Batch query roll number range")
    batch_parser.add_argument("start_reg", type=int)
    batch_parser.add_argument("end_reg", type=int)
    batch_parser.add_argument("--csv", default=None)
    batch_parser.add_argument("--refresh", action="store_true")

    subparsers.add_parser("clear-cache", help="Clear local cache")

    args = parser.parse_args()

    if args.command == "serve" or not args.command:
        host = getattr(args, "host", config.HOST)
        port = getattr(args, "port", config.PORT)
        uvicorn.run("main:app", host=host, port=port, reload=False)
    elif args.command == "get":
        run_cli_get(args.reg_no, refresh=args.refresh)
    elif args.command == "batch":
        run_cli_batch(args.start_reg, args.end_reg, csv_out=args.csv, refresh=args.refresh)
    elif args.command == "clear-cache":
        cache.clear()
        print("Cache cleared.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
