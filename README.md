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
	[--PIP_REQ PIP_REQ] \
	[--KEEP_ARCHIVE] \
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
  --PIP_REQ PIP_REQ          requirements file for 'pip install -r' on the server. Must be located under --SOURCE. Requires server >= 0.4.0. \
  --KEEP_ARCHIVE             keep _source.tar.gz / _result.tar.gz after the run (default: remove). For debugging what was actually sent and received. \
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

## Keeping the transfer archives (`--KEEP_ARCHIVE`)

By default the client deletes `_source.tar.gz` and `_result.tar.gz` when the run finishes.
Pass `--KEEP_ARCHIVE` to keep them, so you can inspect **what was actually sent and received**:

```
python -u -m lrPymRPC ... --KEEP_ARCHIVE
...
[<ip:port>]:Check: keep archive file=_source.tar.gz (12.34 MB)
[<ip:port>]:Check: keep archive file=_result.tar.gz (0.51 MB)
```

```
tar tzf _source.tar.gz | head        # what went to the server
tar tzf _result.tar.gz | head        # what came back
```

- Sizes are reported in MB, with **0.01 MB as the smallest value shown**.
- With `--RUN_NAME`, the files live under `./<RUN_NAME>/`.
- Useful when you hit the server's upload size limit: the error tells you the limit, and the
  kept archive tells you what made it that big.
- **The archives are overwritten on the next run, except when a run produces no result** - then the
  previous `_result.tar.gz` stays behind. Delete it yourself when it would confuse you.


## Each run starts from an empty server-side directory

Every run gets a **fresh** working directory on the server (`/tmp/lrpymrpc/<PORT>/<UUID>/`), and it
is removed when the session ends. Nothing carries over between runs.

That has two consequences worth knowing before you debug a build:

**Multi-stage builds must happen in one `--CMD`.** Locally you can run `make html` today and
`make latexpdf` tomorrow, because `_build/` is still there. Here the second run starts from nothing,
so a target that consumes the output of an earlier target has to be in the same command:

```
--CMD "make -C docs html latexpdf dist"     # OK
--CMD "make -C docs latexpdf"               # fails if the target needs html output from a past run
```

**A successful build still returns nothing unless `--RESULT` matches.** The only hint is one line:

```
Check: Download data is not exist.
```

Check that `--RESULT` names a directory that exists **at the root of the extracted archive**, using
a top-level name only (`_build`, not `docs/_build`). A build writing into `_build/` while `--RESULT`
says `build` produces exactly the message above - with the files sitting on the server until the
session is cleaned up.

`--KEEP_ARCHIVE` helps here: it leaves `_result.tar.gz` behind so you can see what actually came
back, rather than guessing.


## Server-side limits you may hit

The server enforces limits that the client cannot query in advance. They surface as gRPC errors
containing the limit value, so the message itself tells you what to fix.

### Upload size

The server applies **one size limit twice** (`--MAX_UPLOAD_MB` on the server side, 2 GB by default):

| What is measured | Error (`RESOURCE_EXHAUSTED`) |
|---|---|
| **Compressed size** of the `--SOURCE` archive that is sent | `Upload: size limit(<N> MB) exceeded (<X> MB received)` |
| **Extracted size** - the total size of everything inside that archive | `Upload: extracted size limit(<N> MB) exceeded (<X> MB extracted)` |

Both must be within the limit. Because `--SOURCE` usually compresses well, the extracted size is
the one that normally decides. Use `--SOURCE_INCLUDE` / `--SOURCE_EXCLUDE` / `--SOURCE_MATCH` to
drop files you do not need (e.g. GDS) when you hit the limit.

A rejected upload leaves nothing on the server.

### Idle session lifetime

A session directory on the server is removed once it has been idle for `--SESSION_TTL_SEC`
(1 hour by default). **A session with a running RPC is never removed**, no matter how long the
command runs or how long it stays silent - so a multi-hour `--CMD` is safe. The timer starts when
the last RPC returns, so pick up your `--RESULT` in the same run rather than much later.


## Requirements file with `--PIP_REQ`

`--PIP_REQ` installs a requirements file on the server with `pip install -r` before `--REPO_URL`
packages are installed.

```
python -u -m lrPymRPC \
  --SERVER_IP 192.168.0.10 \
  --SOURCE pip_pkg src \
  --RESULT rslt \
  --PIP_REQ ./pip_pkg/requirements.txt \
  --CMD "python3 -m mytool"
```

- `--REPO_URL` and `--PIP_REQ` are independent. **Either one alone, or neither, also works.**
- `--PIP_REQ` takes a single file. Merge multiple requirements into one file if needed.
- Install order is **`--PIP_REQ` first, then `--REPO_URL`**.
- pip output is streamed back in real time.
- No import check is performed for `--PIP_REQ` (module names cannot be derived from a requirements file).
  If pip fails, the run is aborted with `ERR: pip install -r failed ...` and `--CMD` is NOT executed.

### The file must be inside `--SOURCE`

Each `--SOURCE` entry is stored in the archive by its **basename**, so the client rewrites the
`--PIP_REQ` path accordingly and prints the result:

```
PIP_REQ: ./pip_pkg/requirements.txt -> pip_pkg/requirements.txt
```

| `--SOURCE` | `--PIP_REQ` | sent to server |
|---|---|---|
| `pip_pkg src` | `./pip_pkg/requirements.txt` | `pip_pkg/requirements.txt` |
| `work/pip_pkg` | `./work/pip_pkg/req.txt` | `pip_pkg/req.txt` |

If the file is not under `--SOURCE` (or does not exist), the client stops **before connecting**:

```
ERROR: --PIP_REQ must be located under --SOURCE (so that it is transferred): ...
```

### Paths inside the requirements file

pip resolves relative paths in a requirements file **against the current working directory**,
not against the location of the requirements file. On the server the working directory is the
root of the extracted archive, so write paths from there:

```
# OK (relative to the extracted archive root = basename of each --SOURCE entry)
-e ./pip_pkg/lrPya_prj
./pip_pkg/mypkg-0.1.0-py3-none-any.whl
jsoncomment

# NG (relative to the requirements file itself)
-e ./lrPya_prj
```

### Server version

`--PIP_REQ` requires **lrPymRPC_server 0.4.0 or later**. When an older server is detected the run
stops with:

```
ERROR: --PIP_REQ requires lrPymRPC_server >= 0.4.0, but the server is 0.3.9. Upgrade the server, or drop --PIP_REQ.
```

Runs without `--PIP_REQ` keep working against older servers.


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
