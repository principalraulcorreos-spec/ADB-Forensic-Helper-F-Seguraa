"""
Historial de dispositivos conectados.
Guarda en history.json el registro de todos los celulares procesados.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self, base_dir: str):
        self.history_file = Path(base_dir) / "history.json"
        self._history: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Error cargando historial: {e}")
        return []

    def _save(self) -> None:
        try:
            self.history_file.write_text(
                json.dumps(self._history, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Error guardando historial: {e}")

    def add_device(self, manufacturer: str, model: str, serial: str,
                   android_version: str) -> None:
        # No duplicar el mismo serial seguido
        if self._history and self._history[0].get("serial") == serial:
            return
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "manufacturer": manufacturer,
            "model": model,
            "serial": serial,
            "android_version": android_version,
        }
        self._history.insert(0, entry)
        if len(self._history) > 200:
            self._history = self._history[:200]
        self._save()

    def get_all(self) -> list[dict]:
        return list(self._history)

    def clear(self) -> None:
        self._history = []
        self._save()
