import json
import sqlite3
from pathlib import Path

from .constants import DATA_FILE


class StorageService:
    def __init__(self):
        self.database_path = Path(DATA_FILE).with_suffix(".db")
        self._initialize_database()

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _initialize_database(self):
        with self._connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            connection.commit()

    def get_json(self, key: str, default_value):
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT value FROM app_kv WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()

        if row is None:
            return default_value

        try:
            return json.loads(row[0])
        except Exception:
            return default_value

    def set_json(self, key: str, value):
        serialized_value = json.dumps(value)

        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app_kv (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, serialized_value),
            )
            connection.commit()

    def load_data(self):
        return {
            "assignments": self.get_json("assignments", {}),
            "ranks": self.get_json("ranks", {}),
            "ui_state": self.get_json("ui_state", {}),
        }

    def save_data(self, data: dict):
        self.set_json("assignments", data.get("assignments", {}))
        self.set_json("ranks", data.get("ranks", {}))
        self.set_json("ui_state", data.get("ui_state", {}))


def load_data():
    storage_service = StorageService()
    return storage_service.load_data()


def save_data(data):
    storage_service = StorageService()
    storage_service.save_data(data)
