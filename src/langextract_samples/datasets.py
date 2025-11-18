"""Dataset registry and helper utilities for LangExtract sample scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
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
    artifact_prefix: str
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


def _load_dataset_entries() -> List[Dict[str, Any]]:
    """Loads dataset definitions from the bundled JSON file."""
    data_path = resources.files(__package__) / "datasets.json"
    with data_path.open(encoding="utf-8") as f:
        return json.load(f)


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
        artifact_prefix=entry["artifact_prefix"],
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
