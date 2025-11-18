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
- `--output-dir`: 出力フォルダ（既定 `./docs`）。
- `--extraction-passes`: LangExtract の `extraction_passes` 値を上書き。
- CLI は `dataset__model__passN` という命名規則で成果物を保存するため、
  `docs/index.html` の表からモデルやパス回数をすぐ確認できます。

## データセット別の実行例

### Romeo & Juliet Quick Start

README に記載の Quick Start 例（人物・感情・関係の抽出）は `romeo_quickstart`
データセットで再現できます:

```bash
run-langextract-dataset romeo_quickstart \
  --model-id gemini-2.5-flash \
  --output-dir docs
```

Key options:

- `--model-id`: LLM identifier recognized by LangExtract (default:
  `gemini-2.5-flash`).
- `--input-text`: Override the built-in Romeo & Juliet snippet with inline text.
- `--input-file`: Provide a text file to extract from; takes precedence over
  `--input-text`.
- `--output-dir`: Destination directory (defaults to `./docs`).

The script:

1. Builds the example prompt and few-shot definitions from the LangExtract
   README.
2. Calls `lx.extract(...)` with the provided parameters.
3. Stores the structured results as JSONL.
4. Generates and saves the interactive HTML visualization.

Open the resulting HTML file (e.g.
`docs/romeo_sample.html`) in your browser to verify the highlighted spans.
CLI 実行後は `docs/index.html` が自動生成・更新されるので、ブラウザで開くと
JSONL / HTML の一覧テーブルを確認できます。JSONL のリンクは内蔵ビューワ
（`docs/jsonl_viewer.html`）に遷移します。リンクには JSONL の中身が Base64 で
埋め込まれるため、`file://` で開いた場合でもブラウザだけで確認できます。
ビューワでは JSONL の詳細表示に加えて、`extraction_class` / `extraction_text` /
`attributes` をまとめたテーブルも先頭に表示します。

### Medication Named Entity Recognition

[`docs/examples/medication_examples.md`](https://github.com/google/langextract/blob/main/docs/examples/medication_examples.md)
の NER 例は `medication` データセットで単体実行できます:

```bash
run-langextract-dataset medication --model-id gemini-2.5-pro
```

### Medication Relationship Extraction

投与情報を `medication_group` で紐付けする例は `medication_relationship`
データセットで実行できます:

```bash
run-langextract-dataset medication_relationship --model-id gemini-2.5-pro
```

どちらのデータセットも CLI から入力テキストや出力先を差し替えられるため、
シナリオごとに同じ枠組みで比較できます。

### 日本語データセット

英語版と同じスキーマで、日本語テキスト・プロンプトを用意したデータセットも
登録しています。

- `romeo_quickstart_ja`: ロミオとジュリエットの台詞を日本語に翻訳した抽出課題
  ```bash
  run-langextract-dataset romeo_quickstart_ja --model-id gemini-2.5-flash-lite
  ```
- `medication_ja`: 日本語文から投薬情報（薬剤名・用量など）を抽出
  ```bash
  run-langextract-dataset medication_ja --model-id gemini-2.5-flash-lite
  ```
- `medication_relationship_ja`: `medication_group` 属性付きの服薬関係抽出（日本語）
  ```bash
  run-langextract-dataset medication_relationship_ja --model-id gemini-2.5-flash-lite
  ```

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
- `extraction_passes`: LangExtract の `extraction_passes` 引数（省略時は 1）
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
