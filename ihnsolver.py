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
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# -----------------------------
# Metadata / defaults
# -----------------------------
OWNER = "iihhn"
APP = "ihnsolver"
VERSION = "1.0.0"

DEFAULT_INPUT = "subdomains.txt"
DEFAULT_OUTPUT = "live-hosts.txt"
DEFAULT_HTTPX_JSON = "httpx-alive.json"

DEFAULT_CONCURRENCY = int(os.environ.get("CONCURRENCY", "30"))
DEFAULT_DNSX_THREADS = int(os.environ.get("DNSX_THREADS", "50"))
DEFAULT_TIMEOUT = int(os.environ.get("TIMEOUT", "5"))

console = Console()

# -----------------------------
# Utilities
# -----------------------------

def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def normalize_host(h: str) -> str:
    h = re.sub(r"^https?://", "", h, flags=re.I)
    return h.rstrip("/ ")


def read_input(path: Path) -> List[str]:
    if not path.exists():
        console.print(f"[red][!] Input file not found:[/] {path}")
        sys.exit(1)

    lines = set()
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip().lower()
            if s:
                lines.add(s)
    return sorted(lines)


def filter_by_pattern(lines: Iterable[str], pattern: str) -> List[str]:
    if not pattern:
        return list(lines)
    r = re.compile(pattern, re.I)
    return [l for l in lines if r.search(l)]


def sample_lines(lines: List[str], n: int) -> List[str]:
    return lines if n <= 0 else lines[:n]


def resolve_with_dnsx(hosts: Iterable[str], threads: int) -> List[str]:
    cmd = [
        "dnsx",
        "-silent",
        "-a",
        "-aaaa",
        "-resp",
        "-threads",
        str(threads),
    ]

    console.log("[bold]dnsx:[/] " + " ".join(cmd))

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    out, _ = p.communicate("\n".join(hosts) + "\n")

    resolved = set()
    for line in out.splitlines():
        if line.strip():
            resolved.add(line.split()[0])

    return sorted(resolved)


def resolve_with_socket(hosts: Iterable[str], timeout: int, threads: int) -> List[str]:
    resolved = set()

    def check(h: str):
        try:
            socket.setdefaulttimeout(timeout)
            if socket.getaddrinfo(h, None):
                return h
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = [ex.submit(check, h) for h in hosts]
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                resolved.add(r)

    return sorted(resolved)


def run_httpx_on_hosts(
    hosts: Iterable[str],
    threads: int,
    timeout: int,
    json_out: Path,
) -> List[str]:

    cmd = [
        "httpx",
        "-silent",
        "-json",
        "-tech-detect",
        "-status-code",
        "-title",
        "-timeout", str(timeout),
        "-threads", str(threads),
    ]

    console.log("[bold]httpx:[/] " + " ".join(cmd))

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    out, _ = p.communicate("\n".join(hosts) + "\n")

    alive = set()

    with json_out.open("w", encoding="utf-8") as jf:
        for line in out.splitlines():
            if not line.strip():
                continue

            # RAW JSON httpx (tidak disentuh)
            jf.write(line + "\n")

            try:
                obj = json.loads(line)
                url = obj.get("url") or obj.get("host")
                if url:
                    alive.add(normalize_host(url))
            except Exception:
                pass

    return sorted(alive)

# -----------------------------
# Main
# -----------------------------

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ihnsolver - resolve & probe live hosts")
    p.add_argument("-i", "--input", default=DEFAULT_INPUT)
    p.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    p.add_argument("-p", "--pattern", default="")
    p.add_argument("-S", "--sample", type=int, default=0)
    p.add_argument("-t", "--threads", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--dnsx-threads", type=int, default=DEFAULT_DNSX_THREADS)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("-v", "--verbose", action="store_true")
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
    )
    
    console.print(Panel(banner, subtitle=f"{OWNER} · v{VERSION}"))

    in_path = Path(args.input)
    out_path = Path(args.output)
    json_out = Path(DEFAULT_HTTPX_JSON)

    hosts = read_input(in_path)

    if args.pattern:
        hosts = filter_by_pattern(hosts, args.pattern)

    if args.sample:
        hosts = sample_lines(hosts, args.sample)

    console.print(f"[blue]Input hosts:[/] {len(hosts)}")

    # Resolve
    if command_exists("dnsx"):
        resolved = resolve_with_dnsx(hosts, args.dnsx_threads)
    else:
        resolved = resolve_with_socket(hosts, args.timeout, args.threads)

    console.print(f"[green]Resolved:[/] {len(resolved)}")

    if not command_exists("httpx"):
        console.print("[red][!] httpx not found. Install httpx first.[/]")
        return 1

    alive_hosts = run_httpx_on_hosts(
        resolved,
        args.threads,
        args.timeout,
        json_out,
    )

    # Write live hosts
    with out_path.open("w", encoding="utf-8") as f:
        for h in alive_hosts:
            f.write(h + "\n")

    dead_hosts = sorted(set(hosts) - set(alive_hosts))
    with Path("dead-hosts.txt").open("w", encoding="utf-8") as f:
        for h in dead_hosts:
            f.write(h + "\n")

    console.print(
        Panel(
            Text(
                f"Done\n"
                f"Resolved     : {len(resolved)}\n"
                f"Live hosts   : {len(alive_hosts)}\n"
                f"Dead hosts   : {len(dead_hosts)}\n\n"
                f"httpx JSON  : {json_out}\n"
                f"Hosts file  : {out_path}\n"
                f"Dead hosts  : dead-hosts.txt"
            ),
            title="Summary",
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow][!] Interrupted by user[/]")
        raise SystemExit(1)
