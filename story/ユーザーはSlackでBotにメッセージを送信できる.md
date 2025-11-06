# ユーザーはSlackでBotにメッセージを送信できる

## 概要

ユーザーがSlackのチャンネルやダイレクトメッセージでBotにメンション付きメッセージを送信すると、Botがそのメッセージを受信し、応答を返す基本的な機能を実装します。これはSlack Botの最も基本的な機能となります。

## 実行手順

### Phase 1: 要件定義・設計【対話フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] ストーリーの内容を確認する
- [x] 実現方法を具体化をする
- [x] **実現方法の具体化内容についてユーザーから承認を得る**
- [x] 承認を得た内容をストーリーに反映する

#### 実現案

**スケルトン実装として、以下のシンプルな機能を実装します：**

- Botがメンションされた場合、`hello {受け取ったメッセージ}` を返すだけの基本機能

以下の実現方法を提案します：

1. **Slack SDK の選定**
   - Python用の公式Slack SDK（slack-bolt）を使用
   - Socket Modeを使用してWebSocketベースでイベントを受信（開発環境での動作を容易にするため）

2. **必要な実装コンポーネント**
   - Slack App設定（Bot Token, App Token）
   - イベントリスナーの実装（`app_mention` イベント）
   - メッセージ受信時の応答ロジック: `hello {受け取ったメッセージ}`
   - 設定ファイル（環境変数管理）

3. **技術スタック**
   - slack-bolt: Slack Bot開発用フレームワーク
   - python-dotenv: 環境変数管理
   - 設定情報: `.env`ファイルで管理（SLACK_BOT_TOKEN, SLACK_APP_TOKEN）

4. **実装の流れ**
   - Slack Appの設定（Slack APIポータル）
   - Bot Token, App Tokenの取得
   - Socket Modeの有効化
   - 必要なBot Token Scopesの設定（`app_mentions:read`, `chat:write`）
   - Pythonコードでのイベントハンドラー実装
   - 応答メッセージの実装: `hello {受け取ったメッセージ}` を返す

5. **ディレクトリ構成案**
   ```
   src/slack_agent/
   ├── bot.py          # Bot起動とイベントハンドラー
   ├── handlers/       # イベントハンドラー
   │   └── message.py  # app_mentionイベント処理
   └── config.py       # 設定管理
   ```

### Phase 2: 実装【実装フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] Slack Appの作成と設定（管理画面側での作業。App作成・Socket Mode有効化・スコープ追加・app_mention購読）
- [x] 必要な依存パッケージのインストール（slack-bolt, python-dotenv）
  - パッケージ管理は uv を使用（`uv sync` 済み）
- [x] 設定管理モジュールの実装（`config.py` 完了）
- [x] メッセージハンドラーの実装（`handlers/message.py` 完了）
- [x] Bot起動モジュールの実装（`bot.py` 完了）
- [x] 環境変数設定用の`.env.example`ファイル作成（完了）
- [x] Lint（ruff）/ 型チェック（mypy）導入・PASS（`uv run ruff check .` / `uv run mypy src`）
- [x] ログ基盤（basicConfig とイベント受信ログ）実装
      // レビュー: AIによるコードレビュー完了、ユーザー承認済み
- [x] `CODE_REVIEW_GUIDE.md` に準拠してコードレビューをする（AIレビュー & ユーザー承認済み）
- [x] **ユーザーからのコードレビューを受ける**

### Phase 3: テスト【テストフェーズ】(上から順にチェックしてください)

- [x] メッセージハンドラーのユニットテストを作成
- [x] 統合テスト（実際のSlack Workspaceでの動作確認）
  - 仕様: 返信はスレッドに送信（thread_ts=event.thread_ts or event.ts）。実環境で確認済み
- [x] テストが全てパスする（`uv run pytest -q` で 6 passed）

### Phase 4: ドキュメント化【ドキュメント更新フェーズ】(上から順にチェックしてください)

- [x] 実装内容（`*.exp.md`）を更新する
- [x] README.md に以下を追加
  - Slack Appの設定手順
  - 環境変数の設定方法
  - Botの起動方法
  - 使用方法（Slackでのメンション方法など）
- [x] AGENTS.md を更新する
