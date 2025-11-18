"""CLI entry point for the Medication NER dataset."""

from __future__ import annotations

from . import runner


def main() -> None:
    runner.run_cli(
        allowed_dataset_keys=["medication_ner"],
        default_dataset_key="medication_ner",
    )


if __name__ == "__main__":
    main()
