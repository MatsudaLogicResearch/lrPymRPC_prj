# coding: utf-8
###############################################################################
# This file is part of lrPymRPC project.
# Copyright (C) 2025 LogicResearch K.K (Author: MATSUDA Masahiro)
# 
# This script file is licensed under the MIT License.
###############################################################################
#pip3 install --upgrade pip
#python3 -m pip install grpcio grpcio-tools

import argparse
import grpc
import sys
import os
import tarfile
import re
from pathlib import Path

#from proto import file_service_pb2, file_service_pb2_grpc
from lrPymRPC.proto import file_service_pb2, file_service_pb2_grpc

__version__ = "0.5.0.a02"

#-- req_tool.txt の 1 行からツール名だけを取り出す（pip requirements と同じ記法）
_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9._-]+)")


def _req_tool_names(req_tool):
    """req_tool.txt の中身から要求ツール名の一覧を返す。`#` コメントと空行は無視する。"""
    names = []
    for line in (req_tool or "").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        m = _REQ_NAME_RE.match(line)
        if m:
            names.append(m.group(1))
    return names


def _read_req_file(path, opt_name, ip_port):
    """要求ファイル（--REQ_TOOL / --REQ_VM）を読んで中身を返す。未指定なら空文字列。

    中身をそのまま RequestResource で送るだけで、client はパースしない
    （解釈するのは broker。client に TOML パーサ等の依存を増やさないため）。
    指定したのにファイルが無ければ、接続前に読めるエラーで止める。
    """
    if not path:
        return ""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"{opt_name} file not found: {path}")
    text = p.read_text(encoding="utf-8")
    print(f"[{ip_port}]:{opt_name.lstrip('-')}: {path} ({len(text)} bytes)")
    return text


def request_resource(stub, ip_port, req_tool="", req_vm=""):
    """リソース要求を出し、サーバの「実際の対応」を受け取る（0.5.0）。

    req_tool はツール要求（req_tool.txt の中身）、req_vm は VM 要求（req_vm.toml の中身。
    キュー種別も含む）。**どちらも直結サーバは無視する**。broker が VM 選定に使う。

    broker 介在時は PROGRESS が何本でも流れる（キュー状況・VM 起動の進捗など）。
    直結サーバは PROGRESS を送らず READY を 1 本返して終わる。
    戻り値の session_id はこの時点では <server_ip> のみ（work_id は Upload で付く）。
    """
    request = file_service_pb2.ResourceRequest(req_tool=req_tool, req_vm=req_vm)

    session_id = ""
    spec = None
    for response in stub.RequestResource(request):
        if response.stage == file_service_pb2.ResourceResponse.PROGRESS:
            q = ""
            if response.queue_total:
                q = f" [{response.queue_type or 'queue'} {response.queue_position}/{response.queue_total}"
                q += f", eta {response.eta_sec}s]" if response.eta_sec else "]"
            print(f"[{ip_port}]:Resource: {response.message}{q}")
            continue

        #-- READY
        session_id = response.session_id
        spec = response.spec
        if response.message:
            print(f"[{ip_port}]:Resource: {response.message}")

    if not session_id:
        raise RuntimeError("server did not return a session_id (no READY response).")

    #-- サーバの実際の対応をログに出す（値が無い項目は出さない）
    print(f"[{ip_port}]:Resource: session_id={session_id}")
    if spec.server_version:
        print(f"[{ip_port}]:Resource: server={spec.server_version} python={spec.python_version}")
    if spec.tool:
        tools = ", ".join(f"{t.name}{'=' + t.version if t.version else ''}" for t in spec.tool)
        print(f"[{ip_port}]:Resource: tool={tools}")
    if spec.cpu_count or spec.mem_total_mb or spec.disk_free_mb:
        print(f"[{ip_port}]:Resource: cpu={spec.cpu_count} mem_total={spec.mem_total_mb}MB "
              f"mem_avail={spec.mem_available_mb}MB disk_free={spec.disk_free_mb}MB")
    if spec.max_upload_mb or spec.session_ttl_sec:
        print(f"[{ip_port}]:Resource: max_upload={spec.max_upload_mb}MB ttl={spec.session_ttl_sec}s")

    #-- 要求したツールがサーバ側に無ければ警告する（名前の有無のみ。バージョンは比較しない）。
    #   broker 経由なら broker が調達を保証するので、ここでは停止せず警告に留める。
    if req_tool and spec.tool:
        have = {t.name for t in spec.tool}
        missing = [n for n in _req_tool_names(req_tool) if n not in have]
        if missing:
            print(f"[{ip_port}]:Resource: WARN: not in server tool list: {', '.join(missing)}")

    return session_id, spec


def upload(stub, ip_port, session_id, tar_gz_path):
    # tar.gz ファイルをチャンクに分けてサーバーへ送信
    with open(tar_gz_path, 'rb') as f:
        response = stub.Upload(chunk_file(f, session_id))

    # UploadResponse から返された session_id（<server_ip>/<work_id>）を取得
    return response.session_id


def chunk_file(file_obj, session_id, chunk_size=1*1024*1024):
    """ファイルをチャンクに分けて送る。session_id は最初のチャンクのみ設定する。"""
    first = True
    while True:
      chunk = file_obj.read(chunk_size)
      if not chunk: # exit when chunk=empty
        if first:   # 空ファイルでも session_id だけは送る
          yield file_service_pb2.UploadRequest(session_id=session_id, data=b"")
        break
      yield file_service_pb2.UploadRequest(
          session_id=session_id if first else "", data=chunk)
      first = False


def execute(stub, ip_port, session_id, command_opt, req_pip=""):

    # コマンドを実行
    request = file_service_pb2.ExecuteRequest(
        session_id=session_id, command_opt=command_opt, req_pip=req_pip)
    response_iterator = stub.Execute(request)

    # 実行結果（リアルタイム）を受け取る
    for response in response_iterator:
        print(f"[{ip_port}]:{response.message}")


def check(stub, ip_port, session_id, result_dir):
    #print("Check:")

    request = file_service_pb2.CheckRequest(session_id=session_id, result_dir=result_dir)
    response = stub.Check(request)

    return response.has_stream


def download(stub, ip_port, session_id, result_dir, result_gz):
    #print("Download:")

    # 実行結果をダウンロード
    request = file_service_pb2.DownloadRequest(session_id=session_id, result_dir=result_dir)

    # 実行結果（tar.gz）をダウンロード
    result = stub.Download(request)
    
    with open(result_gz, 'wb') as result_file:
        for chunk in result:
            result_file.write(chunk.data)

    msg="Result downloaded and saved as result.tar.gz."
    print(f"[{ip_port}]:{msg}")        

        
def _validate_path(token, opt_name):
    """--SOURCE / --RESULT の 1 トークンを検証し、正規化した相対パスを返す（ISS-00197 / ISS-00338）。

    作業ディレクトリ以下のみ許可する。他のディレクトリのファイル・ディレクトリは禁止。
    **シンボリックリンクは通す**（リンク名が作業ディレクトリ配下なら、リンク先が外でもよい）。
    charao_prj の `sample_src/<pdk>` が NFS 上の PDK を指す symlink で、それを転送するのが
    実運用のため。`dereference=True` で実体が tar に入る。

    判定は os.path.normpath による**文字列処理のみ**で行う。Path.resolve() は symlink を
    辿ってしまい、上記の symlink 指定を弾いてしまうので使わない。
    """
    norm = os.path.normpath(token)
    if os.path.isabs(norm):
        raise ValueError(f"{opt_name} must be a relative path under the current directory: {token!r}")
    if norm == ".." or norm.startswith(".." + os.sep):
        raise ValueError(f"{opt_name} must not escape the current directory: {token!r}")
    if norm == ".":
        raise ValueError(f"{opt_name} must not be '.': {token!r}")
    return norm


def _validate_paths(spec, opt_name):
    """空白区切りの --SOURCE / --RESULT を**トークン単位**で検証し、正規化して組み直す。

    `--SOURCE "Makefile source"` のように 1 要素へ空白区切りで複数渡す書き方が実在するため、
    argparse の要素単位ではなく空白で割ってから検証する。
    """
    return " ".join(_validate_path(t, opt_name) for t in spec.split(" ") if t)


def _validate_run_name(run_name):
    """--RUN_NAME の検証。空文字列はOK（後方互換）。指定時は 1 階層のディレクトリ名のみ許可。"""
    if not run_name:
        return ""
    if "/" in run_name or "\\" in run_name:
        raise ValueError(f"--RUN_NAME must be a single directory name (no slashes): {run_name!r}")
    if run_name in (".", ".."):
        raise ValueError(f"--RUN_NAME cannot be '.' or '..': {run_name!r}")
    return run_name


def _convert_req_pip(req_pip, source):
    """
    --REQ_PIP のローカルパスを、サーバ側（作業ディレクトリ起点）の相対パスへ変換する（ISS-00319）。

    0.5.0 で --SOURCE が**階層を保持して**転送されるようになったため（ISS-00197）、
    変換は「作業ディレクトリ起点の相対パスへ正規化する」だけになった。
    | --SOURCE work/pip_pkg + --REQ_PIP ./work/pip_pkg/req_pip.txt -> work/pip_pkg/req_pip.txt |
    （0.4.x までは basename 起点で `pip_pkg/req_pip.txt` になっていた）

    --SOURCE 配下に無いパスを指定した場合は、転送されないまま実行されるのを防ぐため
    ValueError を raise する（[[ISS-00197]] と同じ「静かに迷子にならない」方針）。
    """
    if not req_pip:
        return ""

    #-- 作業ディレクトリ以下であることを文字列で検証して正規化する
    #   （symlink を辿らないよう resolve() は使わない。_validate_path と同じ方針）
    req_rel = _validate_path(req_pip, "--REQ_PIP")

    if not (Path("./") / req_rel).is_file():
        raise ValueError(f"--REQ_PIP file not found: {req_pip}")

    #-- --SOURCE のいずれかの配下にあることを確認する（source は検証・正規化済み）
    for f in source.split(" "):
        if not f:
            continue
        if req_rel == f or req_rel.startswith(f + os.sep):
            return Path(req_rel).as_posix()

    raise ValueError(
        f"--REQ_PIP must be located under --SOURCE (so that it is transferred): "
        f"req_pip={req_pip!r}, source={source!r}")


def _make_tar_filter(include_exts, exclude_exts, match_patterns=None):
    """tarfile フィルター生成。--SOURCE_INCLUDE / --SOURCE_EXCLUDE / --SOURCE_MATCH に対応。"""
    def _filter(tarinfo):
        if tarinfo.isdir():
            return tarinfo  # ディレクトリは常に通す（再帰探索のため）
        if include_exts and not any(tarinfo.name.endswith(e) for e in include_exts):
            return None     # --SOURCE_INCLUDE 指定時：一致しないファイルは除外
        if exclude_exts and any(tarinfo.name.endswith(e) for e in exclude_exts):
            return None     # --SOURCE_EXCLUDE 指定時：一致するファイルは除外
        if match_patterns and not any(p in tarinfo.name for p in match_patterns):
            return None     # --SOURCE_MATCH 指定時：パスにいずれも含まれないファイルは除外
        return tarinfo
    return _filter


def run(target="help", server_ip="localhost", server_port="8765", client_key=None, client_crt=None, ca_crt=None, source="source", result="build", source_include=None, source_exclude=None, source_match=None, run_name="", req_pip="", req_tool="", req_vm="", keep_archive=False):
    # gRPCチャンネルを作成
    #channel = grpc.insecure_channel('localhost:50052')
    #channel = grpc.insecure_channel('localhost:8765')

    #print("client_key:", type(client_key), client_key is None)
    #print("client_crt:", type(client_crt), client_crt is None)
    #print("ca_crt    :", type(ca_crt), ca_crt is None)

    # ======== 認証処理 ========
    ip_port=server_ip+":"+server_port
    
    if client_key:
      creds = grpc.ssl_channel_credentials(
          root_certificates=ca_crt,
          private_key=client_key,
          certificate_chain=client_crt,
      )
      
      channel = grpc.secure_channel(ip_port, creds)
      
    else:
      channel = grpc.insecure_channel(ip_port)
      

    #--
    stub = file_service_pb2_grpc.FileServiceStub(channel)

    # ======== --REQ_PIP のパス変換 ========
    # ローカル表記のパスを、サーバ側（作業ディレクトリ起点）の相対パスへ変換する（ISS-00319）。
    # 実体は tar で届くので、--SOURCE 配下であることをここで検証して停止する。
    req_pip_remote = ""
    if req_pip:
        req_pip_remote = _convert_req_pip(req_pip, source)
        msg=f"REQ_PIP: {req_pip} -> {req_pip_remote}"
        print(f"[{ip_port}]:{msg}")

    # ======== --REQ_TOOL / --REQ_VM の読み込み ========
    # 要求はファイルの「中身」を RequestResource で送る（tar には乗せない）。
    # Upload より前に要求を出す必要があるため。未指定なら送るデータは無い。
    req_tool_text = _read_req_file(req_tool, "--REQ_TOOL", ip_port)
    req_vm_text   = _read_req_file(req_vm,   "--REQ_VM",   ip_port)

    # ======== リソース要求（0.5.0）========
    # client が要求を出し、server が「実際の対応」を返す。
    # broker 介在時は VM が用意できるまで PROGRESS が流れる。
    print(f"[{ip_port}]:Resource: request")
    session_id, _spec = request_resource(stub, ip_port,
                                         req_tool=req_tool_text, req_vm=req_vm_text)

    # ======== SOURCEファイル準備 ========
    # ディレクトリをtar.gzに圧縮
    source_dir = source
    result_dir = result

    # --RUN_NAME 指定時は ./<run_name>/ 配下にまとめる（並列実行用）
    if run_name:
        Path(run_name).mkdir(parents=True, exist_ok=True)
        source_gz = f"{run_name}/_source.tar.gz"
        result_gz = f"{run_name}/_result.tar.gz"
    else:
        source_gz = '_source.tar.gz'
        result_gz = '_result.tar.gz'

    msg=f"Compress source={source_dir}"
    print(f"[{ip_port}]:{msg}")

    base_dir = (Path("./")).resolve()
    
    tar_filter = _make_tar_filter(source_include or [], source_exclude or [], source_match or [])

    with tarfile.open(source_gz, 'w:gz', dereference=True) as tar:
      # source_dir は _validate_paths() で検証・正規化済み（作業ディレクトリ以下のみ）。
      # arcname に正規化後の相対パスを使うので **階層が保持される**（ISS-00197）。
      for f in source_dir.split(" "):
        source_path = (base_dir / f)

        ## check exist
        if not os.path.exists(source_path):
          msg=f"Check: Not Exist source_dir={f}"
          print(f"[{ip_port}]:{msg}")
          continue

        ## add files
        msg=f"Check: Exist source_dir={f}"
        print(f"[{ip_port}]:{msg}")
        tar.add(f, arcname=f, filter=tar_filter)
        
    # ======== UPLOAD処理 ========
    # データをアップロードする。session_id に work_id が付いて返る
    # （<server_ip> → <server_ip>/<work_id>）
    print(f"[{ip_port}]:Upload")

    session_id = upload(stub, ip_port, session_id, source_gz)
    print(f"[{ip_port}]:Upload: session_id={session_id}")

    # ======== CMD処理 ========
    # コマンドを送信し、出力をリアルタイムで受け取る
    if req_pip_remote:
      print(f"[{ip_port}]:Upload: pip install -r={req_pip_remote}")
    print(f"[{ip_port}]:Upload: Execute target={target}")
    execute(stub, ip_port, session_id, target, req_pip=req_pip_remote)

    # ======== RESULT受信処理 ========
    # 実行結果の有無をチェック
    print(f"[{ip_port}]:Check: result.")
    has_stream = check(stub, ip_port, session_id, result_dir)

    # 実行結果を受け取って展開する
    if has_stream:
      print(f"[{ip_port}]:Check: Download data is exist.")
      download(stub, ip_port, session_id, result_dir, result_gz)
    
      # 実行結果を展開
      # filter='data' で、作業ディレクトリの外を指すメンバー（絶対パス・`..`・外部 symlink）を
      # 拒否する（ISS-00339）。Python 3.9/3.10 には filter 引数が無いのでフォールバックする。
      print(f"[{ip_port}]:Check: Extract result.")
      extract_to = run_name if run_name else '.'
      with tarfile.open(result_gz, 'r:gz') as tar:
        try:
          tar.extractall(path=extract_to, filter='data')
        except TypeError:
          tar.extractall(path=extract_to)
    else:
      print(f"[{ip_port}]:Check: Download data is not exist.")

    #-- tar.gz の後始末。--KEEP_ARCHIVE 指定時は残す（不具合解析用, ISS-00322）
    for f in [source_gz, result_gz]:
      if not os.path.isfile(f):
        continue
      if keep_archive:
        # 単位は MB 固定。1 KB 未満でも 0.00 MB とは出さず、最低 0.01 MB と表示する
        size_mb = max(0.01, os.path.getsize(f) / 1024 / 1024)
        print(f"[{ip_port}]:Check: keep archive file={f} ({size_mb:.2f} MB)")
      else:
        print(f"[{ip_port}]:Check: remove archive file={f}" )
        os.remove(f)

    #-- Finish
    print(f"[{ip_port}]:Finish: done.")
    
def main():
    # console script（lrRPC-client）経由では `python -u` を付けられないため、stdout を
    # 行バッファリングにしてサーバ出力をリアルタイムに流す（ISS-00323）。
    # `python -u -m lrPymRPC` 経由では既に unbuffered なので無害。
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    pars = argparse.ArgumentParser()
    pars.add_argument('-v',"--version"     ,action='version', version=f'%(prog)s {__version__}')
    pars.add_argument('--SERVER_IP'   ,type=str ,default="127.0.0.1"  ,help="IP address of RPC server")
    pars.add_argument('--SERVER_PORT' ,type=str ,default="8766"       ,help="TCP port of RPC server")
    pars.add_argument('--TLS_CONFIG_DIR'    ,default=""  ,help="TLS configuration directory. if empty, Connection not use TLS.")
    pars.add_argument('--REQ_PIP'        ,type=str ,default=""                  ,help="requirements file for 'pip install -r' on the server (recommended name: req_pip.txt). Must be located under --SOURCE. Empty=not sent.")
    pars.add_argument('--REQ_TOOL'       ,type=str ,default=""                  ,help="requirements-style file listing required tools, e.g. 'ngspice>=41' (recommended name: req_tool.txt). Its content is sent with the resource request. Empty=not sent.")
    pars.add_argument('--REQ_VM'         ,type=str ,default=""                  ,help="TOML file describing the VM resources you need, incl. the preferred queue (recommended name: req_vm.toml). Its content is sent with the resource request and used by a broker; a direct server ignores it. Empty=not sent.")
    pars.add_argument('--SOURCE'         ,type=str ,default=["source"] ,nargs="+" ,help="source directory used in make command.")
    pars.add_argument('--SOURCE_INCLUDE' ,type=str ,default=[]         ,nargs="*" ,help="Include only files with these extensions in SOURCE (e.g. .cdl .sp). Empty=all files.")
    pars.add_argument('--SOURCE_EXCLUDE' ,type=str ,default=[]         ,nargs="*" ,help="Exclude files with these extensions from SOURCE (e.g. .gds .gds2).")
    pars.add_argument('--SOURCE_MATCH'   ,type=str ,default=[]         ,nargs="+" ,help="Include only files whose path contains any of these strings (e.g. gf180mcuC). Empty=all files.")
    pars.add_argument('--RESULT'         ,type=str ,default=["build"]  ,nargs="+" ,help="result directory output by make command.")
    pars.add_argument('--CMD'         ,type=str ,default="charao -h"  ,help="command & parameters to module.")
    pars.add_argument('--RUN_NAME'       ,type=str ,default=""                  ,help="Isolate this run under ./<RUN_NAME>/ (single dir name, no slashes). Empty=current dir (backward compatible). For parallel execution.")
    pars.add_argument('--KEEP_ARCHIVE'   ,action="store_true"                    ,help="keep _source.tar.gz / _result.tar.gz after the run (default: remove). For debugging what was actually sent and received.")
    args = pars.parse_args()

    # TLS setting
    client_key = None
    client_crt = None
    ca_crt     = None
    
    if args.TLS_CONFIG_DIR:
      clkey=(Path(args.TLS_CONFIG_DIR).expanduser() / "client" / "client.key").resolve()
      clcrt=(Path(args.TLS_CONFIG_DIR).expanduser() / "client" / "client.crt").resolve()
      cacrt=(Path(args.TLS_CONFIG_DIR).expanduser() / "ca" / "ca.crt").resolve()
      
      if not os.path.exists(clkey):
        msg=f"ERROR: {clkey} file is not exist."
        print(msg)
        return
      else:
        with open(clkey, "rb") as f:
          client_key = f.read()
          
      if not os.path.exists(clcrt):
        msg=f"ERROR: {clcrt} file is not exist."
        print(msg)
        return
      else:
        with open(clcrt, "rb") as f:
          client_crt = f.read()
      
      if not os.path.exists(cacrt):
        msg=f"ERROR: {cacrt} file is not exist."
        print(msg)
        return
      else:
        with open(cacrt, "rb") as f:
          ca_crt = f.read()

    # SOURCE の処理
    source = " ".join(str(x) for x in args.SOURCE)  # まず全て結合して文字列化
    source = re.sub(r'\s+', ' ', source).strip()    # 連続空白を1つにまとめて前後空白を削除
    if not source:                                   # 空文字列なら ""
       source = ""

    source_include = args.SOURCE_INCLUDE
    source_exclude = args.SOURCE_EXCLUDE
    source_match   = args.SOURCE_MATCH

    # RESULT の処理
    result = " ".join(str(x) for x in args.RESULT)
    result = re.sub(r'\s+', ' ', result).strip()
    if not result:
      result = ""

    #
    # 引数の指定ミス（--RUN_NAME の書式、--SOURCE / --RESULT が作業ディレクトリの外、
    # --REQ_PIP が SOURCE 外・不在、--REQ_TOOL / --REQ_VM のファイル不在）は、読める 1 行の
    # エラーで止める（トレースバックを出さない。TLS ファイル不在時の表示スタイルに合わせる）
    try:
      # RUN_NAME の検証（空文字列はOK、それ以外は 1 階層のディレクトリ名のみ許可）
      run_name = _validate_run_name(args.RUN_NAME)

      # SOURCE / RESULT の検証と正規化（作業ディレクトリ以下のみ、ISS-00197 / ISS-00338）。
      # 空白区切りのトークン単位で見る（`--SOURCE "Makefile source"` の形が実在するため）。
      if source:
        source = _validate_paths(source, "--SOURCE")
      if result:
        result = _validate_paths(result, "--RESULT")

      run(target         =args.CMD,
          server_ip      =args.SERVER_IP,
          server_port    =args.SERVER_PORT,
          client_key     =client_key,
          client_crt     =client_crt,
          ca_crt         =ca_crt,
          source         =source,
          result         =result,
          source_include =source_include,
          source_exclude =source_exclude,
          source_match   =source_match,
          run_name       =run_name,
          req_pip        =args.REQ_PIP,
          req_tool       =args.REQ_TOOL,
          req_vm         =args.REQ_VM,
          keep_archive   =args.KEEP_ARCHIVE)
    except (ValueError, RuntimeError) as e:
      print(f"ERROR: {e}")
      sys.exit(1)
    
if __name__ == '__main__':
    main()
    
