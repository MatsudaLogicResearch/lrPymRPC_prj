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
>cd    ~/.tls/tls_lrpymrpc
```

- Generate a private key:
```
>openssl genrsa -out client.key 2048
```

- Generate a Certificate Signing Request(CSR) :
```
openssl req -new \
  -key client.key \
  -subj "/CN=<username>" \
  -out client.csr
```
>Replace < username> with the name assigned by the server administrator.

- Send client.csr to the server administrator:

- Receive the signed certificate(client.crt) and CA certificate(ca.crt) from the server administrator.

- Keep crt files in your TLS directory:
```
ls ~/.tls/tls_lrpymrpc
#   client.key client.csr client.crt ca.crt
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
	--TLS_CONFIG_DIR "~/.tls/tls_lrPymRPC" \
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

## Known issues (future works)
