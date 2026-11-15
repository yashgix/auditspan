"""Evidence-linked extraction of facts from Single Audit findings."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

__all__ = ["DATA_DIR"]
