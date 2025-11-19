"""Shared CLI runner that executes LangExtract datasets."""

from __future__ import annotations

import argparse
import base64
import json
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
        if path.name in {"index.html", "jsonl_viewer.html", "comparison.html"}:
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
  <p>
    Artifacts are written to this directory after running the CLI. 
    <a href="comparison.html"><strong>Compare Datasets</strong></a>
  </p>
  {body}
</body>
</html>
"""
    _ensure_comparison_viewer(output_dir / "comparison.html", artifacts, jsonl_blobs)
    index_path.write_text(html_text, encoding="utf-8")


def _ensure_comparison_viewer(
    viewer_path: Path, artifacts: Dict[str, Any], jsonl_blobs: Dict[str, str]
) -> None:
    """Generates a comparison viewer for multiple runs of datasets."""
    # Build a manifest of available datasets and their runs
    manifest = {}
    for key, data in artifacts.items():
        meta = data["metadata"] or _parse_artifact_metadata(key)
        dataset_name = meta["dataset"]
        if dataset_name not in manifest:
            manifest[dataset_name] = []
        
        if data["jsonl"]:
            manifest[dataset_name].append({
                "model": meta["model"],
                "passes": meta["passes"],
                "file": data["jsonl"],
                "data": jsonl_blobs.get(key, "")
            })

    # Sort runs for each dataset
    for dataset in manifest:
        manifest[dataset].sort(key=lambda x: (x["model"], int(x["passes"])))

    viewer_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Dataset Comparison</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 1.5rem; }}
    header {{ margin-bottom: 1.5rem; }}
    .controls {{ margin-bottom: 1.5rem; padding: 1rem; background: #f5f5f5; border-radius: 6px; }}
    select {{ padding: 0.5rem; font-size: 1rem; min-width: 200px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; table-layout: fixed; }}
    th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: left; vertical-align: top; word-wrap: break-word; }}
    th {{ background: #f5f5f5; position: sticky; top: 0; z-index: 10; }}
    .entry-row:nth-child(even) {{ background: #fafafa; }}
    .diff-add {{ background-color: #e6ffec; }}
    .diff-del {{ background-color: #ffebe9; }}
    .meta-info {{ font-size: 0.85em; color: #666; margin-bottom: 0.5rem; }}
    .extraction-item {{ border-bottom: 1px solid #eee; padding: 4px 0; }}
    .extraction-item:last-child {{ border-bottom: none; }}
    .attr-list {{ font-size: 0.9em; color: #444; margin-left: 1em; }}
  </style>
</head>
<body>
  <header>
    <h1>Dataset Comparison</h1>
    <p><a href="index.html">Back to outputs index</a></p>
  </header>

  <div class="controls">
    <label for="dataset-select">Select Dataset: </label>
    <select id="dataset-select">
      <option value="">-- Select a dataset --</option>
    </select>
  </div>

  <div id="content"></div>

  <script>
    const manifest = {json.dumps(manifest)};

    const selectEl = document.getElementById('dataset-select');
    const contentEl = document.getElementById('content');

    // Populate dropdown
    Object.keys(manifest).sort().forEach(ds => {{
        const option = document.createElement('option');
        option.value = ds;
        option.textContent = ds + ' (' + manifest[ds].length + ' runs)';
        selectEl.appendChild(option);
    }});

    // Handle selection
    selectEl.addEventListener('change', (e) => {{
        const dataset = e.target.value;
        if (!dataset) {{
            contentEl.innerHTML = '';
            return;
        }}
        renderComparison(dataset);
    }});

    const base64ToBytes = (base64) =>
        Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));

    function renderComparison(dataset) {{
        contentEl.innerHTML = '<p>Loading...</p>';
        const runs = manifest[dataset];
        
        try {{
            const parsedRuns = runs.map(run => {{
                let text = "";
                if (run.data) {{
                    text = new TextDecoder("utf-8").decode(base64ToBytes(run.data));
                }}
                return {{
                    meta: run,
                    entries: text.trim().split(/\\n+/).map(line => {{
                        try {{ return JSON.parse(line); }}
                        catch(e) {{ return null; }}
                    }})
                }};
            }});

            buildTable(parsedRuns);
        }} catch (err) {{
            contentEl.innerHTML = '<p class="error">Error loading data: ' + err.message + '</p>';
        }}
    }}

    function buildTable(runs) {{
        if (runs.length === 0) {{
            contentEl.innerHTML = '<p>No data found.</p>';
            return;
        }}

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        
        // Header row
        const trHead = document.createElement('tr');
        trHead.innerHTML = '<th>Entry</th>';
        runs.forEach(run => {{
            const th = document.createElement('th');
            th.innerHTML = `
                <div>${{run.meta.model}}</div>
                <div class="meta-info">Passes: ${{run.meta.passes}}</div>
                <div class="meta-info"><a href="${{run.meta.file}}" target="_blank">JSONL</a></div>
            `;
            trHead.appendChild(th);
        }});
        thead.appendChild(trHead);
        table.appendChild(thead);

        // Determine max entries
        const maxEntries = Math.max(...runs.map(r => r.entries.length));

        for (let i = 0; i < maxEntries; i++) {{
            const tr = document.createElement('tr');
            tr.className = 'entry-row';
            
            // Entry number
            const tdNum = document.createElement('td');
            tdNum.textContent = i + 1;
            tr.appendChild(tdNum);

            runs.forEach(run => {{
                const td = document.createElement('td');
                const entry = run.entries[i];
                
                if (entry && entry.extractions) {{
                    entry.extractions.forEach(ext => {{
                        const div = document.createElement('div');
                        div.className = 'extraction-item';
                        
                        let html = `<strong>${{escapeHtml(ext.extraction_class)}}</strong>: ${{escapeHtml(ext.extraction_text)}}`;
                        
                        if (ext.attributes && Object.keys(ext.attributes).length > 0) {{
                            html += '<div class="attr-list">';
                            Object.entries(ext.attributes).forEach(([k, v]) => {{
                                html += `<div>${{escapeHtml(k)}}: ${{escapeHtml(String(v))}}</div>`;
                            }});
                            html += '</div>';
                        }}
                        
                        div.innerHTML = html;
                        td.appendChild(div);
                    }});
                }} else {{
                    td.textContent = '-';
                }}
                tr.appendChild(td);
            }});
            tbody.appendChild(tr);
        }}
        
        table.appendChild(tbody);
        contentEl.innerHTML = '';
        contentEl.appendChild(table);
    }}

    function escapeHtml(unsafe) {{
        if (unsafe === null || unsafe === undefined) return '';
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }}
  </script>
</body>
</html>
"""
    viewer_path.write_text(viewer_html, encoding="utf-8")


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

if __name__ == "__main__":
    main()
