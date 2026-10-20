# CHANGELOG

このファイルは UTF-8 で記述されています。

---
## [0.5.0.a02] 2026-10-20
### 変更：要求オプションを REQ_* に統一（ISS-00337）

**BREAKING CHANGE（0.5.0.a01 からの変更）。** 0.4.x から見れば 0.5.0 全体が非互換なので、
正式版 0.5.0 の前にここで名前を揃えた。

| 0.5.0.a01 | 0.5.0.a02 |
|---|---|
| `--PIP_REQ` | **`--REQ_PIP`** |
| `--TOOL_REQ` | **`--REQ_TOOL`** |
| `--VM_REQ` | **`--REQ_VM`** |

- ファイル名（`req_pip.txt` / `req_tool.txt` / `req_vm.toml`）と並びが揃う
- **proto のフィールド名も揃えた**：`ResourceRequest.vm_info` → **`req_vm`**、
  `ExecuteRequest.pip_req` → **`req_pip`**（`req_tool` は変更なし）
- **usage の表示順を README と一致させた**（`add_argument` の呼び出し順を並べ替え）。
  接続系（`--SERVER_IP` / `--SERVER_PORT` / `--TLS_CONFIG_DIR`）→ 要求ファイル系
  （`--REQ_PIP` / `--REQ_TOOL` / `--REQ_VM`）→ `--SOURCE` 系 → `--RESULT` → `--CMD` →
  `--RUN_NAME` → `--KEEP_ARCHIVE`。**server 側も同じ思想で並べ替えた**
- Introduction の DATAFLOW 図を 0.5.0 の流れに書き直した
  （`RequestResource` の往復、`UploadResponse` での session_id、階層保持の明示）

### 修正：README のオプション名が実装と食い違っていた

`--QUEUE_TYPE` を `--VM_REQ` へ変更した際に README を直し忘れていた（0.5.0.a01 の漏れ）。
あわせて `req_vm.toml` のサンプルを README に載せた。

## [0.5.0.a01] 2026-10-19
### 変更：プロトコル刷新（RequestResource 追加、REPO_URL 廃止）（ISS-00337）

**BREAKING CHANGE: lrPymRPC_server 0.5.0 以上が必要。旧サーバとは通信できない。**

client が「要求」を出し、broker が要求に合うリソースを調達し、server は「実際の対応」を返す、
という流れに変えた。**broker が無くても（直結でも）動作する。** client/server 間と
client/broker/server 間は同じ proto を使う。

- **`RequestResource` を追加**（server streaming）。Upload の前に要求を出し、サーバの
  実際の対応（版数・python・ツール一覧・CPU/メモリ/ディスク・上限値）を受け取る。
  broker 介在時は `PROGRESS` でキュー状況や VM 起動の進捗が流れる
- **`--TOOL_REQ` を追加**（推奨ファイル名 `req_tool.txt`）。要求するツールとバージョンを
  pip requirements と同じ記法で書き、**中身を** `RequestResource` で送る。
  要求したツールがサーバの一覧に無ければ警告する（停止はしない）
- **`--QUEUE_TYPE` を追加**。broker に希望するキューを伝える（直結サーバは無視する）
- **`--REPO_URL` を削除**。pip パッケージは `--PIP_REQ` の requirements に一本化した
  （git URL もローカルパッケージもそこに書ける）。これに伴い install 後の import チェックも廃止
- **`--PIP_REQ` は据え置き**。推奨ファイル名を `requirements.txt` → **`req_pip.txt`** に変更。
  伝送は `ExecuteRequest.pip_req`（パス 1 本）になった
- **`session_id` は `<server_ip>/<work_id>`** の 1 つの文字列。`RequestResource` の時点では
  `<server_ip>` のみで、Upload 後に `/<work_id>` が付く
- サーバ版数の判定を `ServerSpec.server_version` に移した（起動バナーの正規表現読みを廃止）

### 変更：--SOURCE / --RESULT が階層を保持する（ISS-00197）

```
--SOURCE src1/src2/src3.txt  --RESULT rslt1/rslt2/rslt3.txt
  -> サーバ上で src1/src2/src3.txt に展開
  -> ローカルへ ./rslt1/rslt2/rslt3.txt として回収
```

従来は basename で潰れていたため、`--RESULT tmp/x` がエラーも出さずに `./x` へ落ちていた。
**トップレベル名のみの指定では tar の中身が変わらない**ので、既存の呼び出しは影響を受けない。
`--SOURCE` の「階層トップから渡す」運用ルールは不要になった。

### 修正：--SOURCE がカレントディレクトリの外を拾えた（ISS-00338）

`Path.is_relative_to()` は `..` を解決しないため、`--SOURCE ../secret` が素通りして
**カレント外のファイルが送信されていた**。`os.path.normpath` による検証を追加し、
絶対パス・`..`・`.` を**接続前に**拒否するようにした。

**シンボリックリンクは従来どおり通す。** リンク名が作業ディレクトリ配下なら、リンク先が外でもよい
（PDK ツリーを別の場所にマウントして転送する運用のため）。この判定に `Path.resolve()` は使わない。

### 修正：結果展開に filter が無かった（ISS-00339）

`tar.extractall()` に `filter='data'` を指定するようにした。サーバから `..` を含む tar が
返ってきても作業ディレクトリの外に書かれない。Python 3.9/3.10 向けにフォールバックを入れてある。

### 修正：console script が実在しないモジュールを指していた（ISS-00323）

`lrRPC-client` が `lrPymRPC.client:main` を指しており、pip install しても
`ModuleNotFoundError` になっていた。`lrPymRPC.script.client:main` へ修正した。
あわせて、console script は `python -u` を付けられないため、`main()` の冒頭で stdout を
行バッファリングに設定し、サーバ出力がリアルタイムに流れるようにした。

### 修正：proto 再生成スクリプトが壊れた import を生成していた（ISS-00340）

`compile_proto.sh` が `proto/` 内で実行する形だったため、生成される import が
`import file_service_pb2`（裸の import）になり、**生成後に手で書き換える必要があった**
（その手順はどこにも記録されていなかった）。リポジトリルートから proto のパスごと渡す形に変更し、
`from lrPymRPC.proto import file_service_pb2 as ...` が生成されるようにした。

## [0.3.2] 2026-08-27
### セッションの前提を README に明記（ドキュメントのみ）
- **run ごとにサーバ側の作業ディレクトリは新規**（`/tmp/lrpymrpc/<PORT>/<UUID>/`）で、
  セッション終了時に消える。前 run の中間生成物は残らないため、
  **多段ビルドは 1 つの `--CMD` にまとめる**必要がある
- **ビルドが成功しても `--RESULT` が合っていなければ何も回収されない**。
  手がかりは `Check: Download data is not exist.` の 1 行だけ。
  出力が `_build/` なのに `--RESULT build` を指定する取り違えが典型
- `--KEEP_ARCHIVE` を使えば、実際に何が返ってきたかを `_result.tar.gz` で確認できる

## [0.3.1] 2026-08-27
### add --KEEP_ARCHIVE option (ISS-00322)
- `--KEEP_ARCHIVE` を指定すると `_source.tar.gz` / `_result.tar.gz` を**実行後に削除しない**。
  不具合解析で「実際に何を送り、何を受け取ったか」を確認するため（既定は従来どおり削除）
- 保持したファイルはパスとサイズをログに出す（`Check: keep archive file=... (0.01 MB)`）。
  単位は MB 固定で、**最低表示は 0.01 MB**
- `--RUN_NAME` 併用時は `./<RUN_NAME>/` 配下のファイルが対象

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
