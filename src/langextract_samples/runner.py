"""Shared CLI runner that executes LangExtract datasets."""

from __future__ import annotations

import argparse
import base64
from html import escape
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence
from urllib.parse import quote

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
    extraction_passes: int,
) -> tuple[Path, Path]:
    """Executes a dataset and writes artifacts."""
    config = datasets.get_dataset(dataset_key)
    result = lx.extract(
        text_or_documents=input_text,
        prompt_description=config.prompt_description,
        examples=config.build_examples(),
        model_id=model_id,
        extraction_passes=extraction_passes,
    )
    if config.summary_fn:
        config.summary_fn(result, input_text)
    else:
        print(f"Processed dataset '{dataset_key}'.")
    friendly_model = model_id.replace("/", "_").replace(":", "_")
    prefix = f"{dataset_key}__{friendly_model}__pass{extraction_passes}"
    return save_artifacts(result, output_dir, prefix)


def _parse_artifact_metadata(prefix: str) -> Dict[str, str]:
    """Extracts dataset/model/pass information from artifact names."""
    parts = prefix.split("__")
    dataset_name = parts[0]
    model_name = parts[1] if len(parts) > 1 else ""
    pass_part = parts[2] if len(parts) > 2 else ""
    pass_count = pass_part.replace("pass", "") if pass_part.startswith("pass") else ""
    return {
        "dataset": dataset_name,
        "model": model_name.replace("_", " "),
        "passes": pass_count or "1",
        "prefix": prefix,
    }


def _ensure_jsonl_viewer(viewer_path: Path) -> None:
    viewer_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>JSONL Viewer</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1.5rem; }
    pre { background: #f8f8f8; padding: 1rem; border-radius: 6px; overflow: auto; }
    .entry { margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 6px; padding: 0.75rem; background: #fff; }
    .error { color: #b00020; }
    a { color: #0b57d0; }
    header { margin-bottom: 1.5rem; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }
    th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; vertical-align: top; }
    th { background: #f5f5f5; }
    td:nth-child(2) { min-width: 16rem; white-space: nowrap; }
    caption { text-align: left; font-weight: bold; margin-bottom: 0.5rem; }
    tbody tr:nth-child(even) { background: #fafafa; }
    td div { margin: 0.15rem 0; }
  </style>
</head>
<body>
  <header>
    <h1>JSONL Viewer</h1>
    <p>Showing contents of <code id="file-name"></code></p>
    <p><a href="index.html">Back to outputs index</a></p>
  </header>
  <div id="content"></div>
  <script>
    (() => {
      const params = new URLSearchParams(window.location.search);
      const file = params.get("file");
      const inlineData = params.get("data");
      const fileNameEl = document.getElementById("file-name");
      const contentEl = document.getElementById("content");
      const base64ToBytes = (base64) =>
        Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));

      const renderEntries = (text) => {
        if (!text || !text.trim()) {
          contentEl.innerHTML = "<p>No data in this JSONL file.</p>";
          return;
        }
        const lines = text.trim().split(/\\n+/);
        const parsedDocs = [];
        const listContainer = document.createElement("div");
        lines.forEach((line, idx) => {
          const entry = document.createElement("div");
          entry.className = "entry";
          const header = document.createElement("strong");
          header.textContent = "Entry " + (idx + 1);
          const pre = document.createElement("pre");
          try {
            const parsed = JSON.parse(line);
            parsedDocs.push(parsed);
            pre.textContent = JSON.stringify(parsed, null, 2);
          } catch (err) {
            pre.textContent = line;
            pre.classList.add("error");
          }
          entry.appendChild(header);
          entry.appendChild(pre);
          listContainer.appendChild(entry);
        });

        const table = buildExtractionTable(parsedDocs);
        contentEl.innerHTML = "";
        if (table) {
          contentEl.appendChild(table);
        }
        contentEl.appendChild(listContainer);
      };

      const buildExtractionTable = (documents) => {
        const rows = [];
        documents.forEach((doc, docIndex) => {
          const extractions = Array.isArray(doc.extractions)
            ? doc.extractions
            : [];
          extractions.forEach((extraction, extractionIndex) => {
            rows.push({
              idx: extractionIndex + 1,
              cls: extraction.extraction_class || "-",
              text: extraction.extraction_text || "-",
              attributes: formatAttributes(extraction.attributes),
            });
          });
        });
        if (!rows.length) {
          return null;
        }
        const table = document.createElement("table");
        table.innerHTML = `
          <thead>
            <tr>
              <th>#</th>
              <th>Extraction Class</th>
              <th>Extraction Text</th>
              <th>Attributes</th>
            </tr>
          </thead>
        `;
        const tbody = document.createElement("tbody");
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${row.idx}</td>
            <td>${escapeHtml(row.cls)}</td>
            <td>${escapeHtml(row.text)}</td>
            <td>${row.attributes}</td>
          `;
          tbody.appendChild(tr);
        });
        table.prepend(document.createElement("caption"));
        table.caption.textContent = "Structured Extractions";
        table.appendChild(tbody);
        return table;
      };

      const escapeHtml = (value) => {
        const span = document.createElement("span");
        span.textContent = value ?? "";
        return span.innerHTML || " ";
      };

      const formatAttributes = (attributes) => {
        if (!attributes || typeof attributes !== "object") {
          return "-";
        }
        const entries = Object.entries(attributes);
        if (!entries.length) {
          return "-";
        }
        return entries
          .map(
            ([key, value]) =>
              `<div><strong>${escapeHtml(key)}:</strong> ${escapeHtml(
                String(value)
              )}</div>`
          )
          .join("");
      };

      const showError = (message) => {
      contentEl.innerHTML = "<p class='error'>" + message + "</p>";
    };

      if (!file) {
      fileNameEl.textContent = "(no file selected)";
      showError("Specify ?file=<jsonl name> to view content.");
      return;
    }

      fileNameEl.textContent = file;
      if (inlineData) {
        try {
          renderEntries(
            new TextDecoder("utf-8").decode(base64ToBytes(inlineData))
          );
          return;
      } catch (err) {
        console.error(err);
      }
    }

    fetch(file)
      .then((resp) => {
        if (!resp.ok) throw new Error("Failed to load " + file);
        return resp.text();
      })
      .then(renderEntries)
      .catch((err) => {
        showError(err.message + "<br/>Open via docs/index.html for inline preview.");
      });
    })();
  </script>
</body>
</html>
"""
    viewer_path.write_text(viewer_html, encoding="utf-8")


def _update_outputs_index(output_dir: Path) -> None:
    """Regenerates docs/index.html (or chosen dir) with artifact links."""
    _ensure_jsonl_viewer(output_dir / "jsonl_viewer.html")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    jsonl_blobs: Dict[str, str] = {}
    for path in output_dir.iterdir():
        if not path.is_file():
            continue
        if path.name in {"index.html", "jsonl_viewer.html"}:
            continue
        suffix = path.suffix.lower()
        if suffix not in {".jsonl", ".html"}:
            continue
        prefix = path.stem
        entry = artifacts.setdefault(
            prefix,
            {"dataset": prefix, "jsonl": None, "html": None, "metadata": None},
        )
        if suffix == ".jsonl":
            entry["jsonl"] = path.name
            entry["metadata"] = _parse_artifact_metadata(prefix)
            jsonl_blobs[prefix] = base64.b64encode(
                path.read_text(encoding="utf-8").encode("utf-8")
            ).decode("ascii")
        else:
            entry["html"] = path.name
    index_path = output_dir / "index.html"
    rows = []
    # Sort by dataset, then model, then pass count.
    sorted_entries = sorted(
        artifacts.values(),
        key=lambda item: (
            (item["metadata"] or _parse_artifact_metadata(item["dataset"]))["dataset"],
            (item["metadata"] or _parse_artifact_metadata(item["dataset"]))["model"],
            int(
                (item["metadata"] or _parse_artifact_metadata(item["dataset"]))[
                    "passes"
                ]
            ),
        ),
    )

    for dataset in sorted_entries:
        meta = dataset["metadata"] or _parse_artifact_metadata(dataset["dataset"])
        jsonl_name = dataset["jsonl"]
        if jsonl_name:
            viewer_href = f'jsonl_viewer.html?file={quote(jsonl_name)}'
            inline_data = jsonl_blobs.get(dataset["dataset"])
            if inline_data:
                viewer_href += f"&data={quote(inline_data)}"
            jsonl_cell = f'<a href="{escape(viewer_href)}">{escape(jsonl_name)}</a>'
        else:
            jsonl_cell = "-"
        html_cell = (
            f'<a href="{escape(dataset["html"])}">{escape(dataset["html"])}</a>'
            if dataset["html"]
            else "-"
        )
        rows.append(
            "<tr>"
            f"<td>{escape(meta['dataset'])}</td>"
            f"<td>{escape(meta['model'])}</td>"
            f"<td>{escape(meta['passes'])}</td>"
            f"<td>{jsonl_cell}</td>"
            f"<td>{html_cell}</td>"
            "</tr>"
        )
    if not rows:
        body = "<p>No artifacts have been generated yet.</p>"
    else:
        body = (
            "<table>\n"
            "  <thead><tr><th>Dataset</th><th>Model</th><th>Passes</th><th>JSONL</th><th>HTML</th></tr></thead>\n"
            "  <tbody>\n    "
            + "\n    ".join(rows)
            + "\n  </tbody>\n</table>"
        )
    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>LangExtract Samples Outputs</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 960px; }}
    th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    tbody tr:nth-child(even) {{ background: #fafafa; }}
    td:nth-child(2) {{ white-space: nowrap; min-width: 16rem; }}
  </style>
</head>
<body>
  <h1>LangExtract Samples Outputs</h1>
  <p>Artifacts are written to this directory after running the CLI.</p>
  {body}
</body>
</html>
"""
    index_path.write_text(html_text, encoding="utf-8")


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
    dataset_positional_name: Optional[str] = None
    if needs_dataset_arg:
        parser.add_argument(
            "dataset_key",
            nargs="?",
            choices=available,
            help="Dataset key to run. If omitted, runs all available datasets.",
        )
        dataset_positional_name = "dataset_key"
        parser.add_argument(
            "--dataset",
            choices=available,
            help="Dataset key to run (same as positional argument).",
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
        default=Path("docs"),
        help="Directory for JSONL + HTML artifacts (default: ./docs).",
    )
    parser.add_argument(
        "--extraction-passes",
        type=int,
        help="Number of extraction passes to run (default uses dataset setting).",
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

    selected_dataset: Optional[str] = None
    if needs_dataset_arg:
        positional_value = getattr(args, dataset_positional_name)
        if args.dataset and positional_value and args.dataset != positional_value:
            parser.error(
                f"--dataset ({args.dataset}) and positional dataset argument "
                f"({positional_value}) must match."
            )
        selected_dataset = args.dataset or positional_value
    dataset_keys = (
        [selected_dataset]
        if selected_dataset
        else list(available if needs_dataset_arg else available)
    )

    input_text_override: Optional[str] = None
    if args.input_file:
        input_text_override = args.input_file.read_text(encoding="utf-8")
    elif args.input_text:
        input_text_override = args.input_text

    multiple = len(dataset_keys) > 1
    for dataset_key in dataset_keys:
        config = datasets.get_dataset(dataset_key)
        model_id = args.model_id or config.default_model_id
        input_text = input_text_override or config.default_input_text
        extraction_passes = args.extraction_passes or config.extraction_passes

        print(f"\n=== Running dataset: {dataset_key} ===")
        jsonl_path, html_path = run_dataset(
            dataset_key=dataset_key,
            model_id=model_id,
            input_text=input_text,
            output_dir=args.output_dir,
            extraction_passes=extraction_passes,
        )
        prefix = f"[{dataset_key}] " if multiple else ""
        print(f"\n{prefix}Saved structured output to: {jsonl_path}")
        print(f"{prefix}Saved visualization to:     {html_path}")
        print(f"{prefix}Open the HTML file in a browser to review highlighted spans.")
    _update_outputs_index(args.output_dir)


def main() -> None:
    run_cli()


__all__ = ["run_dataset", "run_cli", "main"]
