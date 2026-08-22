from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional


@dataclass(frozen=True)
class StoredObject:
    sha256: str
    byte_count: int
    object_path: str


class RawManifest:
    """Immutable, content-addressed API archive with request provenance.

    This intentionally mirrors the GTFS collector pattern: raw bytes are written once
    under a SHA-256 path and each observation/request is recorded separately in SQLite.
    """

    def __init__(self, root: str | Path = "data/raw") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "manifest.sqlite"
        self.db = sqlite3.connect(self.db_path)
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                season INTEGER,
                params_json TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                byte_count INTEGER NOT NULL,
                object_path TEXT NOT NULL,
                http_status INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT,
                request_id TEXT,
                schema_version TEXT NOT NULL DEFAULT 'v1'
            )
            """
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_downloads_endpoint_season ON downloads(endpoint, season)")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_downloads_sha256 ON downloads(sha256)")
        self.db.commit()

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def store_bytes(self, payload: bytes, suffix: str = ".json") -> StoredObject:
        digest = hashlib.sha256(payload).hexdigest()
        relative = Path("objects") / digest[:2] / f"{digest}{suffix}"
        target = self.root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".part")
            with tmp.open("wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(target)
        return StoredObject(digest, len(payload), str(relative))

    def record_download(
        self,
        *,
        endpoint: str,
        season: Optional[int],
        params: Mapping[str, object],
        requested_at: str,
        received_at: str,
        stored: StoredObject,
        http_status: int,
        source_url: str,
        headers: Mapping[str, str] | None = None,
        schema_version: str = "v1",
    ) -> int:
        headers = headers or {}
        cur = self.db.execute(
            """
            INSERT INTO downloads (
                endpoint, season, params_json, requested_at, received_at,
                sha256, byte_count, object_path, http_status, source_url,
                etag, last_modified, request_id, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint,
                season,
                json.dumps(dict(params), sort_keys=True, separators=(",", ":")),
                requested_at,
                received_at,
                stored.sha256,
                stored.byte_count,
                stored.object_path,
                http_status,
                source_url,
                headers.get("ETag") or headers.get("etag"),
                headers.get("Last-Modified") or headers.get("last-modified"),
                headers.get("X-Request-Id") or headers.get("x-request-id"),
                schema_version,
            ),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def latest_object(
        self,
        endpoint: str,
        season: int | None = None,
        *,
        params: Mapping[str, object] | None = None,
    ) -> Path | None:
        sql = "SELECT object_path FROM downloads WHERE endpoint = ?"
        args: list[object] = [endpoint]
        if season is not None:
            sql += " AND season = ?"
            args.append(season)
        if params is not None:
            sql += " AND params_json = ?"
            args.append(json.dumps(dict(params), sort_keys=True, separators=(",", ":")))
        sql += " ORDER BY id DESC LIMIT 1"
        row = self.db.execute(sql, args).fetchone()
        return (self.root / row[0]) if row else None


    def iter_downloads(self) -> list[dict[str, object]]:
        columns = [
            "id", "endpoint", "season", "params_json", "requested_at", "received_at",
            "sha256", "byte_count", "object_path", "http_status", "source_url",
            "etag", "last_modified", "request_id", "schema_version",
        ]
        rows = self.db.execute(
            "SELECT id, endpoint, season, params_json, requested_at, received_at, sha256, byte_count, "
            "object_path, http_status, source_url, etag, last_modified, request_id, schema_version "
            "FROM downloads ORDER BY id"
        ).fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def export_jsonl(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in self.iter_downloads():
                item = dict(row)
                item["params"] = json.loads(str(item.pop("params_json")))
                handle.write(json.dumps(item, sort_keys=True) + "\n")
        return path

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "RawManifest":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
