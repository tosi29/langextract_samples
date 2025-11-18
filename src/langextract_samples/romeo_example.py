"""CLI entry point for the Romeo & Juliet quick-start dataset."""

from __future__ import annotations

from . import runner


def main() -> None:
    runner.run_cli(
        allowed_dataset_keys=["romeo_quickstart"],
        default_dataset_key="romeo_quickstart",
    )


if __name__ == "__main__":
    main()
