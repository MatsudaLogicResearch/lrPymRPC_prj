# PROJECT

gRPC client for Python module.

## Introduction

You can install & execute Python-module on ｇRPC-SERVER on network.


## INSTALL
```bash
pip install git+https://github.com/MatsudaLogicResearch/lrPymRPC_prj.git
```

## Required Tools
- Python

## USAGE

```
python -m lrPymRPC [-h] [-v] [--REPO_URL REPO_URL] [--CMD CMD] [--SERVER_IP SERVER_IP] [--SERVER_PORT SERVER_PORT] [--SOURCE SOURCE [SOURCE ...]] [--RESULT RESULT [RESULT ...]]
```

### option
```
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --REPO_URL REPO_URL   git repository for module.
  --CMD CMD             command & parameters to module.
  --SERVER_IP SERVER_IP
                        IP address of RPC server
  --SERVER_PORT SERVER_PORT
                        TCP port of RCP server
  --SOURCE SOURCE [SOURCE ...]
                        source direcrory used in make command.
  --RESULT RESULT [RESULT ...]
                        result direcrory output by make commnand.

```


## example for charao

- command
```
python -m lrPymRPC \
--REPO_URL "git+https://github.com/MatsudaLogicResearch/charao_prj.git@main" \
--SERVER_IP 127.0.0.1 \
--SERVER_PORT 8766 \
--CMD "charao -f OSU035 -g std -u 5P00 -v VENDOR -r REVxx -p TT -t 25.0 --vdd 5.0 --cells_only INV_1X" \
--SOURCE src target \
--RESULT rslt
```

- result
```
ls rslt/
  OSU035CB5P00NORMALV00.00_TTV5P00C25_b00.lib
	OSU035CB5P00NORMALV00.00_TTV5P00C25_b00.md
	OSU035CB5P00NORMALV00.00_b00.v

```

## Known issues (future works)
