# PROJECT

gRPC client for Python modules.

## Introduction

This project provides a Python client to communicate with a lrPymRPC_server(gRPC server) over a network with TLS.

- Dataflow diagram:
<pre>
     [client]                                 [server] 
TLS handshake: 
    client.key--+ 
		client.crt--+=======================> verify & authenticate  
    ca.crt    --+ 
 
DATAFLOW: 
   SOURCE     ==[stream:DataChunk]=====>  /tmp/<UUID>/SOURCE 
   REPO_URL   ==[request:tool]=========>  pip install <REPO_URL> 
   CMD        ==[request:command_opt]==>  execute <CMD> 
   RESULT     <=[stream:DataChunk]=====   /tmp/<UUID>/RESULT 
</pre>


## INSTALL
```bash
pip install git+https://github.com/MatsudaLogicResearch/lrPymRPC_prj.git
```

## Required Tools
- Python 3.9+

## TLS Setup
- Create a TLS directory:
```
>mkdir ~/.tls/tls_lrpymrpc
>mkdir ~/.tls/tls_lrpymrpc/ca
>mkdir ~/.tls/tls_lrpymrpc/client

>cd    ~/.tls/tls_lrpymrpc
```

- Generate a private key for Client:
```
openssl genrsa -out client.key 2048
```

- Generate a Certificate Signing Request(CSR) for Client:
```
openssl req -new \
  -key client/client.key \
  -subj "/CN=<username>" \
  -out client.csr
```
>Replace < username> with the name assigned by the server administrator.

- Send client.csr to the server administrator:

- Receive the signed certificate(client.crt) and CA certificate(ca.crt) from the server administrator.

- Keep crt files in your TLS directory:
```
ls ~/.tls/tls_lrpymrpc/*

# ~/.tls/tls_lrpymrpc/client/client.key
# ~/.tls/tls_lrpymrpc/client/client.crs
# ~/.tls/tls_lrpymrpc/client/client.crt
# ~/.tls/tls_lrpymrpc/ca/ca.crt

```

## USAGE

```
python -m lrPymRPC
  [-h] \
	[-v] \
	[--REPO_URL REPO_URL] \
	[--CMD CMD] \
	[--SERVER_IP SERVER_IP] \
	[--SERVER_PORT SERVER_PORT] \
	[--SOURCE SOURCE [SOURCE ...]] \
	[--RESULT RESULT [RESULT ...]] \
	[--SOURCE_INCLUDE [SOURCE_INCLUDE ...]] \
	[--SOURCE_EXCLUDE [SOURCE_EXCLUDE ...]] \
	[--SOURCE_MATCH SOURCE_MATCH [SOURCE_MATCH ...]] \
	[--RUN_NAME RUN_NAME] \
	[--TLS_CONFIG_DIR TLS_CONFIG_DIR] \
```

### option
```
  -h, --help                 show this help message and exit \
  -v, --version              show program's version number and exit \
  --REPO_URL REPO_URL        pip-install module in repo mapping string(name=url,name=url,) \
  --CMD CMD                  command & parameters to module. \
  --SERVER_IP SERVER_IP      IP address of RPC server \
  --SERVER_PORT SERVER_PORT  TCP port of RPC server \
  --SOURCE SOURCE [SOURCE ...] source directory used in make command. \
  --RESULT RESULT [RESULT ...] result directory output by make command. \
  --SOURCE_INCLUDE [SOURCE_INCLUDE ...] Include only files with these extensions in SOURCE (e.g. .cdl .sp). Empty=all files. \
  --SOURCE_EXCLUDE [SOURCE_EXCLUDE ...] Exclude files with these extensions from SOURCE (e.g. .gds .gds2). \
  --SOURCE_MATCH SOURCE_MATCH [SOURCE_MATCH ...] Include only files whose path contains any of these strings (e.g. gf180mcuC). Empty=all files. \
  --RUN_NAME RUN_NAME        Isolate this run under ./<RUN_NAME>/ (single dir name, no slashes). Empty=current dir (backward compatible). For parallel execution. \
	--TLS_CONFIG_DIR TLS_CONFIG_DIR TLS configuration directory\
                        
```


## example
### A. install python module & execute a local python script.
#### Tools:
  https://github.com/snishizawa/libretto

#### Preparation:
- Start the lrPymRPC server.(e.g. 127.0.0.1)

- Clone the tools repository:
```
git clone git@github.com:snishizawa/libretto.git
```

- Modify the Makefile to use lrPymRPC:

``` makefile
  #-- Original command comment out
	#time python3 $(LIBRETTO) -b $(CMD_FILE);

	python3 -m lrPymRPC \
	--SERVER_IP 127.0.0.1 \
	--REPO_URL "numpy=numpy" \
	--TLS_CONFIG_DIR "~/.tls/tls_lrpymrpc" \
	--CMD "python $(LIBRETTO) -b $(CMD_FILE)" \
	--SOURCE "IHP130 cmd script work" \
	--RESULT "$(LIB) $(MD) $(PROCESS_NAME).v" \
```

#### run
```
make clean; mkdir work; make
```

#### result
```
> ls
# IHP130  IHP130.v  IHP130_1P5V_27C.lib  IHP130_1P5V_27C.md  LICENSE  Makefile  OSU350  SKY130  cat_run.sh  cmd  script  tcl  work
```

## Parallel Execution with `--RUN_NAME`

`--RUN_NAME <name>` isolates each lrPymRPC invocation under `./<name>/` on the client side, so multiple runs can execute in parallel without colliding on `_source.tar.gz`, `_result.tar.gz`, or extracted result directories. Server-side behavior is unchanged: the same archive content is sent and received; only the client-side filesystem layout differs.

### Behavior

| `--RUN_NAME` | Source/Result archive | Extract path |
|---|---|---|
| empty (default) | `./_source.tar.gz`, `./_result.tar.gz` | CWD (`./rslt`, `./work`, ...) |
| `run1` | `./run1/_source.tar.gz`, `./run1/_result.tar.gz` | `./run1/` (`./run1/rslt`, `./run1/work`, ...) |

The directory `./<RUN_NAME>/` is created automatically (`mkdir -p`) just before the source archive is built.

### Validation rules

`--RUN_NAME` accepts a single directory name only. Examples:

| Value | Result |
|---|---|
| `""` (default) | OK — backward-compatible mode, no isolation |
| `A`, `run1`, `job_42` | OK — isolates under `./A/`, `./run1/`, `./job_42/` |
| `a/b`, `/abs`, `a\b`, `foo/` | rejected with `ValueError` (no slashes/backslashes) |
| `.`, `..`, `../foo` | rejected with `ValueError` (no dot-only paths) |

### Example (two parallel runs)

```bash
# Common setup: a placeholder source directory
mkdir -p rslt

# Terminal A
python -u -m lrPymRPC \
    --SERVER_IP 192.168.1.10 \
    --SOURCE rslt \
    --RESULT rslt \
    --RUN_NAME A \
    --CMD "bash -c 'echo hello-A > rslt/test.txt'"
# Result: ./A/rslt/test.txt  contents = "hello-A"

# Terminal B (run concurrently with Terminal A)
python -u -m lrPymRPC \
    --SERVER_IP 192.168.1.10 \
    --SOURCE rslt \
    --RESULT rslt \
    --RUN_NAME B \
    --CMD "bash -c 'echo hello-B > rslt/test.txt'"
# Result: ./B/rslt/test.txt  contents = "hello-B"
```

Both runs share the client-side `./rslt` source directory (used only as an empty placeholder, sent to the server as part of `_source.tar.gz`), but their results land in independent `./A/` and `./B/` subtrees with no cross-contamination.

### Caller-side checklist (tools wrapping lrPymRPC)

When wrapping `lrPymRPC` in a higher-level script (e.g. `debug_run.sh` of another project) and you want to support `--RUN_NAME`:

1. Pass `--RUN_NAME "$RUN_NAME"` (or omit when empty) to `lrPymRPC`.
2. Any post-processing that reads `rslt/...` or `work/...` on the client side must be prefixed with `${RUN_NAME:+$RUN_NAME/}` when `RUN_NAME` is set.
3. Server-side paths inside `--CMD` (e.g. `bash -c '... > rslt/test.txt'`) are NOT prefixed — the server always sees `rslt/` at its tmpdir root.
4. Log files and any other client-side artifacts of the same run should also be placed under `./<RUN_NAME>/` for clean isolation.


## Known issues (future works)
