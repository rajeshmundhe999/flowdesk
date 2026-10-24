"""Unit tests for the diagnostic helper utility."""

import json
from unittest.mock import MagicMock, patch

from diagnose import (
    CheckResult,
    check_dns,
    check_http,
    check_tls,
    format_text_report,
    run_diagnostics,
)


def test_check_dns_success():
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("1.1.1.1", 443))]
        status, latency, info = check_dns("one.one.one.one", timeout=1.0)
        assert status == "PASS"
        assert "1.1.1.1" in info
        assert latency >= 0.0


def test_check_dns_failure():
    with patch("socket.getaddrinfo", side_effect=Exception("Name or service not known")):
        status, latency, info = check_dns("invalid-nonexistent-domain.xyz", timeout=1.0)
        assert status == "FAIL"
        assert "DNS error" in info


def test_check_tls_success():
    mock_ssock = MagicMock()
    mock_ssock.version.return_value = "TLSv1.3"
    mock_ssock.cipher.return_value = ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)

    with patch("socket.create_connection"), patch("ssl.create_default_context") as mock_ctx:
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
        status, latency, info = check_tls("example.com", timeout=1.0)
        assert status == "PASS"
        assert "TLSv1.3" in info


def test_check_http_success():
    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen") as mock_url:
        mock_url.return_value.__enter__.return_value = mock_resp
        status, latency, info = check_http("https://example.com", timeout=1.0)
        assert status == "PASS"
        assert "HTTP 200" in info


def test_run_diagnostics_reads_config(tmp_path):
    cfg_file = tmp_path / "test_cfg.json"
    cfg_file.write_text(
        json.dumps({
            "timeout_seconds": 1.0,
            "latency_warn_threshold_ms": 200.0,
            "endpoints": [
                {"name": "Mock Test", "host": "test.local", "url": "https://test.local"}
            ],
        }),
        encoding="utf-8",
    )

    with patch("diagnose.check_dns", return_value=("PASS", 15.0, "Resolved")), \
         patch("diagnose.check_tls", return_value=("PASS", 35.0, "TLSv1.3")), \
         patch("diagnose.check_http", return_value=("PASS", 50.0, "HTTP 200")):
        results = run_diagnostics(cfg_file)
        assert len(results) == 1
        assert results[0].target_name == "Mock Test"
        assert not results[0].is_slow


def test_format_text_report_flags_slow_warning():
    slow_result = CheckResult(
        target_name="Slow Gateway",
        host="slow.example.com",
        dns_status="PASS",
        dns_latency_ms=10.0,
        dns_info="10.0.0.1",
        tls_status="PASS",
        tls_latency_ms=450.0,
        tls_info="TLSv1.2",
        http_status="PASS",
        http_latency_ms=600.0,
        http_info="HTTP 200",
        is_slow=True,
    )
    report = format_text_report([slow_result], warn_threshold=500.0)
    assert "[WARN: SLOW]" in report
    assert "Elevated latency detected" in report
