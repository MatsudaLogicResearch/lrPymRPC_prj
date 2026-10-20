#===================================================================
# This file is part of lrPymRPC project.
# Copyright (C) 2025 LogicResearch K.K (Author: MATSUDA Masahiro)
#
# This script file is licensed under the MIT License.
#===================================================================
# リポジトリルートから実行すること（ISS-00340）。
#
#   bash lrPymRPC/proto/compile_proto.sh
#
# 旧版は proto ディレクトリ内で `-I. file_service.proto` を実行していたが、
# それだと生成される import が `import file_service_pb2` という裸の形になり、
# パッケージとして import したときに ModuleNotFoundError になる。
# 実際には生成後に手で `import lrPymRPC.proto.file_service_pb2 as ...` へ
# 書き換えられていたが、その手順がどこにも記録されていなかった。
# リポジトリルートから proto のパスごと渡せば、
# `from lrPymRPC.proto import file_service_pb2 as ...` が生成され手修正が要らない。
set -e

if [ ! -f "lrPymRPC/proto/file_service.proto" ]; then
  echo "ERROR: run this script from the repository root." >&2
  echo "       usage: bash lrPymRPC/proto/compile_proto.sh" >&2
  exit 1
fi

python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. lrPymRPC/proto/file_service.proto

echo "generated: lrPymRPC/proto/file_service_pb2.py"
echo "generated: lrPymRPC/proto/file_service_pb2_grpc.py"
