## ihnresolver


`ihnresolver` is a small but professional Python tool to resolve lists of hostnames and detect which hosts are serving HTTP/HTTPS. It is a Python port and enhancement of an existing bash workflow that used `dnsx` and `httpx`.



### Outputs


- `httpx-alive.txt` – Raw output. If the `httpx` binary is installed, this file will contain the raw stdout from `httpx` (preserving the original format). When `httpx` is not available, the script writes a compact, readable probe result into this file.
- `live-hosts.txt` – Hosts-only list from the probing stage. Each line contains a normalized host (no scheme, no trailing slash).


### Requirements


- Python 3.10+
- `rich` Python package (for colored CLI output)
- Optional (recommended): `dnsx` and `httpx` binaries (ProjectDiscovery) if you prefer their exact behavior and raw output to be preserved.


### Installing


```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


If you want the full discovery toolchain and exact raw outputs, install `dnsx` and `httpx` from ProjectDiscovery and put them in your `$PATH`.


### Usage


Basic invocation:


```bash
./ihnresolver.py -i subdomains.txt -o live-hosts.txt
```


Common flags:


- `-i, --input` : Input file (default: `subdomains.txt`)
- `-o, --output`: Output hosts file (default: `live-hosts.txt`)
- `-S, --sample`: Only process the top N lines (default: 0 = disabled)
- `-p, --pattern`: Regex to filter input lines (e.g. `api|admin|login`)
- `-t, --threads`: Concurrency/threads (default: 30)
- `--timeout`: Timeout for probes in seconds (default: 5)
- `-v, --verbose`: Verbose logging


Example with dnsx/httpx installed:


```bash
./ihnresolver.py -i subdomains.txt -o live-hosts.txt -p "api|admin" -t 100 --timeout 7 -v
```


If `dnsx` and `httpx` are installed, the script will delegate resolution and probing to them and preserve their raw `httpx` stdout in `httpx-alive.txt`.


### Notes & design rationale


- The tool prefers existing projectdiscovery binaries when present so users keep the same fingerprints and raw output.
- When binaries are missing, the script provides practical fallback behavior implemented in pure Python so the workflow is still useful.
- `rich` is used for a clear, professional CLI experience and a concise summary at the end of execution.


### Acknowledgement
This tool is built on top of concepts and workflows inspired by the ProjectDiscovery ecosystem, specifically the `dnsx` and `httpx` utilities.
