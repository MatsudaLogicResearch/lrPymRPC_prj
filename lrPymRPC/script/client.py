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
import os
import tarfile
import re
from pathlib import Path

#from proto import file_service_pb2, file_service_pb2_grpc
from lrPymRPC.proto import file_service_pb2, file_service_pb2_grpc

__version__ = "0.2.5"

def upload(stub, ip_port, tar_gz_path):
    # tar.gz ファイルをチャンクに分けてサーバーへ送信
    with open(tar_gz_path, 'rb') as f:
        # 送信するデータのチャンクを生成して送信
        response = stub.Upload(iter(chunk_file(f)))
    
    # UploadResponse から返されたIDを取得
    return response.unique_id
    

def chunk_file(file_obj, chunk_size=1*1024*1024):
    """ファイルオブジェクトを受け取ってチャンクごとにデータを返す"""
    #-- for python 3.8
    #while chunk := file_obj.read(chunk_size):
    #    yield file_service_pb2.DataChunk(data=chunk)
        
    while True:
      chunk = file_obj.read(chunk_size)
      if not chunk: # exit when chunk=empty
        break
      yield file_service_pb2.DataChunk(data=chunk)

def execute(stub, ip_port, unique_id, tool, command_opt):

    # コマンドを実行
    request = file_service_pb2.ExecuteRequest(unique_id=unique_id, tool=tool, command_opt=command_opt)
    response_iterator = stub.Execute(request)
    
    # 実行結果（リアルタイム）を受け取る
    for response in response_iterator:
        msg=response.message
        print(f"[{ip_port}]:{msg}")        
        #print(f"Success: {response.success}, Message: {response.message}")
        
    #print("Done: Execute")


def check(stub, ip_port, unique_id, result_dir):
    #print("Check:")

    request = file_service_pb2.CheckRequest(unique_id=unique_id, result_dir=result_dir)
    response = stub.Check(request)
    
    return response.has_stream
 

def download(stub, ip_port, unique_id, result_dir, result_gz):
    #print("Download:")

    # 実行結果をダウンロード
    request = file_service_pb2.DownloadRequest(unique_id=unique_id, result_dir=result_dir)

    # 実行結果（tar.gz）をダウンロード
    result = stub.Download(request)
    
    with open(result_gz, 'wb') as result_file:
        for chunk in result:
            result_file.write(chunk.data)

    msg="Result downloaded and saved as result.tar.gz."
    print(f"[{ip_port}]:{msg}")        

        
def run(tool="git://github.com", target="help", server_ip="localhost", server_port="8765", client_key=None, client_crt=None, ca_crt=None, source="source", result="build"):
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

    # ======== SOURCEファイル準備 ========
    # ディレクトリをtar.gzに圧縮
    source_dir = source
    result_dir = result

    source_gz  = '_source.tar.gz'
    result_gz  = '_result.tar.gz'
    
    msg=f"Compress source={source_dir}"
    print(f"[{ip_port}]:{msg}")        

    base_dir = (Path("./")).resolve()
    
    #with tarfile.open(source_gz, 'w:gz') as tar:
    with tarfile.open(source_gz, 'w:gz', dereference=True) as tar:
      for f in source_dir.split(" "):
        source_path = (base_dir / f).resolve()

        ## only current directory
        if not source_path.is_relative_to(base_dir):
          msg=f"Check: Not Exist in current directory, removed from source_dir={f}"
          print(f"[{ip_port}]:{msg}")
          continue
      
        ## check exist
        if not os.path.exists(source_path):
          msg=f"Check: Not Exist source_dir={f}"
          print(f"[{ip_port}]:{msg}")
          continue

        ## add files
        msg=f"Check: Exist source_dir={f}"
        print(f"[{ip_port}]:{msg}")
        tar.add(f, arcname=os.path.basename(f))
        
    # ======== UPLOAD処理 ========
    # データをアップロードしてIDを受け取る
    print(f"[{ip_port}]:Upload")
    
    unique_id = upload(stub, ip_port, source_gz)
    print(f"[{ip_port}]:Upload: unique id={unique_id}")

    # ======== CMD処理 ========
    # コマンドを送信し、出力をリアルタイムで受け取る
    print(f"[{ip_port}]:Upload: pip install   ={tool}")
    print(f"[{ip_port}]:Upload: Execute target={target}")
    execute(stub, ip_port, unique_id, tool, target)    

    # ======== RESULT受信処理 ========
    # 実行結果の有無をチェック
    print(f"[{ip_port}]:Check: result.")
    has_stream = check(stub, ip_port, unique_id, result_dir)

    # 実行結果を受け取って展開する
    if has_stream:
      print(f"[{ip_port}]:Check: Download data is exist.")
      download(stub, ip_port, unique_id, result_dir, result_gz)
    
      # 実行結果を展開
      print(f"[{ip_port}]:Check: Extract result.")
      with tarfile.open(result_gz, 'r:gz') as tar:
        tar.extractall()
    else:
      print(f"[{ip_port}]:Check: Download data is not exist.")

    #-- remove tar.gz files
    for f in [source_gz, result_gz]:
      if os.path.isfile(f):
        print(f"[{ip_port}]:Check: remove archive file={f}" )
        os.remove(f)

    #-- Finish
    print(f"[{ip_port}]:Finish: done.")
    
def main():
    pars = argparse.ArgumentParser()
    pars.add_argument('-v',"--version"     ,action='version', version=f'%(prog)s {__version__}')
    pars.add_argument('--REPO_URL'    ,type=str ,default=""     ,help="repo mapping string(name=url,name=url,)")
    pars.add_argument('--CMD'         ,type=str ,default="charao -h"  ,help="command & parameters to module.")
    pars.add_argument('--SERVER_IP'   ,type=str ,default="127.0.0.1"  ,help="IP address of RPC server")
    pars.add_argument('--SERVER_PORT' ,type=str ,default="8766"       ,help="TCP port of RPC server")
    pars.add_argument('--SOURCE'      ,type=str ,default=["source"]     ,nargs="+" ,help="source directory used in make command.")
    pars.add_argument('--RESULT'      ,type=str ,default=["build"]      ,nargs="+" ,help="result directory output by make command.")
    pars.add_argument('--TLS_CONFIG_DIR'    ,default=""  ,help="TLS configuration directory. if empty, Connection not use TLS.")
    
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

    # RESULT の処理
    result = " ".join(str(x) for x in args.RESULT)
    result = re.sub(r'\s+', ' ', result).strip()
    if not result:
      result = ""
    
    #
    run(tool       =args.REPO_URL, 
        target     =args.CMD,
        server_ip  =args.SERVER_IP, 
        server_port=args.SERVER_PORT,
        client_key =client_key,
        client_crt =client_crt,
        ca_crt     =ca_crt,
        source     =source, 
        result     =result)
    
if __name__ == '__main__':
    main()
    
