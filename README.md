# LangExtract Samples

This repository hosts a lightweight playground for running
[LangExtract](https://github.com/google/langextract) with different parameter
sets. The first step is to replicate the official Quick Start example so we
have a known-good baseline before fanning out to other prompts or models.

## Prerequisites

1. Python 3.10+.
2. An API key that LangExtract can use with your preferred provider.
   - For Gemini models, create a key in
     [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Export it as `LANGEXTRACT_API_KEY` or add it to a `.env` file:
     ```bash
     export LANGEXTRACT_API_KEY="your-api-key-here"
     ```
3. (Recommended) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

## Install Dependencies

Install the project in editable mode so the helper script is available as a CLI.

```bash
pip install -e .
```

This pulls LangExtract from PyPI and registers the CLI entry point
`run-langextract-example`.

## 共通ランナーとデータセット

すべての例は `src/langextract_samples/datasets.py` に定義されたデータセットを
`src/langextract_samples/runner.py` の共通ロジックで実行します。
データセット一覧は CLI から確認できます。

```bash
run-langextract-dataset --list-datasets
```

任意のデータセットを直接指定することも可能です:

```bash
run-langextract-dataset --dataset romeo_quickstart --model-id gemini-2.5-flash
```

共通オプション:

- `--dataset`: 実行するデータセットキー。
- `--model-id`: LangExtract に渡すモデル ID（デフォルトは各データセットで定義）。
- `--input-text` / `--input-file`: デフォルトの入力テキストを上書き。
- `--output-dir`: 出力フォルダ（既定 `./outputs`）。
- `--artifact-prefix`: JSONL / HTML のファイル名プレフィックス。

## データセット別の実行例

### Romeo & Juliet Quick Start

`src/langextract_samples/examples_cli.py` の `romeo_main` エントリポイントは README に記載の
Quick Start 例（人物・感情・関係の抽出）をそのまま実行します:

```bash
run-langextract-example \
  --model-id gemini-2.5-flash \
  --output-dir outputs \
  --artifact-prefix romeo_sample
```

Key options:

- `--model-id`: LLM identifier recognized by LangExtract (default:
  `gemini-2.5-flash`).
- `--input-text`: Override the built-in Romeo & Juliet snippet with inline text.
- `--input-file`: Provide a text file to extract from; takes precedence over
  `--input-text`.
- `--output-dir`: Destination directory (defaults to `./outputs`).
- `--artifact-prefix`: File prefix for both the `.jsonl` and `.html`
  artifacts.

The script:

1. Builds the example prompt and few-shot definitions from the LangExtract
   README.
2. Calls `lx.extract(...)` with the provided parameters.
3. Stores the structured results as JSONL.
4. Generates and saves the interactive HTML visualization.

Open the resulting HTML file (e.g.
`outputs/romeo_sample.html`) in your browser to verify the highlighted spans.

### Medication Named Entity Recognition

`src/langextract_samples/examples_cli.py` の `medication_ner_main` は
[`docs/examples/medication_examples.md`](https://github.com/google/langextract/blob/main/docs/examples/medication_examples.md)
の NER 例を単体で再現します:

```bash
run-medication-ner-example --model-id gemini-2.5-pro
# または
run-langextract-dataset --dataset medication_ner --model-id gemini-2.5-pro
```

### Medication Relationship Extraction

投与情報を `medication_group` で紐付けする例は
`src/langextract_samples/examples_cli.py` の `medication_relationship_main` に分岐しています:

```bash
run-medication-relationship-example --model-id gemini-2.5-pro
# または
run-langextract-dataset --dataset medication_relationship --model-id gemini-2.5-pro
```

どちらのデータセットも CLI から入力テキストや出力先を差し替えられるため、
シナリオごとに同じ枠組みで比較できます。

## Next Steps

### データセット定義ファイル

すべてのシナリオは `src/langextract_samples/datasets.json` に記述されています。
JSON 形式なので、Python コードを触らずに差し替え・追加が可能です。

各エントリの主なフィールド:

- `key`: CLI で指定する識別子（例: `romeo_quickstart`）
- `title` / `description`: `--list-datasets` の表示用メタデータ
- `prompt_description`: LangExtract に渡す抽出指示
- `default_input_text`: 標準入力テキスト
- `default_model_id`: 想定モデル ID
- `artifact_prefix`: JSONL/HTML のデフォルトファイル名
- `summary_type`: `basic`（一覧表示）か `relationship`
- `examples`: few-shot 例 (`text` と `extractions` の配列)

`extractions` の要素は `extraction_class`・`extraction_text`・
必要に応じて `attributes` を指定します。`summary_type` を追加したい場合は
`datasets.py` の `SUMMARY_HANDLERS` に対応関数を定義してください。

### 新しいデータセットの追加手順

1. `datasets.json` に新しいオブジェクトを追加する。
2. 既存 CLI (`run-langextract-dataset`) で `--dataset 新キー` を実行する。
   必要なら `pyproject.toml` の `[project.scripts]` に専用エントリポイントを追加。

これで複数パラメータのベンチマークを共通フレームワークで管理しつつ、
データセットを JSON で差し替えて比較できます。
