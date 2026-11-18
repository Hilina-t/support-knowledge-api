import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb

from app.embed import HashingEmbedder


class KnowledgeStore:
    def __init__(self, data_dir: Path, embedder: HashingEmbedder | None = None) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or HashingEmbedder()
        self.db = sqlite3.connect(data_dir / "knowledge.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.db.commit()
        client = chromadb.PersistentClient(path=str(data_dir / "chroma"))
        self.collection = client.get_or_create_collection(name="articles")

    def add(self, title: str, body: str) -> dict:
        document_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO documents (id, title, body, created_at) VALUES (?, ?, ?, ?)",
            (document_id, title, body, created_at),
        )
        self.db.commit()
        self.collection.add(
            ids=[document_id],
            documents=[f"{title}\n{body}"],
            embeddings=self.embedder.embed([f"{title}\n{body}"]),
            metadatas=[{"title": title}],
        )
        return {"id": document_id, "title": title, "body": body, "created_at": created_at}

    def list_documents(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, title, body, created_at FROM documents ORDER BY created_at"
        ).fetchall()
        return [dict(row) for row in rows]

    def search(self, question: str, limit: int = 3) -> list[dict]:
        count = self.collection.count()
        if count == 0:
            return []
        result = self.collection.query(
            query_embeddings=self.embedder.embed([question]),
            n_results=min(limit, count),
        )
        sources = []
        for document_id, document, metadata in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0]
        ):
            sources.append(
                {
                    "id": document_id,
                    "title": metadata["title"],
                    "excerpt": document[:400],
                }
            )
        return sources

    def close(self) -> None:
        self.db.close()
