"""Packaged trading knowledge access.

The JSON files in :mod:`eazzu.trading.knowledge` are treated as reference data.
They are never executed and their narrative guidance does not alter program flow.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeBase:
    """Read-only index over EAZZU's packaged trading-reference documents."""

    _EXCLUDED_FROM_INSTRUMENTS = {
        "_MASTER_GUIDE.json",
        "sessions_sast.json",
        "scalping_daytrading_playbook.json",
        "deriv_api_reference.json",
    }

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path(__file__).resolve().parent.parent / "knowledge"
        self._cache: Dict[str, Dict[str, Any]] = {}

    def document_names(self) -> List[str]:
        """Return all packaged JSON document names in deterministic order."""
        if not self.root.exists():
            return []
        return sorted(path.name for path in self.root.glob("*.json") if path.is_file())

    def load_document(self, name: str) -> Dict[str, Any]:
        """Load a single JSON document while preventing path traversal."""
        if not name or Path(name).name != name or not name.endswith(".json"):
            raise ValueError("knowledge document name must be a simple .json filename")
        if name in self._cache:
            return self._cache[name]

        path = self.root / name
        if not path.exists():
            raise KeyError(f"unknown knowledge document: {name}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in packaged knowledge document {name}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"knowledge document {name} must contain a JSON object")
        self._cache[name] = payload
        return payload

    def master_guide(self) -> Dict[str, Any]:
        """Return the uploaded master guide, or an empty object if unavailable."""
        try:
            return self.load_document("_MASTER_GUIDE.json")
        except KeyError:
            return {}

    def documents(self) -> List[Dict[str, Any]]:
        """Return concise metadata for every packaged knowledge document."""
        rows: List[Dict[str, Any]] = []
        for name in self.document_names():
            try:
                document = self.load_document(name)
                rows.append(
                    {
                        "name": name,
                        "title": document.get("title") or document.get("name") or document.get("instrument"),
                        "instrument": document.get("instrument"),
                        "deriv_symbol": document.get("deriv_symbol"),
                        "market_type": document.get("market_type"),
                    }
                )
            except ValueError as exc:
                rows.append({"name": name, "error": str(exc)})
        return rows

    @staticmethod
    def _normalise(value: Any) -> str:
        return "".join(character for character in str(value or "").upper() if character.isalnum())

    def instrument_profile(self, symbol_or_name: str) -> Optional[Dict[str, Any]]:
        """Find a profile by broker symbol, instrument name, or filename stem."""
        sought = self._normalise(symbol_or_name)
        if not sought:
            return None

        for name in self.document_names():
            if name in self._EXCLUDED_FROM_INSTRUMENTS:
                continue
            try:
                document = self.load_document(name)
            except ValueError:
                continue
            candidates = [
                document.get("deriv_symbol"),
                document.get("instrument"),
                document.get("name"),
                Path(name).stem,
            ]
            if any(self._normalise(candidate) == sought for candidate in candidates):
                return {"document": name, **document}
        return None

    def context_for(self, symbol_or_name: Optional[str]) -> Dict[str, Any]:
        """Return non-executable, compact reference context for an analysis run."""
        profile = self.instrument_profile(symbol_or_name or "") if symbol_or_name else None
        master = self.master_guide()
        context: Dict[str, Any] = {
            "knowledge_version": master.get("version"),
            "timezone": master.get("timezone"),
            "document_count": len(self.document_names()),
            "profile_found": profile is not None,
        }
        if profile:
            context["instrument"] = {
                "document": profile.get("document"),
                "instrument": profile.get("instrument"),
                "deriv_symbol": profile.get("deriv_symbol"),
                "market_type": profile.get("market_type"),
                "trading_hours": profile.get("trading_hours"),
                "best_timeframes": profile.get("best_timeframes"),
                "key_technicals": profile.get("key_technicals"),
            }
        return context

    def session_playbook(self) -> Dict[str, Any]:
        """Return the uploaded session reference data when present."""
        try:
            return self.load_document("sessions_sast.json")
        except KeyError:
            return {}

    def validate(self) -> Dict[str, Any]:
        """Validate package readability and report invalid document names."""
        valid: List[str] = []
        invalid: List[Dict[str, str]] = []
        for name in self.document_names():
            try:
                self.load_document(name)
                valid.append(name)
            except ValueError as exc:
                invalid.append({"name": name, "error": str(exc)})
        return {
            "root": str(self.root),
            "total": len(valid) + len(invalid),
            "valid": valid,
            "invalid": invalid,
            "is_valid": not invalid and bool(valid),
        }
