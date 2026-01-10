#===================================================================
# This file is part of lrPymRPC project.
# Copyright (C) 2025 LogicResearch K.K (Author: MATSUDA Masahiro)
# 
# This script file is licensed under the MIT License.
#===================================================================
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. file_service.proto
