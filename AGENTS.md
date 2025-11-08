## 開発ガイドライン（README.mdより抜粋・補足）

### 概要

{未定義}

---

## ストーリー作成ガイドライン

作成場所: プロジェクトのルートディレクトリ直下の`story`フォルダ内

下記のテンプレートに従い、ストーリーを作成してください。

```markdown
# {ストーリーのタイトル}

## 概要

{ストーリーの概要を記載してください}

## 実行手順

**必須**: フェーズ内のすべてのタスクにチェックがつくまで、次のフェーズに進まないでください。

### Phase 1: 要件定義・設計【対話フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [ ] ストーリーの内容を確認する
- [ ] 実現方法を具体化をする
- [ ] **実現方法の具体化内容についてユーザーから承認を得る**
- [ ] 承認を得た内容をストーリーに反映する

#### 実現案

{実現案を記載してください}

### Phase 2: 実装【実装フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [ ] {必要に応じて実装手順を追加してください}
- [ ] Lint（uv run ruff check . --fix）/ 型チェック（mypy）が通る
- [ ] `CODE_REVIEW_GUIDE.md` に準拠してコードレビューをする
  - AIエージェントが行うので、PRの作成は不要です
- [ ] **ユーザーからのコードレビューを受ける**

### Phase 3: テスト【テストフェーズ】(上から順にチェックしてください)

- [ ] テストコードを作成する
- [ ] テストが全てパスする
- [ ] **ユーザーが受け入れテストをする**

### Phase 4: ドキュメント化【ドキュメント更新フェーズ】(上から順にチェックしてください)

- [ ] 実装内容（`*.exp.md`）を更新する
- [ ] README.md、AGENTS.md を更新する

### Phase 5: コミット・プッシュ【最終フェーズ】(上から順にチェックしてください)

- [ ] コードのコミットメッセージを作成する
- [ ] **ユーザーからコミットメッセージの承認を受ける**
- ストーリーにチェック後にコミット・プッシュする
```

## 実装内容(ドキュメント)作成ガイドライン

以下の条件に従い、指定されたコードファイルをexplainしたドキュメントを作成してください。

- ドキュメントの配置場所：コードファイルと同じパスに配置する
- ドキュメントファイル名：{コードファイル名} + `.exp.md`
  - コードファイル名が`hoge.php`の場合は、explainドキュメント名は`hoge.php.exp.md`となる
- explainではコード内で利用しているクラスのファイルパスを一覧でまとめるのも必須です

注意: テストコードは除外してください。

---

## Phase 4: ドキュメント更新方針

### Phase 4 で更新するドキュメント一覧

- README.md
  - Slack App設定手順（`reactions:write` スコープ追加含む）
  - スレッド返信仕様（:eyes: リアクション付与の説明含む）
  - テスト/ lint 実行方法
  - OpenAI設定手順（OPENAI_API_KEY / gpt-5-nano / 予算上限）
  - MCP ツール自動ロード仕様（`MCP_SEMCHE_PATH` ディレクトリ必須 / `uv --directory <path> python src/semche/mcp_server.py` 起動 / timeout 正規化 / フォールバック無し / エラー一覧表記）
- src/slack_agent/handlers/message.py.exp.md
  - スレッド返信の実装仕様
  - :eyes: リアクション付与の仕様（`_try_add_eyes_reaction`）
  - エラーハンドリング（already_reacted/missing_scope/ratelimited）
  - clean_mention_text関数の利用箇所・仕様
- src/slack_agent/text.py.exp.md
  - clean_mention_text関数の仕様
  - 利用箇所一覧
- src/slack_agent/bot.py.exp.md / src/slack_agent/config.py.exp.md
  - ログ出力・スレッド返信仕様の関連
  - OpenAISettings の説明追記
- src/slack_agent/agent.py.exp.md
  - load_mcp_tools_once の仕様（非同期・メモ化・エラー仕様 / ディレクトリ必須 / サーバースクリプト存在チェック）
  - get_agent_graph の非同期化（ツール自動ロード統合）
  - MCP ツール自動ロードフロー（`uv --directory` による stdio 接続 / langchain_mcp_adapters 経由）
  - 失敗時のエラー仕様（RuntimeError・フォールバック無し / ツール 0 件 / アダプタ未導入 / パス不正 / スクリプト不存在）
  - invoke_agent の仕様
- AGENTS.md
  - Phase 4更新方針（この内容）
- story/\*.md
  - Phase4のチェック済み項目更新（exp/README/AGENTS）

### README 構成要件チェックリスト

README.md には以下を必ず含めること（変更時は網羅性を再確認）。

1. プロジェクト概要: Slack メンション → LangChain エージェント (gpt-5-nano) スレッド返信。
2. 前提環境: Python 3.12+ / Slack App / Socket Mode / 必須スコープ `app_mentions:read` `chat:write` `reactions:write`。
3. セットアップ: `uv sync` / `.env.example` コピーと必須環境変数記載例。
4. Slack App 設定手順: スコープ追加→再インストール手順を番号付きで記載。
5. 実行方法: `uv run slack-agent` と `uv run -m slack_agent.bot`。
6. OpenAI 説明: デフォルト `gpt-5-nano` / 予算上限は Usage limits で管理。
7. スレッド返信仕様: thread_ts 維持 / 新規スレッド開始条件 / `:eyes:` リアクション事前付与と失敗時継続ポリシー（already_reacted / missing_scope / ratelimited）。
8. Semche MCP 自動ロード: 目的（初回のみ接続・ツールキャッシュ）/ 環境変数テーブル (`MCP_SEMCHE_PATH` ディレクトリ必須, `MCP_SEMCHE_TIMEOUT`, `SEMCHE_CHROMA_DIR`) / 起動コマンド `uv run --directory <MCP_SEMCHE_PATH> python src/semche/mcp_server.py` / timeout 正規化 (`safe_timeout`) / メモ化 / フォールバック無し / エラー表（未設定・非ディレクトリ・スクリプト不存在・アダプタ未導入・初期化失敗・ツール0件） / stdioのみ対応。
9. 開発ツール（任意）: ruff / mypy 導入と実行コマンド例。
10. テスト / Lint / 型チェック実行方法: `uv run pytest` / `uv run ruff check . --fix` / `uv run mypy src`。
11. 参照: 詳細は `src/slack_agent/agent.py.exp.md` などへのリンク。

欠落項目がある場合は README 更新タスクを追加すること。

### ドキュメント反映方針

- すべてのexp.mdはコードファイルと同じパスに配置し、関数仕様・利用箇所・関連クラスファイルパスを明記する
- READMEは実行手順・Slack App設定・テスト/静的解析方法・スレッド返信仕様（:eyes: リアクション含む）・MCP ツール自動ロード仕様を日本語で記載する
- AGENTS.mdは各フェーズの更新方針を記録する
- storyは進捗状況（Phase4チェック）を反映する

---

## 開発者向けコマンド早見表（zsh）

日々の運用でコマンド入力ミスを防ぐため、開発者が頻用するコマンドをここに集約します。README と同一内容のうち、最低限の実行に必要なものだけを抜粋しています。

### セットアップ

```zsh
uv sync
```

### 実行

```zsh
uv run slack-agent
# または
uv run -m slack_agent.bot
```

### テスト（pytest）

```zsh
uv run pytest
```

### Lint（ruff）

```zsh
uv run ruff check . --fix
```

### 型チェック（mypy）

```zsh
uv run mypy src
```

必要に応じて README 側の詳細（MCP の設定やエラー仕様など）も参照してください。
