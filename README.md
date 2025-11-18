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
`run-langextract-dataset`.

## 共通ランナーとデータセット

すべての例は `src/langextract_samples/datasets.py` に定義されたデータセットを
`src/langextract_samples/runner.py` の共通ロジックで実行します。
データセット一覧は CLI から確認できます。

```bash
run-langextract-dataset --list-datasets
```

任意のデータセットを直接指定することも可能です:

```bash
run-langextract-dataset romeo_quickstart --model-id gemini-2.5-flash
```

データセット引数を省略すると、登録済みの全データセットを順番に実行します:

```bash
run-langextract-dataset
```

共通オプション:

- `dataset` / `--dataset`: 実行するデータセットキー。
- `--model-id`: LangExtract に渡すモデル ID（デフォルトは各データセットで定義）。
- `--input-text` / `--input-file`: デフォルトの入力テキストを上書き。
- `--output-dir`: 出力フォルダ（既定 `./outputs`）。

## データセット別の実行例

### Romeo & Juliet Quick Start

README に記載の Quick Start 例（人物・感情・関係の抽出）は `romeo_quickstart`
データセットで再現できます:

```bash
run-langextract-dataset romeo_quickstart \
  --model-id gemini-2.5-flash \
  --output-dir outputs
```

Key options:

- `--model-id`: LLM identifier recognized by LangExtract (default:
  `gemini-2.5-flash`).
- `--input-text`: Override the built-in Romeo & Juliet snippet with inline text.
- `--input-file`: Provide a text file to extract from; takes precedence over
  `--input-text`.
- `--output-dir`: Destination directory (defaults to `./outputs`).

The script:

1. Builds the example prompt and few-shot definitions from the LangExtract
   README.
2. Calls `lx.extract(...)` with the provided parameters.
3. Stores the structured results as JSONL.
4. Generates and saves the interactive HTML visualization.

Open the resulting HTML file (e.g.
`outputs/romeo_sample.html`) in your browser to verify the highlighted spans.

### Medication Named Entity Recognition

[`docs/examples/medication_examples.md`](https://github.com/google/langextract/blob/main/docs/examples/medication_examples.md)
の NER 例は `medication_ner` データセットで単体実行できます:

```bash
run-langextract-dataset medication_ner --model-id gemini-2.5-pro
```

### Medication Relationship Extraction

投与情報を `medication_group` で紐付けする例は `medication_relationship`
データセットで実行できます:

```bash
run-langextract-dataset medication_relationship --model-id gemini-2.5-pro
```

どちらのデータセットも CLI から入力テキストや出力先を差し替えられるため、
シナリオごとに同じ枠組みで比較できます。

## Next Steps

### データセット定義ファイル

すべてのシナリオは リポジトリ直下の `dataset/<key>.json`
（1 ファイル 1 データセット）に記述されています。
JSON 形式なので、Python コードを触らずに差し替え・追加が可能です。

各エントリの主なフィールド（ファイル名が CLI で指定するキーになります。例:
`dataset/romeo_quickstart.json` → `romeo_quickstart`）:

- `title` / `description`: `--list-datasets` の表示用メタデータ
- `prompt_description`: LangExtract に渡す抽出指示
- `default_input_text`: 標準入力テキスト
- `default_model_id`: 想定モデル ID
- `summary_type`: `basic`（一覧表示）か `relationship`
- `examples`: few-shot 例 (`text` と `extractions` の配列)

`extractions` の要素は `extraction_class`・`extraction_text`・
必要に応じて `attributes` を指定します。`summary_type` を追加したい場合は
`datasets.py` の `SUMMARY_HANDLERS` に対応関数を定義してください。
JSONL / HTML の出力ファイル名はデータセットキー（= JSON ファイル名）がプレフィックスになります。

### 新しいデータセットの追加手順

1. `dataset/` に `<key>.json` を追加する。
2. 既存 CLI (`run-langextract-dataset`) で `新キー` を引数に実行する。
   必要なら `pyproject.toml` の `[project.scripts]` に専用エントリポイントを追加。

これで複数パラメータのベンチマークを共通フレームワークで管理しつつ、
データセットを JSON で差し替えて比較できます。
