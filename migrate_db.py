# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Safe Backup, Migration & Restoration Tool (migrate_db.py)
"""

import os
import sys
import json
import shutil
import sqlite3
import base64
import argparse
from datetime import datetime

import db_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

ORDERED_TABLES = [
    "users",
    "settings",
    "local_products",
    "clinic_profiles",
    "cases",
    "chat_messages",
    "appointments",
    "vaccinations",
    "drug_inventory",
    "invoices",
    "lab_tests",
    "clinic_prescriptions",
    "client_operations",
    "broadcast_notifications",
    "support_tickets",
    "verification_logs",
    "media_files",
]


def get_table_counts(conn) -> dict:
    counts = {}
    c = conn.cursor()
    for t in ORDERED_TABLES:
        try:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            row = c.fetchone()
            counts[t] = row[0] if row else 0
        except Exception:
            if getattr(conn, "backend_type", "") == "postgres":
                conn.rollback()
            counts[t] = 0
    return counts


def create_full_backup(source_sqlite_path: str = None) -> dict:
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    src_db = source_sqlite_path or os.path.join(BASE_DIR, "vetmind.db")
    binary_backup_path = None
    if os.path.exists(src_db):
        binary_backup_path = os.path.join(BACKUPS_DIR, f"vetmind_backup_{ts}.db")
        shutil.copy2(src_db, binary_backup_path)

    if os.path.exists(src_db) and source_sqlite_path:
        raw_conn = sqlite3.connect(src_db)
        conn = db_engine.UnifiedConnection("sqlite", raw_conn=raw_conn)
    else:
        conn = db_engine.get_db()

    snapshot = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "backend_type": conn.backend_type,
        "table_counts": {},
        "tables": {},
        "uploads_files": {}
    }

    c = conn.cursor()
    for t in ORDERED_TABLES:
        try:
            c.execute(f"SELECT * FROM {t}")
            rows = [dict(r) for r in c.fetchall()]
            snapshot["tables"][t] = rows
            snapshot["table_counts"][t] = len(rows)
        except Exception:
            if conn.backend_type == "postgres":
                conn.rollback()
            snapshot["tables"][t] = []
            snapshot["table_counts"][t] = 0

    conn.close()

    uploads_dir = os.path.join(BASE_DIR, "uploads")
    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if fname.startswith(".") or fname.endswith(".json"):
                continue
            fpath = os.path.join(uploads_dir, fname)
            if os.path.isfile(fpath) and os.path.getsize(fpath) <= 15 * 1024 * 1024:
                try:
                    with open(fpath, "rb") as f:
                        snapshot["uploads_files"][fname] = base64.b64encode(f.read()).decode("ascii")
                except Exception:
                    pass

    json_backup_path = os.path.join(BACKUPS_DIR, f"vetmind_snapshot_{ts}.json")
    with open(json_backup_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    return {
        "timestamp": ts,
        "binary_backup_path": binary_backup_path,
        "json_backup_path": json_backup_path,
        "table_counts": snapshot["table_counts"],
        "uploads_count": len(snapshot["uploads_files"])
    }


def migrate_sqlite_to_target(source_sqlite_path: str, target_conn=None) -> dict:
    if not os.path.exists(source_sqlite_path):
        raise FileNotFoundError(f"ملف قاعدة البيانات المصدر غير موجود: {source_sqlite_path}")

    backup_info = create_full_backup(source_sqlite_path)

    raw_src = sqlite3.connect(source_sqlite_path)
    src_conn = db_engine.UnifiedConnection("sqlite", raw_conn=raw_src)
    before_counts = get_table_counts(src_conn)

    close_target = False
    if target_conn is None:
        target_conn = db_engine.get_db()
        close_target = True

    db_engine.ensure_schema_and_seed(target_conn)

    src_cur = src_conn.cursor()
    tgt_cur = target_conn.cursor()

    migrated_counts = {}

    for t in ORDERED_TABLES:
        try:
            src_cur.execute(f"SELECT * FROM {t}")
            rows = [dict(r) for r in src_cur.fetchall()]
        except Exception:
            rows = []

        if not rows:
            migrated_counts[t] = 0
            continue

        try:
            tgt_cur.execute(f"PRAGMA table_info({t})")
            tgt_cols = {r["name"] for r in tgt_cur.fetchall()}
        except Exception:
            tgt_cols = set(rows[0].keys())

        inserted = 0
        for row in rows:
            valid_cols = [col for col in row.keys() if col in tgt_cols]
            if not valid_cols:
                continue
            cols_str = ", ".join(valid_cols)
            placeholders = ", ".join(["?"] * len(valid_cols))
            vals = [row[col] for col in valid_cols]
            try:
                tgt_cur.execute(
                    f"INSERT OR REPLACE INTO {t} ({cols_str}) VALUES ({placeholders})",
                    vals
                )
                inserted += 1
            except Exception as e_row:
                if target_conn.backend_type == "postgres":
                    target_conn.rollback()
                print(f"Notice migrating row in {t}: {e_row}")

        target_conn.commit()
        migrated_counts[t] = inserted

        if target_conn.backend_type == "postgres" and "id" in tgt_cols:
            try:
                tgt_cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT MAX(id) FROM {t}), 1), true)"
                )
                target_conn.commit()
            except Exception:
                target_conn.rollback()

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(source_sqlite_path)), "uploads")
    media_migrated = 0
    if os.path.exists(uploads_dir):
        for fname in os.listdir(uploads_dir):
            if fname.startswith(".") or fname.endswith(".json"):
                continue
            fpath = os.path.join(uploads_dir, fname)
            if os.path.isfile(fpath) and os.path.getsize(fpath) <= 10 * 1024 * 1024:
                ext = os.path.splitext(fname)[1].lower()
                mime = "video/mp4" if ext in (".mp4", ".webm", ".mov") else "image/jpeg"
                try:
                    with open(fpath, "rb") as f:
                        raw_b = f.read()
                    b64_s = base64.b64encode(raw_b).decode("ascii")
                    tgt_cur.execute(
                        """
                        INSERT OR REPLACE INTO media_files (filename, mime_type, data_b64, size_bytes, owner_id, is_private, created_at)
                        VALUES (?, ?, ?, ?, 0, 0, ?)
                        """,
                        (fname, mime, b64_s, len(raw_b), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    media_migrated += 1
                except Exception:
                    if target_conn.backend_type == "postgres":
                        target_conn.rollback()
        target_conn.commit()

    after_counts = get_table_counts(target_conn)

    src_conn.close()
    if close_target:
        target_conn.close()

    return {
        "backup": backup_info,
        "before_counts": before_counts,
        "migrated_counts": migrated_counts,
        "after_counts": after_counts,
        "media_files_migrated": media_migrated
    }


def restore_from_snapshot(snapshot_json_path: str, target_conn=None) -> dict:
    if not os.path.exists(snapshot_json_path):
        raise FileNotFoundError(f"ملف النسخة الاحتياطية غير موجود: {snapshot_json_path}")

    with open(snapshot_json_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    close_target = False
    if target_conn is None:
        target_conn = db_engine.get_db()
        close_target = True

    db_engine.ensure_schema_and_seed(target_conn)
    c = target_conn.cursor()

    restored_counts = {}
    tables_data = snapshot.get("tables", {})
    for t in ORDERED_TABLES:
        rows = tables_data.get(t, [])
        if not rows:
            restored_counts[t] = 0
            continue
        cnt = 0
        for row in rows:
            cols = list(row.keys())
            cols_str = ", ".join(cols)
            placeholders = ", ".join(["?"] * len(cols))
            vals = [row[k] for k in cols]
            try:
                c.execute(f"INSERT OR REPLACE INTO {t} ({cols_str}) VALUES ({placeholders})", vals)
                cnt += 1
            except Exception:
                if target_conn.backend_type == "postgres":
                    target_conn.rollback()
        target_conn.commit()
        restored_counts[t] = cnt

    uploads_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    for fname, b64_data in snapshot.get("uploads_files", {}).items():
        try:
            clean_name = os.path.basename(fname)
            with open(os.path.join(uploads_dir, clean_name), "wb") as f_out:
                f_out.write(base64.b64decode(b64_data))
        except Exception:
            pass

    if close_target:
        target_conn.close()

    return {"restored_counts": restored_counts}


def main():
    parser = argparse.ArgumentParser(description="VetMind AI Safe Database Backup & Cloud Migration Tool")
    parser.add_argument("--backup", action="store_true", help="Create a full binary + JSON backup of the database")
    parser.add_argument("--migrate-to-cloud", action="store_true", help="Migrate local SQLite database to configured Cloud DB (PostgreSQL / Turso)")
    parser.add_argument("--source", type=str, default=os.path.join(BASE_DIR, "vetmind.db"), help="Path to source SQLite database file")
    parser.add_argument("--restore", type=str, default="", help="Restore database from a JSON snapshot file")
    parser.add_argument("--verify", action="store_true", help="Print record counts across all tables in the active database")

    args = parser.parse_args()

    if args.backup:
        info = create_full_backup(args.source if os.path.exists(args.source) else None)
        print("✅ تم إنشاء النسخة الاحتياطية بنجاح!")
        print(f"📁 ملف JSON الشامل: {info['json_backup_path']}")
        if info["binary_backup_path"]:
            print(f"💾 نسخة SQLite الثنائية: {info['binary_backup_path']}")
        non_empty = {k: v for k, v in info["table_counts"].items() if v > 0}
        print(f"📊 أعداد السجلات في الجداول النشطة: {json.dumps(non_empty, ensure_ascii=False)}")
        return

    if args.restore:
        res = restore_from_snapshot(args.restore)
        print("✅ تمت استعادة البيانات من النسخة الاحتياطية بنجاح!")
        non_empty = {k: v for k, v in res["restored_counts"].items() if v > 0}
        print(f"📊 السجلات المستعادة: {json.dumps(non_empty, ensure_ascii=False)}")
        return

    if args.migrate_to_cloud:
        status = db_engine.get_storage_status()
        print(f"🔄 الوجهة النشطة: {status['label']} ({status['backend']})")
        res = migrate_sqlite_to_target(args.source)
        print("✅ اكتمل الترحيل الآمن بنجاح مع الحفاظ على النسخة الاحتياطية!")
        non_empty = {k: v for k, v in res["after_counts"].items() if v > 0}
        print(f"📊 أعداد السجلات بعد الترحيل: {json.dumps(non_empty, ensure_ascii=False)}")
        return

    status = db_engine.get_storage_status()
    conn = db_engine.get_db()
    counts = get_table_counts(conn)
    conn.close()
    print(f"🩺 حالة قاعدة البيانات النشطة: {status['label']}")
    print(f"🔒 تخزين دائم ومشترك: {'نعم ✅' if status['is_permanent'] else 'لا ⚠️'}")
    if status["warning"]:
        print(f"⚠️ {status['warning']}")
    non_empty = {k: v for k, v in counts.items() if v > 0}
    print(f"📊 إجمالي الجداول: {len(counts)} | الجداول التي تحتوي على بيانات ({len(non_empty)}):")
    for k, v in non_empty.items():
        print(f"   - {k}: {v} سجل")


if __name__ == "__main__":
    main()
