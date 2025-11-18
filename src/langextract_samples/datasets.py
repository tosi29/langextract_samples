"""Dataset registry and helper utilities for LangExtract sample scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import langextract as lx


AnnotatedDocument = lx.data.AnnotatedDocument
ExampleBuilder = Callable[[], List[lx.data.ExampleData]]
SummaryFn = Callable[[AnnotatedDocument, str], None]
ExamplesConfig = List[Dict[str, Any]]


@dataclass(frozen=True)
class DatasetConfig:
    """Represents a runnable LangExtract scenario."""

    key: str
    title: str
    description: str
    prompt_description: str
    default_input_text: str
    default_model_id: str
    build_examples: ExampleBuilder
    summary_fn: Optional[SummaryFn] = None


def _format_position(extraction: lx.data.Extraction) -> str:
    """Helper for formatting optional char positions."""
    if not extraction.char_interval:
        return ""
    start = extraction.char_interval.start_pos
    end = extraction.char_interval.end_pos
    return f" (pos: {start}-{end})"


def _basic_summary(result: AnnotatedDocument, input_text: str) -> None:
    """Default console summary showing entities in order."""
    print(f"Input: {input_text.strip()}\n")
    print("Extracted entities:")
    for entity in result.extractions:
        print(
            f"• {entity.extraction_class.capitalize()}: "
            f"{entity.extraction_text}{_format_position(entity)}"
        )


def _relationship_summary(result: AnnotatedDocument, input_text: str) -> None:
    """Specialized summary that groups medication attributes."""
    print(f"Input text: {input_text.strip()}\n")
    print("Extracted medications:")
    medication_groups: Dict[str, List[lx.data.Extraction]] = {}
    for extraction in result.extractions:
        group_name = (extraction.attributes or {}).get("medication_group")
        if not group_name:
            print(f"  ⚠ Missing medication_group for {extraction.extraction_text}")
            continue
        medication_groups.setdefault(group_name, []).append(extraction)

    for med_name, extractions in medication_groups.items():
        print(f"\n* {med_name}")
        for extraction in extractions:
            print(
                f"  • {extraction.extraction_class.capitalize()}: "
                f"{extraction.extraction_text}{_format_position(extraction)}"
            )


SUMMARY_HANDLERS: Dict[str, SummaryFn] = {
    "basic": _basic_summary,
    "relationship": _relationship_summary,
}


def _build_examples_from_config(
    examples_config: ExamplesConfig,
) -> List[lx.data.ExampleData]:
    """Converts raw JSON config into ExampleData objects."""
    examples: List[lx.data.ExampleData] = []
    for example in examples_config:
        extractions = [
            lx.data.Extraction(
                extraction_class=extraction["extraction_class"],
                extraction_text=extraction["extraction_text"],
                attributes=extraction.get("attributes"),
            )
            for extraction in example.get("extractions", [])
        ]
        examples.append(
            lx.data.ExampleData(
                text=example["text"],
                extractions=extractions,
            )
        )
    return examples


def _normalize_entry(
    entry: Dict[str, Any],
    *,
    source_name: str,
    default_key: Optional[str],
) -> Dict[str, Any]:
    """Ensures each entry has a dataset key, preferring filenames."""
    normalized = dict(entry)
    key = normalized.get("key") or default_key
    if not key:
        raise KeyError(
            f"Dataset config '{source_name}' must provide a 'key' field "
            "or rely on its filename to define the key."
        )
    normalized["key"] = key
    return normalized


def _read_config_dir(config_dir) -> Optional[List[Dict[str, Any]]]:
    if not config_dir.is_dir():
        return None
    entries: List[Dict[str, Any]] = []
    for path in sorted(
        (item for item in config_dir.iterdir() if item.name.endswith(".json")),
        key=lambda traversable: traversable.name,
    ):
        with path.open(encoding="utf-8") as f:
            entry = json.load(f)
        if not isinstance(entry, dict):
            raise TypeError(f"Dataset config {path} must contain a JSON object.")
        name = path.name
        default_key = name[: -len(".json")] if name.endswith(".json") else name
        entries.append(
            _normalize_entry(
                entry,
                source_name=str(path),
                default_key=default_key,
            )
        )
    if not entries:
        raise RuntimeError(f"No dataset configs were found inside {config_dir}")
    return entries


def _load_dataset_entries() -> List[Dict[str, Any]]:
    """Loads dataset definitions from JSON files.

    Primary source lives at <repo_root>/dataset/<key>.json (one file per dataset).
    We keep compatibility fallbacks for the previous bundled locations.
    """

    repo_root = Path(__file__).resolve().parents[2]
    new_location = repo_root / "dataset"
    entries = _read_config_dir(new_location)
    if entries:
        return entries

    # Fallback to the prior package-internal layout.
    package_root = resources.files(__package__)
    legacy_dir = package_root / "dataset_configs"
    legacy_entries = _read_config_dir(legacy_dir)
    if legacy_entries:
        return legacy_entries

    # Fallback for environments that still ship the old aggregated file.
    data_path = package_root / "datasets.json"
    with data_path.open(encoding="utf-8") as f:
        raw_entries = json.load(f)
    if not isinstance(raw_entries, list):
        raise TypeError(f"{data_path} must contain a list of dataset definitions.")
    normalized_entries: List[Dict[str, Any]] = []
    for idx, entry in enumerate(raw_entries):
        normalized_entries.append(
            _normalize_entry(entry, source_name=f"{data_path}[{idx}]", default_key=None)
        )
    return normalized_entries


def _make_example_builder(
    examples_config: ExamplesConfig,
) -> ExampleBuilder:
    def builder() -> List[lx.data.ExampleData]:
        return _build_examples_from_config(examples_config)

    return builder


def _create_dataset_config(entry: Dict[str, Any]) -> DatasetConfig:
    """Creates a DatasetConfig from a JSON dictionary."""
    key = entry["key"]
    summary_type = entry.get("summary_type", "basic")
    if summary_type:
        if summary_type not in SUMMARY_HANDLERS:
            raise KeyError(
                f"Unknown summary_type '{summary_type}' for dataset {key}"
            )
        summary_fn = SUMMARY_HANDLERS[summary_type]
    else:
        summary_fn = None
    examples_config = entry.get("examples", [])
    if not isinstance(examples_config, list):
        raise TypeError(f"'examples' for dataset {key} must be a list")
    return DatasetConfig(
        key=key,
        title=entry["title"],
        description=entry["description"],
        prompt_description=entry["prompt_description"],
        default_input_text=entry["default_input_text"],
        default_model_id=entry["default_model_id"],
        build_examples=_make_example_builder(examples_config),
        summary_fn=summary_fn,
    )


def _load_datasets() -> Dict[str, DatasetConfig]:
    entries = _load_dataset_entries()
    datasets_map: Dict[str, DatasetConfig] = {}
    for entry in entries:
        config = _create_dataset_config(entry)
        datasets_map[config.key] = config
    return datasets_map


DATASETS: Dict[str, DatasetConfig] = _load_datasets()


def get_dataset(key: str) -> DatasetConfig:
    """Returns the dataset configuration for a given key."""
    if key not in DATASETS:
        raise KeyError(f"Unknown dataset: {key}")
    return DATASETS[key]


def list_dataset_keys() -> Iterable[str]:
    """Returns the known dataset keys in insertion order."""
    return DATASETS.keys()


__all__ = ["DatasetConfig", "DATASETS", "get_dataset", "list_dataset_keys"]
