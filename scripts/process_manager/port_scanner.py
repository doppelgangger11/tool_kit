"""
Определение занятых портов и конфликтов через psutil.

psutil.net_connections() под Windows обычно требует прав администратора
для получения полного списка соединений *других* процессов. Если прав
не хватает, функции просто вернут None/пустой результат вместо падения -
это осознанный компромисс, чтобы GUI не падал.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class PortOwner:
    pid: int
    process_name: str
    cmdline: str


def find_process_on_port(port: int) -> Optional[PortOwner]:
    """Вернуть информацию о процессе, слушающем заданный порт, либо None."""
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        return None

    for conn in connections:
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            if not conn.pid:
                continue
            try:
                proc = psutil.Process(conn.pid)
                return PortOwner(
                    pid=conn.pid,
                    process_name=proc.name(),
                    cmdline=" ".join(proc.cmdline()),
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return PortOwner(pid=conn.pid, process_name="<unknown>", cmdline="")
    return None


def is_port_free(port: int) -> bool:
    return find_process_on_port(port) is None


@dataclass
class ListeningPort:
    port: int
    pid: int
    process_name: str
    cmdline: str
    is_ipv6: bool


def list_all_listening_ports() -> list[ListeningPort]:
    """
    Просканировать ВСЮ систему и вернуть все порты, на которых сейчас
    кто-то слушает (LISTEN) - не только те, что зарегистрированы как
    проекты в этом инструменте. По сути человекочитаемая замена
    `netstat -ano | findstr LISTENING`.

    Один и тот же порт может встретиться дважды (IPv4 + IPv6) - оставляем
    обе записи, но помечаем is_ipv6, чтобы не путать в UI.
    """
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        return []

    # кэш имён процессов, чтобы не дёргать psutil.Process на каждый porт
    # одного и того же PID по нескольку раз
    proc_cache: dict[int, tuple[str, str]] = {}
    result: list[ListeningPort] = []

    for conn in connections:
        if conn.status != psutil.CONN_LISTEN or not conn.laddr:
            continue

        if conn.pid is None:
            # PID не удалось определить - обычно это чужой процесс,
            # на который не хватает прав (нужен админ), либо сокет
            # в другом неймспейсе. Раньше такие записи тихо пропускались -
            # это плохо: порт занят, а пользователь этого не видит и не
            # понимает, почему запуск падает с "address already in use".
            # Показываем как есть, с пометкой.
            result.append(ListeningPort(
                port=conn.laddr.port,
                pid=0,
                process_name="<нет доступа, нужны права администратора>",
                cmdline="",
                is_ipv6=":" in conn.laddr.ip,
            ))
            continue

        if conn.pid not in proc_cache:
            try:
                proc = psutil.Process(conn.pid)
                proc_cache[conn.pid] = (proc.name(), " ".join(proc.cmdline()))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_cache[conn.pid] = ("<unknown>", "")

        name, cmdline = proc_cache[conn.pid]
        is_ipv6 = ":" in conn.laddr.ip

        result.append(ListeningPort(
            port=conn.laddr.port,
            pid=conn.pid,
            process_name=name,
            cmdline=cmdline,
            is_ipv6=is_ipv6,
        ))

    # убираем полные дубликаты (бывает, что одна и та же пара pid+port
    # приходит несколько раз из-за нескольких сокетов) и сортируем по порту
    seen = set()
    deduped = []
    for item in result:
        key = (item.port, item.pid, item.is_ipv6)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda x: x.port)
    return deduped


def kill_process(pid: int, force: bool = True) -> None:
    """
    Убить произвольный процесс по PID - используется для "чужих" процессов
    из общесистемного списка портов, которыми Localhost Manager не управляет
    напрямую (то есть их нет в ProcessManager, только PID из psutil).
    """
    import subprocess
    import sys

    if sys.platform.startswith("win"):
        args = ["taskkill", "/T", "/PID", str(pid)]
        if force:
            args.insert(1, "/F")
        subprocess.run(args, capture_output=True)
    else:
        proc = psutil.Process(pid)
        proc.kill() if force else proc.terminate()
