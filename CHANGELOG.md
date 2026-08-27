# CHANGELOG

このファイルは UTF-8 で記述されています。

---
## [0.3.0] 2026-08-27
### --PIP_REQ 対応（0.3.0.a01〜a02 の内容を正式版として確定）
- `--PIP_REQ`：サーバ側で `pip install -r <requirements>` を実行する（ISS-00319）
- サーバ側制限（Upload サイズ・セッション TTL）を README に明記
- **必要なサーバ**：`lrPymRPC_server` 0.4.0 以上

## [0.3.0.a02] 2026-08-27
### document server-side limits (upload size / session TTL)
- README に「Server-side limits you may hit」を追加
- クライアントからは事前に問い合わせられないこと、上限値はエラーメッセージに含まれること、
  上限に当たった場合は `--SOURCE_INCLUDE` / `--SOURCE_EXCLUDE` / `--SOURCE_MATCH` で削ること
- セッション TTL（サーバ既定 1 時間）と、**実行中の RPC がある間は回収されない**ことを明記

## [0.3.0.a01] 2026-08-27
### add --PIP_REQ option: run "pip install -r <requirements>" on the server (ISS-00319)
- `--PIP_REQ <path>` を追加。`--REPO_URL` とは独立した引数で、**片方だけ／両方省略でも動作する**（単数指定）
- ローカルパスを `--SOURCE` の basename 展開に合わせて変換し、変換結果をログに出す
  （`PIP_REQ: ./pip_pkg/requirements.txt -> pip_pkg/requirements.txt`）。
  **`--SOURCE` 配下に無い／存在しないファイルは、サーバへ接続する前にエラーで停止**する（[[ISS-00197]] と同じ
  「静かに迷子になる」状態を作らないため）
- サーバへは既存の `tool` チャネルで送る（**proto は変更しない**）。requirements は **module 名が空の項目**
  （`=<requirement path>`）として表現し、サーバ側が `pip install -r` を付ける
- サーバが返す `[lrPymRPC_server vX.Y.Z] Execute start` からバージョンを読み、**`--PIP_REQ` 指定時に
  サーバが 0.4.0 未満ならエラーで停止**する（`--PIP_REQ` 未使用なら旧サーバでも従来どおり動作）
- `--PIP_REQ` 関連のエラーはトレースバックではなく `ERROR: <message>` の 1 行で表示し、終了コード 1 で終わる
- README に `--PIP_REQ` の章を追加（パス変換規則、requirements 内の相対パスの解決基準、必要なサーバ版数）

**必要なサーバ**：`lrPymRPC_server` 0.4.0 以上

## [0.2.9] 2026-05-15
### add --RUN_NAME option to isolate each run under ./<RUN_NAME>/ for parallel execution (empty=backward compatible). Fix tar.extractall(path=None) TypeError on Python 3.10.

## [0.2.8] 2026-04-11
### add --SOURCE_MATCH option: filter SOURCE files by path substring (OR condition, multiple values allowed).

## [0.2.7] 2026-03-xx
### add --SOURCE_INCLUDE / --SOURCE_EXCLUDE options.

## [0.2.6] 2026-02-02
### archive symbolic-link file.

## [0.2.5] 2026-01-21
### support on-TLS

## [0.2.4] 2026-01-16
### update message.

## [0.2.3] 2026-01-16
### README: update

## [0.2.1] 2026-01-15
### modified args.SOURCE/args.RESULT.

## [0.2.0] 2026-01-15
### support TLS.

## [0.1.1] 2026-01-14
### change message for param(REPO_URL)

## [0.1.0] 2026-01-10
### First Commit
