"""Shared CLI runner that executes LangExtract datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional, Sequence

import langextract as lx

from . import datasets


def save_artifacts(
    result: lx.data.AnnotatedDocument, output_dir: Path, artifact_prefix: str
) -> tuple[Path, Path]:
    """Writes JSONL + HTML visualization and returns their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_name = f"{artifact_prefix}.jsonl"
    lx.io.save_annotated_documents(
        [result], output_name=jsonl_name, output_dir=str(output_dir)
    )
    jsonl_path = output_dir / jsonl_name

    html_content = lx.visualize(str(jsonl_path))
    html_text = html_content.data if hasattr(html_content, "data") else html_content
    html_path = output_dir / f"{artifact_prefix}.html"
    html_path.write_text(html_text)
    return jsonl_path, html_path


def run_dataset(
    dataset_key: str,
    *,
    model_id: str,
    input_text: str,
    output_dir: Path,
    artifact_prefix: str,
) -> tuple[Path, Path]:
    """Executes a dataset and writes artifacts."""
    config = datasets.get_dataset(dataset_key)
    result = lx.extract(
        text_or_documents=input_text,
        prompt_description=config.prompt_description,
        examples=config.build_examples(),
        model_id=model_id,
    )
    if config.summary_fn:
        config.summary_fn(result, input_text)
    else:
        print(f"Processed dataset '{dataset_key}'.")
    return save_artifacts(result, output_dir, artifact_prefix)


def _comma_join(items: Iterable[str]) -> str:
    return ", ".join(items)


def run_cli(
    *,
    allowed_dataset_keys: Optional[Sequence[str]] = None,
    default_dataset_key: Optional[str] = None,
) -> None:
    """Parses arguments and executes the requested dataset."""
    available = list(allowed_dataset_keys or datasets.list_dataset_keys())
    if not available:
        raise SystemExit("No datasets registered.")
    if default_dataset_key is None:
        default_dataset_key = available[0]
    if default_dataset_key not in available:
        raise SystemExit(
            f"default_dataset_key='{default_dataset_key}' not in "
            f"allowed datasets: {_comma_join(available)}"
        )

    parser = argparse.ArgumentParser(
        description="Run a predefined LangExtract dataset scenario."
    )
    needs_dataset_arg = len(available) > 1
    if needs_dataset_arg:
        parser.add_argument(
            "--dataset",
            choices=available,
            default=default_dataset_key,
            help="Dataset key to run.",
        )
    parser.add_argument(
        "--model-id",
        help="Override the default model for the dataset.",
    )
    parser.add_argument(
        "--input-text",
        help="Inline text to process instead of the dataset default snippet.",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Path to a text file that overrides --input-text.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for JSONL + HTML artifacts (default: ./outputs).",
    )
    parser.add_argument(
        "--artifact-prefix",
        help="Filename prefix for generated artifacts.",
    )
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="Print available dataset keys and exit.",
    )
    args = parser.parse_args()

    if args.list_datasets:
        for key in available:
            config = datasets.get_dataset(key)
            print(f"{key}: {config.title}")
        return

    dataset_key = args.dataset if needs_dataset_arg else available[0]
    config = datasets.get_dataset(dataset_key)

    model_id = args.model_id or config.default_model_id
    input_text = args.input_text or config.default_input_text
    if args.input_file:
        input_text = args.input_file.read_text(encoding="utf-8")
    artifact_prefix = args.artifact_prefix or config.artifact_prefix

    jsonl_path, html_path = run_dataset(
        dataset_key=dataset_key,
        model_id=model_id,
        input_text=input_text,
        output_dir=args.output_dir,
        artifact_prefix=artifact_prefix,
    )
    print(f"\nSaved structured output to: {jsonl_path}")
    print(f"Saved visualization to:     {html_path}")
    print("Open the HTML file in a browser to review highlighted spans.")


def main() -> None:
    run_cli()


__all__ = ["run_dataset", "run_cli", "main"]
