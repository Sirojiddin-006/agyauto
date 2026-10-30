"""SQLite event history shared by every running session and the dashboard."""
import os
import sqlite3
import time

from . import paths
from .redact import redact

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  session_id INTEGER,
  session TEXT,
  kind TEXT NOT NULL,          -- APPROVED | BLOCKED | STALLED
  ptype TEXT,                  -- command | edit | create | tool | other | generic
  command TEXT,
  key TEXT,
  screen TEXT
);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);
"""


def connect():
    paths.ensure_private(paths.state_dir())
    new = not os.path.exists(paths.history_db())
    db = sqlite3.connect(paths.history_db(), timeout=5.0)
    if new:
        try:
            os.chmod(paths.history_db(), 0o600)
        except OSError:
            pass
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    return db


def add(db, session_id, session, kind, ptype="", command="", key="", screen=""):
    try:
        db.execute(
            "INSERT INTO events(ts,session_id,session,kind,ptype,command,key,screen) VALUES(?,?,?,?,?,?,?,?)",
            (time.time(), session_id, redact(session), kind, ptype, redact(command)[:2000], key,
             redact(screen)[-1500:] if screen else ""))
        db.commit()
    except sqlite3.Error:
        pass  # history must never break the wrapped session


def prune(db, days):
    try:
        db.execute("DELETE FROM events WHERE ts < ?", (time.time() - days * 86400,))
        db.commit()
    except sqlite3.Error:
        pass


def query(db, kind=None, text=None, limit=200, offset=0, session_id=None):
    sql, args = "SELECT id,ts,session_id,session,kind,ptype,command,key,screen FROM events WHERE 1=1", []
    if kind and kind != "ALL":
        sql += " AND kind=?"
        args.append(kind)
    if session_id:
        sql += " AND session_id=?"
        args.append(session_id)
    if text:
        sql += " AND (command LIKE ? OR session LIKE ?)"
        args += ["%" + text + "%"] * 2
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    args += [limit, offset]
    try:
        return db.execute(sql, args).fetchall()
    except sqlite3.Error:
        return []


def hourly(db, hours=24):
    """Approved counts per hour for the last `hours` hours, oldest first."""
    now = time.time()
    start = now - hours * 3600
    buckets = [0] * hours
    try:
        for (ts,) in db.execute("SELECT ts FROM events WHERE kind='APPROVED' AND ts>=?", (start,)):
            i = min(hours - 1, int((ts - start) // 3600))
            buckets[i] += 1
    except sqlite3.Error:
        pass
    return buckets


def totals(db):
    out = {}
    try:
        day = time.time() - 86400
        for kind, n in db.execute("SELECT kind,COUNT(*) FROM events GROUP BY kind"):
            out[kind] = n
        out["today"] = db.execute("SELECT COUNT(*) FROM events WHERE kind='APPROVED' AND ts>=?", (day,)).fetchone()[0]
    except sqlite3.Error:
        pass
    return out


def per_session(db, limit=8):
    try:
        return db.execute(
            "SELECT session,COUNT(*) c FROM events WHERE kind='APPROVED' GROUP BY session ORDER BY c DESC LIMIT ?",
            (limit,)).fetchall()
    except sqlite3.Error:
        return []


def top_commands(db, limit=8):
    counts = {}
    try:
        for (cmd,) in db.execute("SELECT command FROM events WHERE kind='APPROVED' AND ptype='command' AND command!=''"):
            parts = cmd.split()
            w = " ".join(parts[:2]) if parts and parts[0] in ("git", "npm", "pnpm", "npx", "docker", "sudo") and len(parts) > 1 \
                else (parts[0] if parts else "")
            counts[w] = counts.get(w, 0) + 1
    except sqlite3.Error:
        pass
    return sorted(counts.items(), key=lambda kv: -kv[1])[:limit]
