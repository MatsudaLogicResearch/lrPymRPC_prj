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

#from proto import file_service_pb2, file_service_pb2_grpc
from lrPymRPC.proto import file_service_pb2, file_service_pb2_grpc

__version__ = "0.1.1"

def upload(stub, tar_gz_path):
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

def execute(stub, unique_id, tool, command_opt):

    # コマンドを実行
    request = file_service_pb2.ExecuteRequest(unique_id=unique_id, tool=tool, command_opt=command_opt)
    response_iterator = stub.Execute(request)
    
    # 実行結果（リアルタイム）を受け取る
    for response in response_iterator:
        msg=response.message
        print(msg)
        #print(f"Success: {response.success}, Message: {response.message}")
        
    #print("Done: Execute")


def check(stub, unique_id, result_dir):
    #print("Check:")

    request = file_service_pb2.CheckRequest(unique_id=unique_id, result_dir=result_dir)
    response = stub.Check(request)
    
    return response.has_stream
 

def download(stub,unique_id, result_dir, result_gz):
    #print("Download:")

    # 実行結果をダウンロード
    request = file_service_pb2.DownloadRequest(unique_id=unique_id, result_dir=result_dir)

    # 実行結果（tar.gz）をダウンロード
    result = stub.Download(request)
    
    with open(result_gz, 'wb') as result_file:
        for chunk in result:
            result_file.write(chunk.data)

    print("Result downloaded and saved as result.tar.gz.")

        
def run(tool="git://github.com", target="help", server_ip="localhost", server_port="8765", source="source", result="build"):
    # gRPCチャンネルを作成
    #channel = grpc.insecure_channel('localhost:50052')
    #channel = grpc.insecure_channel('localhost:8765')

    ip_port=server_ip+":"+server_port
    channel = grpc.insecure_channel(ip_port)
    stub = file_service_pb2_grpc.FileServiceStub(channel)

    # ディレクトリをtar.gzに圧縮
    source_dir = source
    result_dir = result

    #source_gz  = source_dir + '.tar.gz'
    #result_gz  = result_dir + '.tar.gz'
    source_gz  = '_source.tar.gz'
    result_gz  = '_result.tar.gz'
    
    print("["+ip_port+"]:"+"Compress source=" + source_dir)

    #with tarfile.open(source_gz, 'w:gz') as tar:
    with tarfile.open(source_gz, 'w:gz', dereference=True) as tar:
        for f in source_dir.split(" "):
          #print(source_dir)
          #print(f)
          tar.add(f, arcname=os.path.basename(f))

        
    # データをアップロードしてIDを受け取る
    print("["+ip_port+"]:"+"Upload")
    unique_id = upload(stub, source_gz)
    
    print("["+ip_port+"]:"+"unique id="+unique_id)

    # コマンドを送信し、出力をリアルタイムで受け取る
    print("["+ip_port+"]:"+"pip install   ="+tool)
    print("["+ip_port+"]:"+"Execute target="+target)
    execute(stub, unique_id, tool, target)    

    # 実行結果の有無をチェック
    print("["+ip_port+"]:"+"Check result.")
    has_stream = check(stub, unique_id, result_dir)

    # 実行結果を受け取って展開する
    if has_stream:
      print("["+ip_port+"]:"+"Download data is exist.")
      download(stub, unique_id, result_dir, result_gz)
    
      # 実行結果を展開
      print("["+ip_port+"]:"+"Extract result.")
      with tarfile.open(result_gz, 'r:gz') as tar:
        tar.extractall()
    else:
      print("["+ip_port+"]:"+"Download data is not exist.")

    #-- remove tar.gz files
    for f in [source_gz, result_gz]:
      if os.path.isfile(f):
        print("["+ip_port+"]:"+"remove archive file="+f )
        os.remove(f)

    #-- Finish
    print("["+ip_port+"]:"+"Finish.")
    
def main():
    pars = argparse.ArgumentParser()
    pars.add_argument('-v',"--version"     ,action='version', version=f'%(prog)s {__version__}')
    pars.add_argument('--REPO_URL'    ,type=str ,default="charao=git+https://github.com/MatsudaLogicResearch/charao_prj.git@main"     ,help="repo mapping string(name=url,name=url,)")
    pars.add_argument('--CMD'         ,type=str ,default="charao -h"  ,help="command & parameters to module.")
    pars.add_argument('--SERVER_IP'   ,type=str ,default="127.0.0.1"  ,help="IP address of RPC server")
    pars.add_argument('--SERVER_PORT' ,type=str ,default="8766"       ,help="TCP port of RCP server")
    pars.add_argument('--SOURCE'      ,type=str ,default=["source"]     ,nargs="+" ,help="source direcrory used in make command.")
    pars.add_argument('--RESULT'      ,type=str ,default=["build"]      ,nargs="+" ,help="result direcrory output by make commnand.")
    
    args = pars.parse_args()
    
    run(tool       =args.REPO_URL, 
        target     =args.CMD,
        server_ip  =args.SERVER_IP, 
        server_port=args.SERVER_PORT, 
        source     =" ".join(args.SOURCE), 
        result     =" ".join(args.RESULT))
    
if __name__ == '__main__':
    main()
    
