# エージェントは回答する前に「:eyes:」で質問メッセージにリアクションする

## 概要

SlackでBotがユーザーからのメンション（またはDM）メッセージを受け取ったら、応答を生成・送信する前に、その「元メッセージ」に :eyes: リアクションを付与して「対応中」であることを明示します。UX向上（待機の見える化）と、失敗時に本処理全体を阻害しない堅牢性を両立します。

## 実行手順

**必須**: フェーズ内のすべてのタスクにチェックがつくまで、次のフェーズに進まないでください。

### Phase 1: 要件定義・設計【対話フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] ストーリーの内容を確認する
- [x] 実現方法を具体化をする
- [x] **実現方法の具体化内容についてユーザーから承認を得る**
- [x] 承認を得た内容をストーリーに反映する

#### 実現案

- 目的: 応答生成に着手したことを即時に可視化するため、対象メッセージに :eyes: を付与する。
- 対象: `app_mention` / DM の受信イベントで、Botが返信対象と判定したメッセージ（=イベントの `ts`）。
- 付与タイミング: エージェント呼び出し・応答生成の「直前」。重い処理の前に行う。
- 実装ポイント:
  1. Slack権限: Slack App の Bot Token Scopes に `reactions:write` を追加（既存の `app_mentions:read`, `chat:write` などは維持）。
  2. ハンドラー: `src/slack_agent/handlers/message.py` のメンション受信処理で、`event['channel']` と `event['ts']` を使い `reactions.add` を実行。
  3. 安全性:
     - エラーは握りつぶさずログ警告に留め、応答処理は継続（`missing_scope`, `already_reacted`, `ratelimited` 等を個別に扱う）。
     - 既に :eyes: が付いている場合（`already_reacted`）は成功相当として無視。
     - 例外はSlack SDKの `SlackApiError` を捕捉し、重要度に応じて `warning`/`info` ログを出す。
  4. 付与対象の選択:
     - スレッド中のメッセージであっても「イベントの `ts`（ユーザーが送ったそのメッセージ）」にリアクションを付与する。
     - 返信は既存仕様どおりスレッドに送信（`thread_ts = event.get('thread_ts', event['ts'])`）。
  5. 冪等性: 同一イベントに対して多重呼び出しされても機能的に問題にならない（`already_reacted` を無視）。

- 受け入れ条件:
  - Botがユーザーメッセージを受け取ると、応答送信前にそのメッセージへ :eyes: が付く。
  - `reactions:write` が無い/レート制限/既に付与済みでも、応答の生成と送信は継続する。
  - Lint（ruff）/ 型チェック（mypy）/ テスト（pytest）が通る。

### Phase 2: 実装【実装フェーズ - ユーザー確認必須】(上から順にチェックしてください)

- [x] Slack Appに `reactions:write` スコープを追加し、再インストール（管理画面側の作業）
- [x] `handlers/message.py` にリアクション付与処理を追加（`reactions.add` 呼び出し）
- [x] エラーハンドリング（`SlackApiError` の `response['error']` に応じて `already_reacted`/`missing_scope`/`ratelimited` を考慮）
- [x] ログ出力の整備（成功/失敗、失敗時の要約メッセージ）
- [x] Lint（ruff check . --fix）/ 型チェック（mypy）が通る
- [x] `CODE_REVIEW_GUIDE.md` に準拠してコードレビューをする
  - AIエージェントが行うので、PRの作成は不要です
- [x] **ユーザーからのコードレビューを受ける**

### Phase 3: テスト【テストフェーズ】(上から順にチェックしてください)

- [x] ユニットテスト: `handlers/message.py` で `reactions.add` が呼ばれることをモックで検証
- [x] エラー分岐テスト: `already_reacted`/`missing_scope`/`ratelimited` の各ケースで処理継続すること
- [ ] 統合テスト（実Slack環境）: メンション/DM/スレッド内返信でも :eyes: が付与されることを確認
- [x] テストが全てパスする

### Phase 4: ドキュメント化【ドキュメント更新フェーズ】(上から順にチェックしてください)

- [x] README.md を更新（Slack権限 `reactions:write` の追加手順、スレッド返信仕様との関係）
- [x] `src/slack_agent/handlers/message.py.exp.md` を更新（リアクション付与の処理位置・例外扱い）
- [x] `src/slack_agent/bot.py.exp.md` / `src/slack_agent/config.py.exp.md` を必要に応じて追記（ログ/設定まわり）
- [x] AGENTS.md を更新（Phase 4 追記方針に基づく進捗反映）

### Phase 5: コミット・プッシュ【最終フェーズ】(上から順にチェックしてください)

- [ ] コードのコミットメッセージを作成する
- [ ] **ユーザーからコミットメッセージの承認を受ける**
- [ ] コミット・プッシュする
