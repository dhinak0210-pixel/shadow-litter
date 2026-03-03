"""
src/agent/database.py
──────────────────────
DumpArchive — SQLite temporal database for persistent dump site tracking.

Schema:
  dumps       — unique dump sites (canonical record)
  detections  — individual detection events (one per scan)
  verifications — crowd-source ground truth votes
"""
from __future__ import annotations
import sqlite3, logging, json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS dumps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    zone        TEXT    NOT NULL,
    lat         REAL    NOT NULL,
    lon         REAL    NOT NULL,
    first_seen  TEXT    NOT NULL,
    last_seen   TEXT    NOT NULL,
    area_sqm    REAL    DEFAULT 0,
    status      TEXT    DEFAULT 'active',   -- active|resolved|false_positive
    dump_type   TEXT    DEFAULT 'unknown',
    ward        TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS detections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dump_id     INTEGER REFERENCES dumps(id),
    detected_at TEXT    NOT NULL,
    confidence  REAL    NOT NULL,
    area_sqm    REAL,
    image_path  TEXT,
    geojson     TEXT
);

CREATE TABLE IF NOT EXISTS verifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dump_id     INTEGER REFERENCES dumps(id),
    user_id     TEXT,
    vote        TEXT    NOT NULL,   -- yes|no|unsure
    timestamp   TEXT    NOT NULL,
    comment     TEXT
);

CREATE INDEX IF NOT EXISTS idx_dumps_zone ON dumps(zone);
CREATE INDEX IF NOT EXISTS idx_detections_dump ON detections(dump_id);
"""


class DumpArchive:
    def __init__(self, db_path: str = "data/shadow_litter.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        logger.info(f"DumpArchive connected → {db_path}")

    # ── Write ─────────────────────────────────────────────────────────────────

    def log_detection(
        self,
        zone: str,
        lat: float,
        lon: float,
        confidence: float,
        area_sqm: float,
        dump_type: str = "unknown",
        image_path: str = "",
        geojson: dict = None,
        ward: str = None,
    ) -> int:
        """
        Record a new detection. Merges with existing nearby dump if within 50m.
        Returns dump_id.
        """
        now = datetime.utcnow().isoformat()
        
        # Check if nearby dump already exists (within ~0.0005° ≈ 50m)
        existing = self.conn.execute(
            """SELECT id FROM dumps
               WHERE zone=? AND abs(lat-?)<0.0005 AND abs(lon-?)<0.0005
               AND status='active' LIMIT 1""",
            (zone, lat, lon),
        ).fetchone()

        if existing:
            dump_id = existing["id"]
            self.conn.execute(
                "UPDATE dumps SET last_seen=?, area_sqm=MAX(area_sqm,?) WHERE id=?",
                (now, area_sqm, dump_id),
            )
        else:
            cur = self.conn.execute(
                """INSERT INTO dumps(zone,lat,lon,first_seen,last_seen,area_sqm,dump_type,ward)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (zone, lat, lon, now, now, area_sqm, dump_type, ward),
            )
            dump_id = cur.lastrowid

        self.conn.execute(
            """INSERT INTO detections(dump_id,detected_at,confidence,area_sqm,image_path,geojson)
               VALUES(?,?,?,?,?,?)""",
            (dump_id, now, confidence, area_sqm, image_path,
             json.dumps(geojson) if geojson else None),
        )
        self.conn.commit()
        return dump_id

    def update_status(self, dump_id: int, status: str, notes: str = "") -> None:
        self.conn.execute(
            "UPDATE dumps SET status=?, notes=? WHERE id=?", (status, notes, dump_id)
        )
        self.conn.commit()

    def add_verification(
        self, dump_id: int, user_id: str, vote: str, comment: str = ""
    ) -> None:
        self.conn.execute(
            "INSERT INTO verifications(dump_id,user_id,vote,timestamp,comment) VALUES(?,?,?,?,?)",
            (dump_id, user_id, vote, datetime.utcnow().isoformat(), comment),
        )
        self.conn.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    def query_history(
        self,
        zone: Optional[str] = None,
        status: str = "active",
        since: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict]:
        query = "SELECT * FROM dumps WHERE status=?"
        params = [status]
        if zone: query += " AND zone=?"; params.append(zone)
        if since: query += " AND first_seen>=?"; params.append(since)
        query += f" ORDER BY first_seen DESC LIMIT {limit}"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_dump_timeline(self, dump_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM detections WHERE dump_id=? ORDER BY detected_at", (dump_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def verification_summary(self, dump_id: int) -> dict:
        rows = self.conn.execute(
            "SELECT vote, COUNT(*) as cnt FROM verifications WHERE dump_id=? GROUP BY vote",
            (dump_id,),
        ).fetchall()
        return {r["vote"]: r["cnt"] for r in rows}

    def stats(self) -> dict:
        return {
            "total_dumps": self.conn.execute("SELECT COUNT(*) FROM dumps").fetchone()[0],
            "active_dumps": self.conn.execute("SELECT COUNT(*) FROM dumps WHERE status='active'").fetchone()[0],
            "total_detections": self.conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0],
            "total_verifications": self.conn.execute("SELECT COUNT(*) FROM verifications").fetchone()[0],
        }

    def close(self) -> None:
        self.conn.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
