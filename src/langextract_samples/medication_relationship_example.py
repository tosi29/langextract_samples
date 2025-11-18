"""CLI entry point for the Medication relationship dataset."""

from __future__ import annotations

from . import runner


def main() -> None:
    runner.run_cli(
        allowed_dataset_keys=["medication_relationship"],
        default_dataset_key="medication_relationship",
    )


if __name__ == "__main__":
    main()
