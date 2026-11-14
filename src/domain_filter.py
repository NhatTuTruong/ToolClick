"""Lọc quảng cáo / click theo domain cho phép và domain bỏ qua."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from .sponsored_parser import SponsoredResult


def normalize_domain(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s:
        return ""
    if "://" in s:
        try:
            s = urlparse(s).netloc or s
        except Exception:
            pass
    s = s.split("/")[0].split("?")[0]
    if s.startswith("www."):
        s = s[4:]
    return s


def parse_domains_text(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in text.replace(",", "\n").splitlines():
        d = normalize_domain(line)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def parse_domains_env(value: str | None) -> list[str]:
    if not value or not value.strip():
        return []
    return parse_domains_text(value)


def _host_from_display(display: str) -> str:
    t = (display or "").strip().lower()
    if not t:
        return ""
    t = t.split("›")[0].split("»")[0].strip()
    t = re.sub(r"\s+", " ", t)
    if "://" in t:
        try:
            return normalize_domain(urlparse(t).netloc)
        except Exception:
            pass
    token = t.split()[0] if t.split() else t
    return normalize_domain(token)


def _hosts_from_href(href: str) -> set[str]:
    hosts: set[str] = set()
    if not href:
        return hosts
    try:
        parsed = urlparse(href)
        if parsed.netloc:
            hosts.add(normalize_domain(parsed.netloc))
        qs = parse_qs(parsed.query)
        for key in ("adurl", "url", "q", "u"):
            for val in qs.get(key, []):
                decoded = unquote(val)
                if not decoded:
                    continue
                if "://" not in decoded:
                    decoded = "https://" + decoded.lstrip("/")
                pu = urlparse(decoded)
                if pu.netloc:
                    hosts.add(normalize_domain(pu.netloc))
    except Exception:
        pass
    return {h for h in hosts if h}


def sponsored_hosts(item: SponsoredResult) -> set[str]:
    hosts = _hosts_from_href(item.destination_url)
    dh = _host_from_display(item.display_url)
    if dh:
        hosts.add(dh)
    return hosts


def host_matches_allowed(host: str, allowed: set[str]) -> bool:
    if not host or not allowed:
        return False
    h = normalize_domain(host)
    for dom in allowed:
        if h == dom or h.endswith("." + dom):
            return True
    return False


def sponsored_matches_domains(item: SponsoredResult, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    allowed = {normalize_domain(d) for d in allowed_domains if normalize_domain(d)}
    if not allowed:
        return True
    for host in sponsored_hosts(item):
        if host_matches_allowed(host, allowed):
            return True
    return False


def sponsored_matches_skip(item: SponsoredResult, skip_domains: list[str]) -> bool:
    if not skip_domains:
        return False
    blocked = {normalize_domain(d) for d in skip_domains if normalize_domain(d)}
    if not blocked:
        return False
    for host in sponsored_hosts(item):
        if host_matches_allowed(host, blocked):
            return True
    return False


def filter_sponsored_for_click(
    sponsored: list[SponsoredResult],
    allowed_domains: list[str],
    skip_domains: list[str] | None = None,
) -> list[SponsoredResult]:
    out = list(sponsored)
    if allowed_domains:
        out = [s for s in out if sponsored_matches_domains(s, allowed_domains)]
    skip = skip_domains or []
    if skip:
        out = [s for s in out if not sponsored_matches_skip(s, skip)]
    return out
