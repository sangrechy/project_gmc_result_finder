import json
import sqlite3
import time
import threading
from typing import Optional, Dict, Any
from app import config

_lock = threading.Lock()

class CacheManager:
    def __init__(self, db_path=None, default_ttl=None):
        self.db_path = db_path or config.CACHE_DB_PATH
        self.default_ttl = default_ttl or config.DEFAULT_CACHE_TTL_SECONDS
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0
        self._init_sqlite()

    def _init_sqlite(self):
        with _lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_results_cache (
                    cache_key TEXT PRIMARY KEY,
                    registration_no TEXT NOT NULL,
                    term_code TEXT NOT NULL,
                    student_name TEXT,
                    result_status TEXT,
                    total_marks TEXT,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reg_no ON exam_results_cache (registration_no)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON exam_results_cache (expires_at)")
            conn.commit()
            conn.close()

    def _make_key(self, reg_no: str, term_code: Optional[str] = None) -> str:
        term_clean = (term_code or "DEFAULT").strip().upper()
        return f"{str(reg_no).strip().upper()}:{term_clean}"

    def get(self, reg_no: str, term_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        key = self._make_key(reg_no, term_code)
        now = time.time()

        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if now < entry["expires_at"]:
                entry["hit_count"] += 1
                entry["last_accessed"] = now
                self._hits += 1
                res = dict(entry["payload"])
                res["_cache_info"] = {
                    "source": "memory_cache",
                    "cached_at": entry["created_at"],
                    "expires_at": entry["expires_at"],
                    "ttl_remaining_sec": int(entry["expires_at"] - now),
                    "hit_count": entry["hit_count"]
                }
                return res
            else:
                del self._memory_cache[key]

        with _lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT payload_json, created_at, expires_at, hit_count 
                FROM exam_results_cache 
                WHERE cache_key = ? OR (registration_no = ? AND ? = 'DEFAULT')
                LIMIT 1
            """, (key, str(reg_no).strip().upper(), (term_code or "DEFAULT").strip().upper()))
            row = cursor.fetchone()

            if row:
                payload_json, created_at, expires_at, hit_count = row
                if now < expires_at:
                    new_hits = hit_count + 1
                    cursor.execute("""
                        UPDATE exam_results_cache 
                        SET hit_count = ?, last_accessed = ? 
                        WHERE cache_key = ?
                    """, (new_hits, now, key))
                    conn.commit()
                    conn.close()

                    payload = json.loads(payload_json)
                    self._memory_cache[key] = {
                        "payload": payload,
                        "created_at": created_at,
                        "expires_at": expires_at,
                        "last_accessed": now,
                        "hit_count": new_hits
                    }
                    self._hits += 1
                    payload["_cache_info"] = {
                        "source": "sqlite_cache",
                        "cached_at": created_at,
                        "expires_at": expires_at,
                        "ttl_remaining_sec": int(expires_at - now),
                        "hit_count": new_hits
                    }
                    return payload
                else:
                    cursor.execute("DELETE FROM exam_results_cache WHERE cache_key = ?", (key,))
                    conn.commit()

            conn.close()

        self._misses += 1
        return None

    def set(
        self,
        reg_no: str,
        data: Dict[str, Any],
        term_code: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        student_name: str = "",
        result_status: str = "",
        total_marks: str = ""
    ):
        clean_data = {k: v for k, v in data.items() if not k.startswith("_")}
        key = self._make_key(reg_no, term_code)
        now = time.time()
        ttl = ttl_seconds or self.default_ttl
        expires_at = now + ttl

        if len(self._memory_cache) >= config.MEMORY_CACHE_MAX_SIZE:
            oldest_key = min(self._memory_cache.keys(), key=lambda k: self._memory_cache[k]["last_accessed"])
            del self._memory_cache[oldest_key]

        self._memory_cache[key] = {
            "payload": clean_data,
            "created_at": now,
            "expires_at": expires_at,
            "last_accessed": now,
            "hit_count": 0
        }

        with _lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO exam_results_cache (
                    cache_key, registration_no, term_code, student_name,
                    result_status, total_marks, payload_json, created_at,
                    expires_at, last_accessed, hit_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                str(reg_no).strip().upper(),
                (term_code or "DEFAULT").strip().upper(),
                student_name or clean_data.get("student_name", ""),
                result_status or clean_data.get("overall_result", ""),
                total_marks or str(clean_data.get("overall_marks", "")),
                json.dumps(clean_data),
                now,
                expires_at,
                now,
                0
            ))
            conn.commit()
            conn.close()

    def clear(self):
        self._memory_cache.clear()
        with _lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM exam_results_cache")
            conn.commit()
            conn.close()

    def stats(self) -> Dict[str, Any]:
        with _lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM exam_results_cache")
            total_db = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM exam_results_cache WHERE expires_at > ?", (time.time(),))
            active_db = cursor.fetchone()[0]
            conn.close()

        total_reqs = self._hits + self._misses
        hit_ratio = round((self._hits / total_reqs * 100), 1) if total_reqs > 0 else 0.0

        return {
            "memory_cache_entries": len(self._memory_cache),
            "sqlite_active_entries": active_db,
            "sqlite_total_entries": total_db,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio_pct": hit_ratio
        }

cache = CacheManager()
