# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Unified Multi-Backend Database Engine (db_engine.py)
============================================================================
Provides a 100% unified, drop-in compatible Database Connection & Cursor API
supporting:
1. PostgreSQL (Neon / Supabase Free Tier) via DATABASE_URL / POSTGRES_URL
2. Serverless SQLite / LibSQL (Turso Free Tier) via TURSO_DATABASE_URL + TURSO_AUTH_TOKEN
3. Local SQLite (vetmind.db) for local Windows/Linux/macOS development
"""

import os
import re
import json
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "vetmind.db")
SCHEMA_SQL_PATH = os.path.join(BASE_DIR, "schema.sql")


def load_dotenv_file(dotenv_path: str = None):
    path = dotenv_path or os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


load_dotenv_file()


class RowProxy:
    __slots__ = ("_cols", "_vals", "_map")

    def __init__(self, columns: list, values: list):
        self._cols = list(columns)
        self._vals = list(values)
        self._map = dict(zip(self._cols, self._vals))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        if isinstance(key, slice):
            return self._vals[key]
        return self._map[key]

    def get(self, key, default=None):
        return self._map.get(key, default)

    def keys(self):
        return self._cols

    def values(self):
        return self._vals

    def items(self):
        return self._map.items()

    def __iter__(self):
        return iter(self._cols)

    def __len__(self):
        return len(self._vals)

    def __contains__(self, item):
        return item in self._map

    def __repr__(self):
        return f"RowProxy({self._map!r})"


PG_CONFLICT_TARGETS = {
    "settings": "(key)",
    "clinic_profiles": "(user_id)",
    "media_files": "(filename)",
}

PG_TABLES_WITHOUT_ID = {"settings", "clinic_profiles"}


def translate_sqlite_to_postgres(sql: str) -> tuple[str, str]:
    clean = sql.strip()

    m_pragma = re.match(r"^PRAGMA\s+table_info\(\s*([a-zA-Z0-9_]+)\s*\)", clean, re.IGNORECASE)
    if m_pragma:
        t_name = m_pragma.group(1).lower()
        pg_sql = (
            "SELECT ordinal_position AS cid, column_name AS name, data_type AS type, "
            "0 AS notnull, column_default AS dflt_value, 0 AS pk "
            "FROM information_schema.columns "
            f"WHERE table_name = '{t_name}' ORDER BY ordinal_position"
        )
        return pg_sql, f"pragma_table_info:{t_name}"

    if clean.upper().startswith("PRAGMA"):
        return "SELECT 1", "noop"

    out = clean

    out = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "SERIAL PRIMARY KEY",
        out,
        flags=re.IGNORECASE
    )

    out = re.sub(
        r"\bMAX\s*\(\s*(\d+)\s*,",
        r"GREATEST(\1,",
        out,
        flags=re.IGNORECASE
    )

    if re.match(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", out, re.IGNORECASE):
        out = re.sub(r"^INSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", out, flags=re.IGNORECASE)
        if "ON CONFLICT" not in out.upper():
            out = out.rstrip(";") + " ON CONFLICT DO NOTHING"

    m_rep = re.match(
        r"^INSERT\s+OR\s+REPLACE\s+INTO\s+([a-zA-Z0-9_]+)\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)\s*;?$",
        out,
        re.IGNORECASE | re.DOTALL
    )
    if m_rep:
        t_name = m_rep.group(1).lower()
        cols_raw = m_rep.group(2)
        vals_raw = m_rep.group(3)
        cols = [c.strip() for c in cols_raw.split(",") if c.strip()]
        conflict_target = PG_CONFLICT_TARGETS.get(t_name, "(id)")
        conflict_cols = {c.strip() for c in conflict_target.strip("()").split(",")}
        update_cols = [c for c in cols if c not in conflict_cols]
        if update_cols:
            set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
            out = f"INSERT INTO {t_name} ({cols_raw}) VALUES ({vals_raw}) ON CONFLICT {conflict_target} DO UPDATE SET {set_clause}"
        else:
            out = f"INSERT INTO {t_name} ({cols_raw}) VALUES ({vals_raw}) ON CONFLICT {conflict_target} DO NOTHING"

    parts = re.split(r"('[^']*')", out)
    new_parts = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            new_parts.append(part.replace("%", "%%"))
        else:
            p_escaped = part.replace("%", "%%").replace("?", "%s")
            new_parts.append(p_escaped)
    out = "".join(new_parts)

    special_mode = ""
    m_ins = re.match(r"^INSERT\s+INTO\s+([a-zA-Z0-9_]+)\b", out, re.IGNORECASE)
    if m_ins:
        t_name = m_ins.group(1).lower()
        if t_name not in PG_TABLES_WITHOUT_ID and "RETURNING " not in out.upper():
            out = out.rstrip(";") + " RETURNING id"
            special_mode = "returning_id"

    return out, special_mode


class UnifiedCursor:
    def __init__(self, connection):
        self._conn = connection
        self.lastrowid = None
        self.rowcount = -1
        self._rows = []
        self._pos = 0

    def execute(self, sql: str, params: tuple | list = ()):
        if params is None:
            params = ()
        elif not isinstance(params, (tuple, list)):
            params = tuple(params)

        backend = self._conn.backend_type

        if backend == "sqlite":
            if os.environ.get("SIMULATE_DB_FAILURE") == "1":
                raise sqlite3.OperationalError("Simulated database connection failure")
            raw_cur = self._conn._raw_conn.cursor()
            raw_cur.execute(sql, params)
            self.lastrowid = raw_cur.lastrowid
            self.rowcount = raw_cur.rowcount
            if raw_cur.description:
                cols = [d[0] for d in raw_cur.description]
                self._rows = [RowProxy(cols, list(r)) for r in raw_cur.fetchall()]
            else:
                self._rows = []
            self._pos = 0
            return self

        elif backend == "postgres":
            if os.environ.get("SIMULATE_DB_FAILURE") == "1":
                raise RuntimeError("Simulated PostgreSQL database connection failure")
            pg_sql, mode = translate_sqlite_to_postgres(sql)
            if mode == "noop":
                self._rows = []
                self._pos = 0
                return self

            raw_cur = self._conn._raw_conn.cursor()
            if params:
                raw_cur.execute(pg_sql, tuple(params))
            else:
                raw_cur.execute(pg_sql)

            self.rowcount = getattr(raw_cur, "rowcount", -1)

            if mode == "returning_id":
                fetched = raw_cur.fetchone()
                self.lastrowid = fetched[0] if fetched else None
                self._rows = []
            elif raw_cur.description:
                cols = [d[0] for d in raw_cur.description]
                self._rows = [RowProxy(cols, list(r)) for r in raw_cur.fetchall()]
            else:
                self._rows = []
            self._pos = 0
            return self

        elif backend == "turso":
            if os.environ.get("SIMULATE_DB_FAILURE") == "1":
                raise RuntimeError("Simulated Turso database connection failure")
            res = self._conn._turso_execute(sql, params)
            self.lastrowid = res.get("last_insert_rowid")
            self.rowcount = res.get("affected_row_count", 0)
            cols = [c["name"] for c in res.get("cols", [])]
            rows_data = res.get("rows", [])
            parsed_rows = []
            for r in rows_data:
                vals = []
                for cell in r:
                    ctype = cell.get("type")
                    cval = cell.get("value")
                    if ctype == "null" or cval is None:
                        vals.append(None)
                    elif ctype == "integer":
                        vals.append(int(cval))
                    elif ctype == "float":
                        vals.append(float(cval))
                    else:
                        vals.append(cval)
                parsed_rows.append(RowProxy(cols, vals))
            self._rows = parsed_rows
            self._pos = 0
            return self

        raise RuntimeError(f"Unsupported database backend: {backend}")

    def executescript(self, sql_script: str):
        if self._conn.backend_type == "sqlite":
            self._conn._raw_conn.executescript(sql_script)
            return self
        statements = [s.strip() for s in sql_script.split(";") if s.strip()]
        for stmt in statements:
            lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
            clean_stmt = "\n".join(lines).strip()
            if clean_stmt:
                self.execute(clean_stmt)
        return self

    def fetchone(self):
        if self._pos < len(self._rows):
            row = self._rows[self._pos]
            self._pos += 1
            return row
        return None

    def fetchall(self):
        if self._pos == 0:
            self._pos = len(self._rows)
            return list(self._rows)
        rem = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rem


class UnifiedConnection:
    def __init__(self, backend_type: str, raw_conn=None, turso_url: str = "", turso_token: str = ""):
        self.backend_type = backend_type
        self._raw_conn = raw_conn
        self._turso_url = turso_url
        self._turso_token = turso_token
        self.row_factory = RowProxy

    def cursor(self) -> UnifiedCursor:
        return UnifiedCursor(self)

    def execute(self, sql: str, params: tuple | list = ()) -> UnifiedCursor:
        cur = self.cursor()
        return cur.execute(sql, params)

    def executescript(self, sql_script: str) -> UnifiedCursor:
        cur = self.cursor()
        return cur.executescript(sql_script)

    def commit(self):
        if self.backend_type in ("sqlite", "postgres") and self._raw_conn:
            self._raw_conn.commit()

    def rollback(self):
        if self.backend_type in ("sqlite", "postgres") and self._raw_conn:
            try:
                self._raw_conn.rollback()
            except Exception:
                pass

    def close(self):
        if self.backend_type in ("sqlite", "postgres") and self._raw_conn:
            try:
                self._raw_conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def _turso_execute(self, sql: str, params: tuple | list = ()) -> dict:
        http_url = self._turso_url
        if http_url.startswith("libsql://"):
            http_url = "https://" + http_url[len("libsql://"):]
        http_url = http_url.rstrip("/")
        if not http_url.endswith("/v2/pipeline"):
            http_url += "/v2/pipeline"

        args = []
        for p in (params or ()):
            if p is None:
                args.append({"type": "null"})
            elif isinstance(p, bool):
                args.append({"type": "integer", "value": "1" if p else "0"})
            elif isinstance(p, int):
                args.append({"type": "integer", "value": str(p)})
            elif isinstance(p, float):
                args.append({"type": "float", "value": float(p)})
            else:
                args.append({"type": "text", "value": str(p)})

        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": args}},
                {"type": "close"}
            ]
        }
        req = urllib.request.Request(
            http_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._turso_token}",
                "Content-Type": "application/json",
                "User-Agent": "VetMindAI-DBEngine/4.4"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("results", [])
        if not results:
            return {}
        first = results[0]
        if first.get("type") == "error":
            err_msg = first.get("error", {}).get("message", "Unknown Turso SQL error")
            raise RuntimeError(f"Turso SQL Error: {err_msg}")
        return first.get("response", {}).get("result", {})


def get_storage_status() -> dict:
    db_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("NEON_DATABASE_URL")
        or ""
    ).strip()
    turso_url = (os.environ.get("TURSO_DATABASE_URL") or "").strip()
    turso_token = (os.environ.get("TURSO_AUTH_TOKEN") or "").strip()
    is_vercel = bool(os.environ.get("VERCEL"))

    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        return {
            "backend": "postgres",
            "label": "PostgreSQL Cloud (Neon / Supabase)",
            "is_permanent": True,
            "is_shared": True,
            "is_vercel": is_vercel,
            "warning": ""
        }
    if turso_url and turso_token:
        return {
            "backend": "turso",
            "label": "Turso Serverless SQLite Cloud (LibSQL)",
            "is_permanent": True,
            "is_shared": True,
            "is_vercel": is_vercel,
            "warning": ""
        }
    if is_vercel or not os.access(BASE_DIR, os.W_OK):
        return {
            "backend": "sqlite_ephemeral",
            "label": "SQLite مؤقت في بيئة سحابية (/tmp)",
            "is_permanent": False,
            "is_shared": False,
            "is_vercel": True,
            "warning": (
                "تنبيه هام: التطبيق يعمل حالياً على Vercel بدون ربط متغير DATABASE_URL أو TURSO_DATABASE_URL. "
                "التخزين في /tmp مؤقت ويُمسح عند إعادة تشغيل الخادم. يرجى إضافة رابط قاعدة البيانات السحابية المجانية في إعدادات Vercel."
            )
        }
    return {
        "backend": "sqlite_local",
        "label": "SQLite محلي دائم (vetmind.db)",
        "is_permanent": True,
        "is_shared": True,
        "is_vercel": False,
        "warning": ""
    }


def _connect_postgres(db_url: str) -> UnifiedConnection:
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]

    try:
        import psycopg2
        raw_conn = psycopg2.connect(db_url, connect_timeout=15)
        return UnifiedConnection("postgres", raw_conn=raw_conn)
    except ImportError:
        pass

    try:
        import psycopg
        raw_conn = psycopg.connect(db_url, connect_timeout=15)
        return UnifiedConnection("postgres", raw_conn=raw_conn)
    except ImportError:
        pass

    try:
        import pg8000.dbapi
        import urllib.parse
        import ssl
        parsed = urllib.parse.urlparse(db_url)
        q = urllib.parse.parse_qs(parsed.query)
        ssl_ctx = None
        if q.get("sslmode", ["require"])[0] in ("require", "verify-ca", "verify-full"):
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        raw_conn = pg8000.dbapi.connect(
            user=urllib.parse.unquote(parsed.username or ""),
            password=urllib.parse.unquote(parsed.password or ""),
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=(parsed.path or "/postgres").lstrip("/"),
            ssl_context=ssl_ctx,
            timeout=15
        )
        return UnifiedConnection("postgres", raw_conn=raw_conn)
    except ImportError:
        pass

    raise RuntimeError(
        "PostgreSQL DATABASE_URL is configured, but no PostgreSQL driver (psycopg2-binary or pg8000) is installed. "
        "Run: pip install psycopg2-binary"
    )


def get_active_sqlite_path() -> str:
    custom_path = os.environ.get("SQLITE_DB_PATH", "").strip()
    if custom_path:
        return custom_path

    if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
        tmp_db = "/tmp/vetmind.db"
        if not os.path.exists(tmp_db) and os.path.exists(DEFAULT_SQLITE_PATH):
            try:
                import shutil
                shutil.copy2(DEFAULT_SQLITE_PATH, tmp_db)
            except Exception:
                pass
        return tmp_db
    return DEFAULT_SQLITE_PATH


_SCHEMA_INITIALIZED = False


def get_db() -> UnifiedConnection:
    global _SCHEMA_INITIALIZED

    if os.environ.get("SIMULATE_DB_FAILURE") == "1":
        raise sqlite3.OperationalError("Simulated database connection failure")

    db_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("NEON_DATABASE_URL")
        or ""
    ).strip()

    turso_url = (os.environ.get("TURSO_DATABASE_URL") or "").strip()
    turso_token = (os.environ.get("TURSO_AUTH_TOKEN") or "").strip()

    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        conn = _connect_postgres(db_url)
    elif turso_url and turso_token:
        conn = UnifiedConnection("turso", turso_url=turso_url, turso_token=turso_token)
    else:
        sqlite_path = get_active_sqlite_path()
        raw_conn = sqlite3.connect(sqlite_path, timeout=25.0)
        raw_conn.execute("PRAGMA foreign_keys = ON")
        try:
            raw_conn.execute("PRAGMA journal_mode = WAL")
        except Exception:
            pass
        conn = UnifiedConnection("sqlite", raw_conn=raw_conn)

    if not _SCHEMA_INITIALIZED:
        _SCHEMA_INITIALIZED = True
        try:
            ensure_schema_and_seed(conn)
        except Exception as e:
            print("Schema initialization warning:", e)

    return conn


def ensure_schema_and_seed(conn: UnifiedConnection = None):
    close_after = False
    if conn is None:
        conn = get_db()
        close_after = True

    try:
        c = conn.cursor()
        has_users = False
        has_cases = False
        has_media = False
        try:
            c.execute("SELECT COUNT(*) FROM users")
            has_users = True
            c.execute("SELECT COUNT(*) FROM cases")
            has_cases = True
            c.execute("SELECT COUNT(*) FROM media_files")
            has_media = True
        except Exception:
            if conn.backend_type == "postgres":
                conn.rollback()

        if not (has_users and has_cases and has_media):
            if os.path.exists(SCHEMA_SQL_PATH):
                with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                c.executescript(schema_sql)
                conn.commit()

        _ensure_column(conn, "cases", "diagnosis", "TEXT DEFAULT ''")
        _ensure_column(conn, "cases", "client_name", "TEXT DEFAULT ''")

        try:
            import seed_data
            seed_data.seed_if_empty(conn)
        except Exception as se:
            print("Seed check notice:", se)

    finally:
        if close_after:
            conn.close()


def _ensure_column(conn: UnifiedConnection, table: str, column: str, col_def: str):
    try:
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        existing = {r["name"].lower() for r in c.fetchall()}
        if column.lower() not in existing:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            conn.commit()
    except Exception:
        if conn.backend_type == "postgres":
            conn.rollback()
