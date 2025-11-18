"""Single CLI module that exposes dataset-specific entry points."""

from __future__ import annotations

from typing import Iterable, Optional

from . import runner


def _run_for_dataset(dataset_key: Optional[str] = None) -> None:
    allowed: Optional[Iterable[str]] = None
    if dataset_key:
        allowed = [dataset_key]
    runner.run_cli(
        allowed_dataset_keys=allowed,
        default_dataset_key=dataset_key,
    )


def main() -> None:
    """Single entry point that allows choosing any dataset."""
    _run_for_dataset(None)


__all__ = ["main"]
