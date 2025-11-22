# LangExtract Samples

このリポジトリは、さまざまなパラメータセットで
[LangExtract](https://github.com/google/langextract) を手軽に試すための
プレイグラウンドです。まずは公式 README に記載されている Quick Start 例を再現し、
既知のベースラインを確立してから他のプロンプトやモデルに展開できるようにしています。

## 前提条件

1. Python 3.10 以上。
2. LangExtract が利用できる API キー。
   - Gemini 系モデルの場合は
     [Google AI Studio](https://aistudio.google.com/app/apikey) で作成します。
   - `LANGEXTRACT_API_KEY` としてエクスポートするか、`.env` に追記します:
     ```bash
     export LANGEXTRACT_API_KEY="your-api-key-here"
     ```
3. （推奨）仮想環境の作成と有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

## 依存関係のインストール

ヘルパースクリプトを CLI から直接呼び出せるよう、編集モードでプロジェクトを
インストールします。

```bash
pip install -e .
```

このコマンドで LangExtract が PyPI から取得され、`run-langextract-dataset`
という CLI エントリーポイントが登録されます。

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

主なオプション:

- `--model-id`: LangExtract が認識できる LLM ID（デフォルトは `gemini-2.5-flash`）。
- `--input-text`: Romeo & Juliet のサンプル文をインラインテキストで上書き。
- `--input-file`: 抽出対象のテキストファイルを指定。`--input-text` より優先されます。
- `--output-dir`: 出力先ディレクトリ（既定は `./docs`）。

スクリプトの流れ:

1. LangExtract README の例からプロンプトと few-shot 定義を構築。
2. 指定されたパラメータで `lx.extract(...)` を呼び出し。
3. 構造化された結果を JSONL として保存。
4. インタラクティブな HTML ビジュアライザーを生成・保存。

生成された HTML（例: `docs/romeo_sample.html`）をブラウザで開くと、
ハイライトされたスパンを確認できます。CLI 実行後は `docs/index.html` が自動生成・更新されるため、
ブラウザから JSONL / HTML の一覧テーブルを参照可能です。JSONL のリンクは
内蔵ビューワ（`docs/jsonl_viewer.html`）に遷移し、内容が Base64 で埋め込まれるので
`file://` で開いた場合でもブラウザだけでプレビューできます。
ビューワ冒頭には `extraction_class` / `extraction_text` / `attributes` をまとめた
テーブルも表示されます。

### Medication Named Entity Recognition（薬剤 NER）

[`docs/examples/medication_examples.md`](https://github.com/google/langextract/blob/main/docs/examples/medication_examples.md)
に掲載されている NER 例は `medication` データセットで単体実行できます:

```bash
run-langextract-dataset medication --model-id gemini-2.5-pro
```

### Medication Relationship Extraction（薬剤関係抽出）

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

## 次のステップ

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
