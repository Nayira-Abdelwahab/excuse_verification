"""Step 5: Detect duplicate files using SHA-256 and perceptual hashing with SQLite."""

import hashlib
import os
import sqlite3
import imagehash

DB_FILE = "seen_files.db"
PHASH_THRESHOLD = 5  # Lower values mean stricter matching


def init_db():
    """إنشاء جدول قاعدة البيانات لضمان الأمان مع الطلبات المتزامنة"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            file_name TEXT,
            sha256 TEXT,
            phash TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def sha256_file(path: str) -> str:
    file_hash = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            file_hash.update(chunk)
    return file_hash.hexdigest()


def check_duplicates(
    path: str,
    img,
    student_id: str,
    register: bool = True
) -> dict:
    init_db()
    sha = sha256_file(path)
    ph = str(imagehash.phash(img)) if img is not None else None

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT student_id, file_name, sha256, phash FROM uploads")
    rows = cursor.fetchall()
    matches = []

    for row in rows:
        db_student_id, db_file, db_sha, db_phash = row

        # فحص ما إذا كان الملف مرفوعاً سابقاً (حتى من نفس الطالب لمادة أخرى أو تعديل بسيط)
        if db_sha == sha:
            reason_text = (
                "Exact file match uploaded previously by the same student"
                if db_student_id == student_id
                else "Exact file match uploaded by another student"
            )
            matches.append({
                "student_id": db_student_id,
                "reason": reason_text
            })
        elif ph and db_phash:
            try:
                distance = (
                    imagehash.hex_to_hash(ph)
                    - imagehash.hex_to_hash(db_phash)
                )
                if distance <= PHASH_THRESHOLD:
                    reason_text = (
                        f"Near-duplicate image by same student (distance: {distance})"
                        if db_student_id == student_id
                        else f"Near-duplicate image by another student (distance: {distance})"
                    )
                    matches.append({
                        "student_id": db_student_id,
                        "reason": reason_text
                    })
            except Exception:
                pass

    if register:
        cursor.execute(
            "INSERT INTO uploads (student_id, file_name, sha256, phash) VALUES (?, ?, ?, ?)",
            (student_id, os.path.basename(path), sha, ph)
        )
        conn.commit()

    conn.close()

    return {
        "sha256": sha,
        "matches": matches
    }