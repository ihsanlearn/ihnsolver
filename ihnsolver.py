#!/usr/bin/env python3
"""
ihnsolver.py
Resolve + Live host checker (Python port of the provided bash script)

Features:
 - Uses external tools dnsx and httpx when available (preferred)
 - Fallbacks: Python DNS resolver + concurrent requests probing
 - Produces two outputs:
     * httpx-alive.txt  -> raw httpx-like output (or our probe output when httpx missing)
     * live-hosts.txt  -> host-only list, one host per line (normalized, no trailing slashes)
 - Colorful professional banner and runtime output using 'rich'
 - CLI flags: -i, -o, -S, -p, -t (threads), --timeout, -v/--verbose, -h/--help
 - Owner: iihhn

Note: This script intentionally shells out to the external binaries when present so
that users who prefer discovery tools (dnsx/httpx) continue to get the exact raw
output preserved to httpx-alive.txt. When those binaries are not available, the
script performs equivalent probing and writes a readable raw output file.

"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text

# -----------------------------
# Metadata / defaults
# -----------------------------
OWNER = "iihhn"
APP = "ihnsolver"
VERSION = "1.0.0"

DEFAULT_INPUT = "subdomains.txt"
DEFAULT_OUTPUT = "live-hosts.txt"
DEFAULT_HTTPX_RAW = "httpx-alive.txt"
DEFAULT_CONCURRENCY = int(os.environ.get("CONCURRENCY", "30"))
DEFAULT_DNSX_THREADS = int(os.environ.get("DNSX_THREADS", "50"))
DEFAULT_HTTPX_THREADS = int(os.environ.get("HTTPX_THREADS", str(DEFAULT_CONCURRENCY)))
DEFAULT_TIMEOUT = int(os.environ.get("TIMEOUT", "5"))

console = Console()

# -----------------------------
# Utilities
# -----------------------------

def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def read_input(path: Path) -> List[str]:
    if not path.exists() or not path.is_file():
        console.print(f"[red][!] Input file not found or empty:[/] {path}")
        sys.exit(1)
    lines = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip().lower()
            if s:
                lines.append(s)
    return sorted(set(lines))


def filter_by_pattern(lines: Iterable[str], pattern: Optional[str]) -> List[str]:
    if not pattern:
        return list(lines)
    pat = re.compile(pattern, re.IGNORECASE)
    return [l for l in lines if pat.search(l)]


def sample_lines(lines: List[str], n: int) -> List[str]:
    if n <= 0:
        return lines
    return lines[:n]


def resolve_with_dnsx(hosts: Iterable[str], threads: int) -> List[str]:
    """Call dnsx -silent -a -aaaa -resp and return list of resolved hosts (one per line)."""
    cmd = [
        "dnsx",
        "-silent",
        "-a",
        "-aaaa",
        "-resp",
        "-threads",
        str(threads),
    ]
    console.log("[bold]dnsx command:[/] " + " ".join(cmd))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    stdin_data = "\n".join(hosts) + "\n"
    out, _ = p.communicate(stdin_data)
    # dnsx output format: <host> ... we'll take first token per line
    resolved = []
    for line in out.splitlines():
        if not line.strip():
            continue
        first = line.split()[0]
        resolved.append(first)
    return sorted(set(resolved))


def resolve_with_socket(hosts: Iterable[str], threads: int, timeout: int) -> List[str]:
    resolved = set()

    def check(h: str) -> Optional[str]:
        try:
            # getaddrinfo will raise if no A/AAAA
            socket.setdefaulttimeout(timeout)
            infos = socket.getaddrinfo(h, None)
            if infos:
                return h
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(check, h): h for h in hosts}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                resolved.add(r)
    return sorted(resolved)


def run_httpx_on_hosts(hosts: Iterable[str], threads: int, timeout: int, raw_out_path: Path) -> List[str]:
    """Use httpx binary when available. Writes raw stdout to raw_out_path.
    Returns list of host (normalized) found alive.
    """
    cmd = [
        "httpx",
        "-silent",
        "-status-code",
        "-title",
        "-tech-detect",
        "-timeout",
        str(timeout),
        "-threads",
        str(threads),
    ]
    console.log("[bold]httpx command:[/] " + " ".join(cmd))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    stdin_data = "\n".join(hosts) + "\n"
    out, _ = p.communicate(stdin_data)
    with raw_out_path.open("w", encoding="utf-8") as f:
        f.write(out)
    alive = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # httpx output begins with host/url as first token; take it
        first = line.split()[0]
        alive.append(first)
    return sorted(set(normalize_host(h) for h in alive))


def probe_host_with_requests(host: str, timeout: int) -> Optional[Tuple[str, int, str]]:
    """Probe host using socket to check if HTTP or HTTPS responds.
    Return (url, status_code, title_or_dash) or None if unreachable.
    This function intentionally uses the standard library only to avoid heavy deps.
    """
    # Try HTTPS first
    for scheme in ("https", "http"):
        try:
            url = f"{scheme}://{host}"
            # Use a simple socket connect to the host:443/80 to check
            parts = url.split("://", 1)[1]
            hostname = parts.split("/", 1)[0]
            port = 443 if scheme == "https" else 80
            with socket.create_connection((hostname, port), timeout=timeout) as s:
                # Send a minimal HTTP request
                req = f"HEAD / HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"
                s.sendall(req.encode())
                data = s.recv(1024).decode(errors="ignore")
                m = re.search(r"HTTP/\d+\.\d+\s+(\d{3})", data)
                if m:
                    code = int(m.group(1))
                else:
                    code = 0
                # Title extraction skipped for speed; placeholder
                title = "-"
                return (url, code, title)
        except Exception:
            continue
    return None


def run_probe_fallback(hosts: Iterable[str], threads: int, timeout: int, raw_out_path: Path) -> List[str]:
    alive_hosts = set()
    lines = []
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(probe_host_with_requests, h, timeout): h for h in hosts}
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TimeElapsedColumn(), console=console) as progress:
            task = progress.add_task("Probing hosts", total=len(futures))
            for fut in as_completed(futures):
                progress.update(task, advance=1)
                res = fut.result()
                if res:
                    url, code, title = res
                    lines.append(f"{url} {code} {title}\n")
                    alive_hosts.add(normalize_host(url))
    # write raw out
    with raw_out_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    return sorted(alive_hosts)


def normalize_host(h: str) -> str:
    # Remove scheme and trailing slashes
    h2 = re.sub(r"^https?://", "", h, flags=re.IGNORECASE)
    h2 = h2.rstrip("/ ")
    return h2


# -----------------------------
# Main
# -----------------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ihnsolver - resolve and live-host checker (owner: iihhn)")
    p.add_argument("-i", "--input", default=DEFAULT_INPUT, help=f"Input file (default: {DEFAULT_INPUT})")
    p.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help=f"Output file (default: {DEFAULT_OUTPUT})")
    p.add_argument("-S", "--sample", default=0, type=int, help="Sample top N results (0=disabled)")
    p.add_argument("-p", "--pattern", default="", help="Regex filter (e.g. 'api|admin|login')")
    p.add_argument("-t", "--threads", default=DEFAULT_CONCURRENCY, type=int, help=f"Concurrency/threads (default: {DEFAULT_CONCURRENCY})")
    p.add_argument("--dnsx-threads", default=DEFAULT_DNSX_THREADS, type=int, help=f"dnsx threads if used (default: {DEFAULT_DNSX_THREADS})")
    p.add_argument("--timeout", default=DEFAULT_TIMEOUT, type=int, help=f"Probe timeout seconds (default: {DEFAULT_TIMEOUT})")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p.add_argument("--version", action="version", version=VERSION)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_argparser().parse_args(argv)

    # Banner
    banner = Text(r"""
.__.__                        .__                     
|__|  |__   ____   __________ |  |___  __ ___________ 
|  |  |  \ /    \ /  ___/  _ \|  |\  \/ // __ \_  __ \
|  |   Y  \   |  \\___ (  <_> )  |_\   /\  ___/|  | \/
|__|___|  /___|  /____  >____/|____/\_/  \___  >__|   
        \/     \/     \/                     \/       
v1.0.0
        """

        , style="yellow")
    owner = Text(f"{OWNER}", style="italic")
    console.print(Panel(banner, subtitle=owner))

    console.print(f"[bold]Input:[/] {args.input}")
    console.print(f"[bold]Output (hosts):[/] {args.output}")
    console.print(f"[bold]Raw httpx file:[/] {DEFAULT_HTTPX_RAW}")
    console.print(f"[bold]Threads:[/] {args.threads}  [bold]Timeout:[/] {args.timeout}s")
    if args.pattern:
        console.print(f"[bold]Filter pattern:[/] {args.pattern}")
    if args.sample:
        console.print(f"[bold]Sample limit:[/] {args.sample}")
    console.print()

    in_path = Path(args.input)
    out_path = Path(args.output)
    raw_out_path = Path(DEFAULT_HTTPX_RAW)

    hosts = read_input(in_path)
    console.print(f"[blue]Deduped input:[/] {len(hosts)} lines")

    if args.pattern:
        hosts = filter_by_pattern(hosts, args.pattern)
        console.print(f"[blue]After pattern filter:[/] {len(hosts)} lines")

    if args.sample > 0:
        hosts = sample_lines(hosts, args.sample)
        console.print(f"[blue]After sampling:[/] {len(hosts)} lines")

    # Resolve
    console.print("[bold]Resolving hosts...[/]")
    resolved: List[str] = []
    if command_exists("dnsx"):
        if args.verbose:
            console.log("Using dnsx to resolve hosts")
        resolved = resolve_with_dnsx(hosts, args.dnsx_threads)
    else:
        if args.verbose:
            console.log("dnsx not found, using socket fallback")
        resolved = resolve_with_socket(hosts, args.threads, args.timeout)

    console.print(f"[green]Resolved count:[/] {len(resolved)}")

    # Probe for HTTP(S)
    console.print("[bold]Probing resolved hosts for HTTP(S) service...[/]")
    alive_hosts: List[str]
    if command_exists("httpx"):
        if args.verbose:
            console.log("Using httpx to probe hosts")
        alive_hosts = run_httpx_on_hosts(resolved, args.threads, args.timeout, raw_out_path)
    else:
        if args.verbose:
            console.log("httpx not found, using socket-based probe fallback")
        alive_hosts = run_probe_fallback(resolved, args.threads, args.timeout, raw_out_path)

    # Write final hosts-only output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for h in sorted(set(alive_hosts)):
            f.write(h.rstrip("/\n") + "\n")

    console.print()
    console.print(Panel(Text(f"Done. Resolved: {len(resolved)} | Live hosts: {len(set(alive_hosts))}\nRaw details: {raw_out_path}\nHosts file: {out_path}"), title="Summary"))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Interrupted by user.[/yellow]")
        raise SystemExit(1)