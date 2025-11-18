"""Dataset registry and helper utilities for LangExtract sample scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional
import textwrap

import langextract as lx


AnnotatedDocument = lx.data.AnnotatedDocument
ExampleBuilder = Callable[[], List[lx.data.ExampleData]]
SummaryFn = Callable[[AnnotatedDocument, str], None]


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


def _relationship_summary(
    result: AnnotatedDocument, input_text: str
) -> None:
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


def _build_romeo_examples() -> List[lx.data.ExampleData]:
    return [
        lx.data.ExampleData(
            text=(
                "ROMEO. But soft! What light through yonder window breaks? "
                "It is the east, and Juliet is the sun."
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="ROMEO",
                    attributes={"emotional_state": "wonder"},
                ),
                lx.data.Extraction(
                    extraction_class="emotion",
                    extraction_text="But soft!",
                    attributes={"feeling": "gentle awe"},
                ),
                lx.data.Extraction(
                    extraction_class="relationship",
                    extraction_text="Juliet is the sun",
                    attributes={"type": "metaphor"},
                ),
            ],
        )
    ]


def _build_medication_ner_examples() -> List[lx.data.ExampleData]:
    return [
        lx.data.ExampleData(
            text="Patient was given 250 mg IV Cefazolin TID for one week.",
            extractions=[
                lx.data.Extraction(extraction_class="dosage", extraction_text="250 mg"),
                lx.data.Extraction(extraction_class="route", extraction_text="IV"),
                lx.data.Extraction(
                    extraction_class="medication", extraction_text="Cefazolin"
                ),
                lx.data.Extraction(
                    extraction_class="frequency", extraction_text="TID"
                ),
                lx.data.Extraction(
                    extraction_class="duration", extraction_text="for one week"
                ),
            ],
        )
    ]


def _build_medication_relationship_examples() -> List[lx.data.ExampleData]:
    return [
        lx.data.ExampleData(
            text=(
                "Patient takes Aspirin 100mg daily for heart health and "
                "Simvastatin 20mg at bedtime."
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="medication",
                    extraction_text="Aspirin",
                    attributes={"medication_group": "Aspirin"},
                ),
                lx.data.Extraction(
                    extraction_class="dosage",
                    extraction_text="100mg",
                    attributes={"medication_group": "Aspirin"},
                ),
                lx.data.Extraction(
                    extraction_class="frequency",
                    extraction_text="daily",
                    attributes={"medication_group": "Aspirin"},
                ),
                lx.data.Extraction(
                    extraction_class="condition",
                    extraction_text="heart health",
                    attributes={"medication_group": "Aspirin"},
                ),
                lx.data.Extraction(
                    extraction_class="medication",
                    extraction_text="Simvastatin",
                    attributes={"medication_group": "Simvastatin"},
                ),
                lx.data.Extraction(
                    extraction_class="dosage",
                    extraction_text="20mg",
                    attributes={"medication_group": "Simvastatin"},
                ),
                lx.data.Extraction(
                    extraction_class="frequency",
                    extraction_text="at bedtime",
                    attributes={"medication_group": "Simvastatin"},
                ),
            ],
        )
    ]


ROMEO_PROMPT = textwrap.dedent(
    """\
    Extract characters, emotions, and relationships in order of appearance.
    Use exact text for extractions. Do not paraphrase or overlap entities.
    Provide meaningful attributes for each entity to add context."""
)

DEFAULT_REL_INPUT = textwrap.dedent(
    """\
    The patient was prescribed Lisinopril and Metformin last month.
    He takes the Lisinopril 10mg daily for hypertension, but often misses
    his Metformin 500mg dose which should be taken twice daily for diabetes.
    """
)


DATASETS: Dict[str, DatasetConfig] = {
    "romeo_quickstart": DatasetConfig(
        key="romeo_quickstart",
        title="Romeo & Juliet Quick Start",
        description="Characters, emotions, and relationships using the README example.",
        prompt_description=ROMEO_PROMPT,
        default_input_text=(
            "Lady Juliet gazed longingly at the stars, her heart aching for Romeo."
        ),
        default_model_id="gemini-2.5-flash-lite",
        artifact_prefix="romeo_juliet_basic",
        build_examples=_build_romeo_examples,
        summary_fn=_basic_summary,
    ),
    "medication_ner": DatasetConfig(
        key="medication_ner",
        title="Medication Named Entity Recognition",
        description=(
            "Extract medication name, dosage, route, frequency, and duration "
            "from simple sentences."
        ),
        prompt_description=(
            "Extract medication information including medication name, dosage, "
            "route, frequency, and duration in the order they appear in the text."
        ),
        default_input_text="Patient took 400 mg PO Ibuprofen q4h for two days.",
        default_model_id="gemini-2.5-pro",
        artifact_prefix="medication_ner",
        build_examples=_build_medication_ner_examples,
        summary_fn=_basic_summary,
    ),
    "medication_relationship": DatasetConfig(
        key="medication_relationship",
        title="Medication Relationship Extraction",
        description=(
            "Group medication details using medication_group attributes to link "
            "dosage, frequency, and indications."
        ),
        prompt_description=textwrap.dedent(
            """\
            Extract medications with their details, using attributes to group related information:

            1. Extract entities in the order they appear in the text
            2. Each entity must have a 'medication_group' attribute linking it to its medication
            3. All details about a medication should share the same medication_group value
            """
        ),
        default_input_text=DEFAULT_REL_INPUT,
        default_model_id="gemini-2.5-pro",
        artifact_prefix="medication_relationship",
        build_examples=_build_medication_relationship_examples,
        summary_fn=_relationship_summary,
    ),
}


def get_dataset(key: str) -> DatasetConfig:
    """Returns the dataset configuration for a given key."""
    if key not in DATASETS:
        raise KeyError(f"Unknown dataset: {key}")
    return DATASETS[key]


def list_dataset_keys() -> Iterable[str]:
    """Returns the known dataset keys in insertion order."""
    return DATASETS.keys()


__all__ = ["DatasetConfig", "DATASETS", "get_dataset", "list_dataset_keys"]
