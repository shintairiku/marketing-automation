# Fact-Check + Text-Edit マルチエージェント利用ガイド

このディレクトリには Codex 互換テキスト編集エージェントと、HTML記事のファクトチェック→必要時修正を自動で行う `fact_check_multi_agent.py` が含まれます。以下にセットアップと使い方をまとめます。

## 事前準備
- Python 3.12 以上を想定しています。
- 仮想環境を有効化し、必要パッケージをインストールします。
  ```bash
  pip install openai-agents beautifulsoup4 html5lib lxml rich
  ```
  ※ `lxml` が無い場合でも動作しますが、HTMLパースの精度向上のためインストール推奨です。
- OpenAI API キーを `OPENAI_API_KEY` に設定してください。
  ```bash
  export OPENAI_API_KEY=sk-...
  ```

## 主要ファイル
- `fact_check_multi_agent.py`: ファクトチェック＋テキスト編集のCLI。`patch` と `fact-check` の2サブコマンドを提供します。
- `edit_agent.py`: 既存の Codex 互換テキスト編集CLI（参考用）。
- `test.html`: 動作確認用のサンプルHTML。

## ファクトチェック → 必要なら編集
HTML記事を検証し、誤りがあると判断した場合だけ apply_patch 編集を行います。
```bash
python fact_check_multi_agent.py fact-check --article ./test.html
```
主なオプション:
- `--edit-file`: 編集対象ファイル（省略時は `--article` と同じ）。
- `--fact-model`: ファクトチェックモデル名（デフォルト `gpt-5-mini`）。
- `--edit-model`: 編集用モデル名（デフォルト `gpt-5-mini`）。
- `--fact-max-turns`, `--edit-max-turns`: 各エージェントの最大ターン数。
- `--force-text-tools`: Text-Editエージェントにapply_patch利用を必須化。
- `--allow-agent-handoff`: Fact-Checkエージェントからの自律ハンドオフを有効化。

### 実行ログの読み方
ターミナル出力に `[agents] phase_start:read` などのステータスメッセージが表示され、
以下の情報がリアルタイムで確認できます。
- `phase_start / phase_done`: Fact-Checkの3フェーズ（read / search / synthesis）。
- `tool:web_search`: Web検索ツール起動。回数は `web_search_count` として最終表示。
- `llm_start / llm_end`: モデル呼び出しの開始・完了。
- `text_edit_start / text_edit_done`: Text-Editエージェント実行状況。

## テキスト編集のみ（インタラクティブ）
単体の Codex 互換エージェントを使う場合は `patch` サブコマンドを使用します。
```bash
python fact_check_multi_agent.py patch --file ./sample.md
```
起動後はプロンプトにコマンド（例: `read_file(offset=1, limit_lines=120)`）を入力し、
apply_patch 差分を出力するフローは `edit_agent.py` と同等です。

## トレーシング / セッション
- `--session` で `SQLiteSession` のIDを指定し、複数回実行で状態を継続できます。
- `--trace-workflow-name`, `--trace-id`, `--trace-group-id`, `--disable-tracing` により
  OpenAIトレーシングの制御が可能です。

## エラー時のヒント
- `read_article` でパーサーが無い場合は自動的に `html.parser` → `html5lib` → プレーンテキストに切り替えます。
- Web検索が未実行の場合は処理を中断しエラーになります。ネットワーク権限や `OPENAI_API_KEY` を確認してください。
- モデルが `temperature` 非対応の場合でも本スクリプトは自動的にパラメータ送信を抑制します。

## 参考フロー
1. `test.html` に修正が必要な主張を仕込む。
2. `python fact_check_multi_agent.py fact-check --article test.html` を実行。
3. `[agents]` ログで `tool:web_search` が呼ばれていること、`FactCheckReport` が出力されることを確認。
4. `needs_edit=True` の場合は `=== Text-Edit Agent Final Output ===` にapply_patchが表示されます。

以上を参考に、OpenAI Agents SDK を用いたマルチエージェント運用を行ってください。
