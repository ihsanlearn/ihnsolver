<pre align="left">

.__ __                        .__
|__|  |__   ____   __________ |  |___  __ ___________
|  |  |  \ /    \ /  ___/  _ \|  |\  \/ // __ \_  __ \
|  |   Y  \  |  \\___ (  <_> )  |_\   /\  ___/|  | \/
|__|___|  /___|  /____  >____/|____/\_/  \___  >__|
       \/     \/     \/                     \/
</pre>
<p align="center">
  <strong>Professional Hybrid Resolver & Live Host Prober</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT">
  <img src="https://img.shields.io/badge/Owner-Ihsan-red?style=for-the-badge" alt="Owner: Ihsan">
  <img src="https://img.shields.io/badge/Requires-Rich-purple?style=for-the-badge" alt="Requires: Rich">
</p>

`ihnsolver` is a professional Python tool to resolve lists of hostnames and detect which hosts are serving HTTP/HTTPS services.

This tool is a port and enhancement of an existing bash workflow, intelligently using `dnsx` and `httpx` when available, or falling back to a reliable native Python implementation.

---

## ✨ Key Features

* **Hybrid Engine:** Automatically uses `dnsx` and `httpx` from ProjectDiscovery if detected in your `$PATH` for maximum speed and fingerprinting accuracy.
* **Seamless Fallback:** If the binaries are not found, `ihnsolver` switches to a concurrent, native Python-based DNS resolver and socket prober.
* **Professional Terminal UI:** Built with `rich` for a beautiful, clear, and professional command-line output, complete with progress bars and a colored summary.
* **Dual Output:** Generates two essential files:
    1.  `live-hosts.txt`: A clean, normalized list of live hosts (no scheme/port).
    2.  `httpx-alive.txt`: Preserves the original raw `httpx` output (if used) or an informative custom probe output.
* **Flexible Filtering:** Supports input filtering with regex (`-p`), sampling (`-S`), and concurrency control (`-t`).

## 🎯 Design Rationale: The Hybrid Approach

This tool is intentionally designed to **prefer ProjectDiscovery binaries** (`dnsx`, `httpx`) when present. Why?

1.  **Consistency:** Ensures bug hunters accustomed to raw `httpx` output get the exact same format.
2.  **Speed & Fingerprinting:** Leverages the advanced optimizations and fingerprinting techniques of these industry-standard tools.

When those binaries are **absent**, `ihnsolver` doesn't fail. It switches to its native Python fallback mode, providing the core functionality (DNS resolution and HTTP/S port probing) so your workflow keeps running in any environment.

## 🚀 Installation

1.  Clone this repository (or save the script).
2.  Create and activate a virtual environment (recommended):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  Install dependencies (only `rich`):

    ```bash
    pip install rich
    # Or from a requirements.txt if you create one
    # pip install -r requirements.txt
    ```

4.  **(Optional but Recommended)** For full functionality, install `dnsx` and `httpx` from ProjectDiscovery and ensure they are in your `$PATH`.

## 💻 Usage

Basic usage, reading from `subdomains.txt` and saving to `live-hosts.txt`:

```bash
python3 ihnsolver.py
```

A more complete example with regex filtering, higher threads, and verbose output:

```bash
python3 ihnsolver.py -i targets.txt -o my-live-hosts.txt -p "api|admin|dev" -t 100 -v
```

## Command-Line Options (Flags)

```md
Flag (Short),Flag (Long),Description,Default
-i,--input,Input file containing subdomains.,subdomains.txt
-o,--output,Output file for live hosts.,live-hosts.txt
-t,--threads,Number of concurrent threads.,30
-S,--sample,Only process the top N lines (0=disabled).,0
-p,--pattern,Regex pattern to filter input.,(Empty)
,--timeout,Probe timeout in seconds.,5
,--dnsx-threads,Dedicated threads for dnsx (if used).,50
-v,--verbose,Enable verbose logging.,(Off)
-h,--help,Show the help message.,
```
