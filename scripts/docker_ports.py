from __future__ import annotations

import csv
import errno
import io
import json
import os
import re
import socket
import subprocess

from pathlib import Path
from typing import NamedTuple


NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
IS_WINDOWS = os.name == "nt"

MAX_RANGE = 1000

# состояния, которые мешают запуску
BAD_STATES = ("busy", "reserved", "duplicate")

WILDCARDS = ("", "0.0.0.0", "::")


class PortMapping(NamedTuple):
    service: str
    host_ip: str        # "" = все интерфейсы
    port: int           # порт на хосте
    target: str         # порт в контейнере
    protocol: str       # tcp | udp


class PortStatus(NamedTuple):
    mapping: PortMapping
    state: str          # free | mine | busy | reserved | duplicate | unknown
    owner: str


class PortReport(NamedTuple):
    project: str
    statuses: list
    notes: list


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _first_line(text) -> str:
    for line in str(text).splitlines():
        if line.strip():
            return line.strip()
    return str(text).strip()


def _run(command, timeout, cwd=None):
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {command[0]}") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timed out: {' '.join(command[:3])}") from None


# ---------------------------------------------------------
# 1. Ports from the Compose file
# ---------------------------------------------------------

def _expand(published: str) -> list[int]:
    """'8080' -> [8080], '8000-8003' -> [8000..8003]."""
    published = published.strip()

    if "-" in published:
        left, _, right = published.partition("-")
        start, end = int(left), int(right)
        if end < start or end - start >= MAX_RANGE:
            raise ValueError(published)
        ports = list(range(start, end + 1))
    else:
        ports = [int(published)]

    if any(not 1 <= p <= 65535 for p in ports):
        raise ValueError(published)

    return ports


def _parse_short(text: str) -> dict:
    """Запасной разбор короткой записи: '127.0.0.1:8080:80/tcp'."""
    spec, _, protocol = text.partition("/")
    parts = spec.split(":")

    if len(parts) == 1:
        return {"target": parts[0], "published": "", "protocol": protocol or "tcp"}

    return {
        "host_ip": ":".join(parts[:-2]).strip("[]"),
        "published": parts[-2],
        "target": parts[-1],
        "protocol": protocol or "tcp",
    }


def parse_config(data: dict):
    """Вывод `docker compose config --format json` -> (проект, порты, заметки)."""
    project = str(data.get("name") or "")
    mappings: list[PortMapping] = []
    notes: list[str] = []

    for service, spec in (data.get("services") or {}).items():
        for item in (spec or {}).get("ports") or []:
            if isinstance(item, str):
                item = _parse_short(item)
            if not isinstance(item, dict):
                continue

            target = str(item.get("target", "") or "")
            published = str(item.get("published", "") or "").strip()
            protocol = str(item.get("protocol", "tcp") or "tcp").lower()
            host_ip = str(item.get("host_ip", "") or "")

            if not published:
                notes.append(
                    f"{service}: container port {target or '?'} gets a random "
                    "host port, not checked."
                )
                continue

            try:
                ports = _expand(published)
            except ValueError:
                notes.append(f"{service}: cannot read port '{published}'.")
                continue

            for port in ports:
                mappings.append(
                    PortMapping(service, host_ip, port, target, protocol)
                )

    return project, mappings, notes


def get_compose_ports(compose_file):
    compose_file = Path(compose_file)

    if not compose_file.is_file():
        raise RuntimeError(f"Compose file not found: {compose_file}")

    result = _run(
        ["docker", "compose", "-f", str(compose_file), "config", "--format", "json"],
        timeout=30,
        cwd=str(compose_file.parent),
    )

    if result.returncode != 0:
        raise RuntimeError(
            _first_line(result.stderr or result.stdout)
            or "docker compose config failed"
        )

    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError("Unexpected output of 'docker compose config'.") from None

    return parse_config(data)


# ---------------------------------------------------------
# 2. Is the port free? (bind test, nothing is sent over the network)
# ---------------------------------------------------------

def probe_bind(host_ip: str, port: int, protocol: str = "tcp") -> str:
    """free | busy | reserved | unknown"""
    address = host_ip or "0.0.0.0"
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    kind = socket.SOCK_DGRAM if protocol == "udp" else socket.SOCK_STREAM

    try:
        sock = socket.socket(family, kind)
    except OSError:
        return "unknown"

    try:
        # как у docker-proxy; на Windows SO_REUSEADDR разрешил бы двойной bind
        if not IS_WINDOWS:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind((address, port))
        return "free"

    except OSError as error:
        code = getattr(error, "winerror", None) or error.errno

        if code in (errno.EADDRINUSE, 10048):
            return "busy"

        # WSAEACCES: порт в зарезервированном диапазоне Windows
        # или его держит процесс с SO_EXCLUSIVEADDRUSE
        if IS_WINDOWS and code == 10013:
            return "reserved"

        return "unknown"

    finally:
        sock.close()


# ---------------------------------------------------------
# 3. Who holds the port?
# ---------------------------------------------------------

_PORT_RE = re.compile(
    r"(?:(?P<ip>\[[^\]]+\]|[\d.]+):)?(?P<start>\d+)(?:-(?P<end>\d+))?"
    r"->(?P<target>\d+)(?:-\d+)?/(?P<proto>tcp|udp)"
)


def parse_docker_ps(text: str) -> dict:
    """
    Строки вида 'name|project|0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp'
    -> {(порт, протокол): [(контейнер, проект), ...]}
    """
    owners: dict = {}

    for line in text.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue

        name, project, ports = (p.strip() for p in parts)

        for match in _PORT_RE.finditer(ports):
            start = int(match["start"])
            end = int(match["end"] or start)

            if end - start > MAX_RANGE:
                continue

            for port in range(start, end + 1):
                bucket = owners.setdefault((port, match["proto"]), [])
                entry = (name, project)
                if entry not in bucket:
                    bucket.append(entry)

    return owners


def docker_published_ports() -> dict:
    result = _run(
        [
            "docker", "ps", "--format",
            '{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Ports}}',
        ],
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(_first_line(result.stderr) or "docker ps failed")

    return parse_docker_ps(result.stdout)


def parse_netstat(text: str, protocol: str = "tcp") -> dict:
    """{порт: {PID, ...}} для слушающих сокетов. Не зависит от языка Windows."""
    proto = protocol.upper()
    result: dict = {}

    for line in text.splitlines():
        parts = line.split()

        if len(parts) < 4 or parts[0].upper() != proto:
            continue

        local, foreign, pid_text = parts[1], parts[2], parts[-1]

        if proto == "TCP" and foreign not in ("0.0.0.0:0", "[::]:0", "*:*"):
            continue

        port_text = local.rsplit(":", 1)[-1]

        if pid_text.isdigit() and port_text.isdigit():
            result.setdefault(int(port_text), set()).add(int(pid_text))

    return result


def parse_excluded_ranges(text: str) -> list[tuple[int, int]]:
    ranges = []

    for line in text.splitlines():
        match = re.match(r"^\s*(\d+)\s+(\d+)\s*\*?\s*$", line)
        if match:
            ranges.append((int(match.group(1)), int(match.group(2))))

    return ranges


def _windows_listeners() -> dict:
    result = _run(["netstat", "-ano"], timeout=15)
    return {
        "tcp": parse_netstat(result.stdout, "tcp"),
        "udp": parse_netstat(result.stdout, "udp"),
    }


def _windows_excluded_ranges(protocol: str) -> list[tuple[int, int]]:
    try:
        result = _run(
            ["netsh", "interface", "ipv4", "show", "excludedportrange",
             f"protocol={protocol}"],
            timeout=10,
        )
    except RuntimeError:
        return []

    return parse_excluded_ranges(result.stdout)


def _process_name(pid: int) -> str:
    try:
        result = _run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            timeout=10,
        )
    except RuntimeError:
        return ""

    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2:
            return row[0]

    return ""


# ---------------------------------------------------------
# 4. Putting it together
# ---------------------------------------------------------

def _overlap(a: str, b: str) -> bool:
    return a == b or a in WILDCARDS or b in WILDCARDS


def check_ports(compose_file) -> PortReport:
    project, mappings, notes = get_compose_ports(compose_file)
    notes = list(notes)

    try:
        docker_map = docker_published_ports()
    except RuntimeError as error:
        docker_map = {}
        notes.append(f"Container owners unknown: {_first_line(error)}")

    listeners = None
    excluded: dict = {}
    names: dict = {}
    seen: dict = {}
    statuses: list[PortStatus] = []

    for m in sorted(mappings, key=lambda m: (m.port, m.protocol, m.service)):
        key = (m.port, m.protocol)

        # два сервиса одного проекта хотят один и тот же порт
        clash = next(
            (other for other in seen.get(key, []) if _overlap(other.host_ip, m.host_ip)),
            None,
        )
        seen.setdefault(key, []).append(m)

        if clash:
            statuses.append(PortStatus(
                m, "duplicate", f'also published by service "{clash.service}"'
            ))
            continue

        state = probe_bind(m.host_ip, m.port, m.protocol)

        if state == "free":
            statuses.append(PortStatus(m, "free", ""))
            continue

        # 1) контейнер, который публикует этот порт
        owners = docker_map.get(key, [])
        if owners:
            foreign = [o for o in owners if o[1] != project]

            if foreign:
                name, other_project = foreign[0]
                owner = f'container "{name}"'
                if other_project:
                    owner += f' (project "{other_project}")'
                if len(foreign) > 1:
                    owner += f" and {len(foreign) - 1} more"
                statuses.append(PortStatus(m, "busy", owner))
            else:
                statuses.append(PortStatus(
                    m, "mine", f'this project: container "{owners[0][0]}"'
                ))
            continue

        # 2) обычный процесс Windows
        if IS_WINDOWS:
            if listeners is None:
                try:
                    listeners = _windows_listeners()
                except RuntimeError:
                    listeners = {"tcp": {}, "udp": {}}

            pids = sorted(listeners.get(m.protocol, {}).get(m.port, ()))

            if pids:
                parts = []
                for pid in pids[:3]:
                    if pid not in names:
                        names[pid] = _process_name(pid) or "unknown"
                    parts.append(f"{names[pid]} (PID {pid})")
                statuses.append(PortStatus(m, "busy", ", ".join(parts)))
                continue

            if state == "reserved":
                if m.protocol not in excluded:
                    excluded[m.protocol] = _windows_excluded_ranges(m.protocol)

                span = next(
                    ((a, b) for a, b in excluded[m.protocol] if a <= m.port <= b),
                    None,
                )
                owner = (
                    f"reserved by Windows (excluded range {span[0]}-{span[1]})"
                    if span else
                    "access denied: reserved by Windows or held exclusively"
                )
                statuses.append(PortStatus(m, "reserved", owner))
                continue

        if state == "busy":
            statuses.append(PortStatus(
                m, "busy", "another process (could not identify it)"
            ))
        else:
            statuses.append(PortStatus(m, "unknown", "could not test this port"))

    return PortReport(project, statuses, notes)


def conflicts(report: PortReport) -> list[PortStatus]:
    return [s for s in report.statuses if s.state in BAD_STATES]


def summarize(report: PortReport):
    """-> (уровень ok|warn|error, короткий текст для строки статуса)."""
    total = len(report.statuses)

    if total == 0:
        text = "Ports: this project publishes no fixed host ports."
        return "ok", text

    bad = conflicts(report)

    if bad:
        shown = [
            f"{s.mapping.port}/{s.mapping.protocol} busy: {s.owner}"
            if s.state == "busy" else
            f"{s.mapping.port}/{s.mapping.protocol} {s.state}: {s.owner}"
            for s in bad[:3]
        ]
        extra = f" (+{len(bad) - 3} more)" if len(bad) > 3 else ""
        return "error", "Ports: " + "; ".join(shown) + extra

    unknown = sum(1 for s in report.statuses if s.state == "unknown")
    mine = sum(1 for s in report.statuses if s.state == "mine")

    if unknown:
        return "warn", f"Ports: {total} mapped · {unknown} could not be tested"

    if mine:
        return "ok", f"Ports: {total} mapped · {mine} used by this project, the rest free"

    return "ok", f"Ports: {total} mapped · all free"