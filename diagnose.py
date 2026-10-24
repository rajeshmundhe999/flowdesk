"""FlowDesk Local Network & Connectivity Diagnostics Utility.

Performs non-intrusive DNS resolution, TLS handshake, and single polite HTTP
reachability checks for domains explicitly listed in a local configuration file.
"""

import argparse
import json
import socket
import ssl
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    target_name: str
    host: str
    dns_status: str
    dns_latency_ms: float
    dns_info: str
    tls_status: str
    tls_latency_ms: float
    tls_info: str
    http_status: str
    http_latency_ms: float
    http_info: str
    is_slow: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_name": self.target_name,
            "host": self.host,
            "dns": {
                "status": self.dns_status,
                "latency_ms": round(self.dns_latency_ms, 1),
                "info": self.dns_info,
            },
            "tls": {
                "status": self.tls_status,
                "latency_ms": round(self.tls_latency_ms, 1),
                "info": self.tls_info,
            },
            "http": {
                "status": self.http_status,
                "latency_ms": round(self.http_latency_ms, 1),
                "info": self.http_info,
            },
            "is_slow": self.is_slow,
        }


def check_dns(host: str, timeout: float = 3.0) -> tuple[str, float, str]:
    """Test DNS resolution for a host. Returns (status, latency_ms, info)."""
    start = time.perf_counter()
    try:
        socket.setdefaulttimeout(timeout)
        addr_info = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        latency = (time.perf_counter() - start) * 1000.0
        ip = addr_info[0][4][0] if addr_info else "Resolved"
        return "PASS", latency, f"Resolved to {ip}"
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000.0
        return "FAIL", latency, f"DNS error: {exc}"


def check_tls(host: str, port: int = 443, timeout: float = 3.0) -> tuple[str, float, str]:
    """Test TLS handshake and certificate validity. Returns (status, latency_ms, info)."""
    start = time.perf_counter()
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=host) as ssock:
                version = ssock.version() or "TLS"
                cipher = ssock.cipher()
                cipher_name = cipher[0] if cipher else "UnknownCipher"
                latency = (time.perf_counter() - start) * 1000.0
                return "PASS", latency, f"{version} ({cipher_name})"
    except ssl.SSLCertVerificationError as cert_err:
        latency = (time.perf_counter() - start) * 1000.0
        return "FAIL", latency, f"Untrusted CA / SSL Inspection: {cert_err.verify_message}"
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000.0
        return "FAIL", latency, f"TLS error: {exc}"


def check_http(url: str, timeout: float = 3.0) -> tuple[str, float, str]:
    """Perform a single polite HTTP reachability probe. Returns (status, latency_ms, info)."""
    start = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FlowDesk-Diagnostics/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            latency = (time.perf_counter() - start) * 1000.0
            return "PASS", latency, f"HTTP {status_code}"
    except urllib.error.HTTPError as http_err:
        latency = (time.perf_counter() - start) * 1000.0
        # HTTP 403 or 404 still indicates network and server reachability
        return "PASS", latency, f"HTTP {http_err.code} (Reachable)"
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000.0
        return "FAIL", latency, f"HTTP error: {exc}"


def run_diagnostics(config_path: Path | str) -> list[CheckResult]:
    """Execute all network diagnostic checks defined in the config file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Diagnostics config not found at: {path}")

    config = json.loads(path.read_text(encoding="utf-8"))
    timeout = float(config.get("timeout_seconds", 3.0))
    warn_threshold = float(config.get("latency_warn_threshold_ms", 500.0))
    endpoints = config.get("endpoints", [])

    results: list[CheckResult] = []

    for ep in endpoints:
        name = ep.get("name", "Unknown Endpoint")
        host = ep.get("host", "")
        url = ep.get("url", f"https://{host}")

        dns_status, dns_ms, dns_info = check_dns(host, timeout=timeout)

        # Only attempt TLS/HTTP if DNS resolved successfully
        if dns_status == "PASS":
            tls_status, tls_ms, tls_info = check_tls(host, timeout=timeout)
            http_status, http_ms, http_info = check_http(url, timeout=timeout)
        else:
            tls_status, tls_ms, tls_info = "FAIL", 0.0, "Skipped due to DNS failure"
            http_status, http_ms, http_info = "FAIL", 0.0, "Skipped due to DNS failure"

        total_ms = dns_ms + tls_ms + http_ms
        is_slow = total_ms > warn_threshold or any(
            ms > warn_threshold for ms in (dns_ms, tls_ms, http_ms)
        )

        results.append(
            CheckResult(
                target_name=name,
                host=host,
                dns_status=dns_status,
                dns_latency_ms=dns_ms,
                dns_info=dns_info,
                tls_status=tls_status,
                tls_latency_ms=tls_ms,
                tls_info=tls_info,
                http_status=http_status,
                http_latency_ms=http_ms,
                http_info=http_info,
                is_slow=is_slow,
            )
        )

    return results


def format_text_report(results: list[CheckResult], warn_threshold: float = 500.0) -> str:
    """Format diagnostic results into a clean human-readable CLI table."""
    lines = [
        "=" * 78,
        "  FlowDesk Local Connectivity Diagnostics Helper",
        "=" * 78,
        f"Latency warning threshold: {warn_threshold} ms",
        "-" * 78,
    ]

    for r in results:
        slow_tag = " [WARN: SLOW]" if r.is_slow else ""
        lines.append(f"\nTarget: {r.target_name} ({r.host}){slow_tag}")
        lines.append(f"  - DNS:  [{r.dns_status}] {r.dns_latency_ms:6.1f}ms -> {r.dns_info}")
        lines.append(f"  - TLS:  [{r.tls_status}] {r.tls_latency_ms:6.1f}ms -> {r.tls_info}")
        lines.append(f"  - HTTP: [{r.http_status}] {r.http_latency_ms:6.1f}ms -> {r.http_info}")

    lines.append("\n" + "-" * 78)

    # Actionable guidance
    has_dns_fail = any(r.dns_status == "FAIL" for r in results)
    has_tls_fail = any(r.tls_status == "FAIL" for r in results)
    has_slow = any(r.is_slow for r in results)

    if has_tls_fail:
        lines.append(
            "Recommendation: TLS handshake failed. Check corporate proxy / VPN SSL inspection.\n"
            "See KB article: docs/known_issues/net_connection_lost_vpn.md"
        )
    elif has_dns_fail:
        lines.append(
            "Recommendation: DNS resolution failed. Check local network or DNS server settings."
        )
    elif has_slow:
        lines.append(
            "Recommendation: Elevated latency detected (> threshold). May trigger\n"
            "'Taking longer than usual' timeouts. See KB net_timeout_taking_longer.md"
        )
    else:
        lines.append("Connectivity Status: ALL CHECKS PASSED. Network connectivity is healthy.")

    lines.append("=" * 78)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FlowDesk Local Network & Connectivity Diagnostics Utility"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="diagnose_config.json",
        help="Path to diagnostics configuration JSON file (default: diagnose_config.json)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as structured JSON",
    )
    args = parser.parse_args()

    try:
        results = run_diagnostics(args.config)
    except Exception as exc:
        print(f"Diagnostics Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(format_text_report(results))

    any_failed = any(
        r.dns_status == "FAIL" or r.tls_status == "FAIL" or r.http_status == "FAIL"
        for r in results
    )
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
