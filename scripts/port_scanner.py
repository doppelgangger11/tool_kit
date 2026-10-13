import ipaddress
import queue
import re
import socket
import threading
import time


# ---------------------------------------------------------
# Limits (чтобы случайно не устроить сканирование на пол-интернета)
# ---------------------------------------------------------

MAX_HOSTS = 1024            # /22
MAX_PROBES = 1_000_000      # хосты x порты
MAX_WORKERS = 500

COMMON_PORTS = sorted(set([
    20, 21, 22, 23, 25, 53, 67, 68, 69, 80, 88, 110, 111, 119, 123, 135, 137,
    138, 139, 143, 161, 162, 389, 443, 445, 465, 500, 514, 515, 587, 631, 636,
    873, 993, 995, 1080, 1433, 1521, 1723, 2049, 2375, 2376, 3000, 3128, 3306,
    3389, 4369, 5000, 5432, 5433, 5555, 5601, 5672, 5900, 5984, 6379, 6443,
    7001, 8000, 8008, 8080, 8081, 8088, 8443, 8793, 8888, 8974, 9000, 9042,
    9090, 9092, 9200, 9300, 11211, 15672, 27017,
]))

# имена для портов, которые встречаются в разработке и часто путаются
SERVICE_NAMES = {
    1433: "mssql", 1521: "oracle", 2375: "docker (unencrypted!)",
    2376: "docker-tls", 3306: "mysql", 3389: "rdp", 5000: "http-dev",
    5432: "postgresql", 5433: "postgresql-alt", 5555: "flower",
    5601: "kibana", 5672: "rabbitmq", 6379: "redis", 8080: "http-alt",
    8793: "airflow-worker-logs", 8974: "airflow-scheduler-health",
    9092: "kafka", 9200: "elasticsearch", 15672: "rabbitmq-ui",
    27017: "mongodb",
}


# ---------------------------------------------------------
# Parsing
# ---------------------------------------------------------

def _check_port(port: int) -> int:
    if not 1 <= port <= 65535:
        raise ValueError(f"Port out of range (1-65535): {port}")
    return port


def parse_ports(text: str) -> list[int]:
    """'22, 80, 8000-8100' -> отсортированный список без повторов."""
    ports = set()

    for token in re.split(r"[,\s;]+", text.strip()):
        if not token:
            continue

        if "-" in token:
            left, _, right = token.partition("-")
            if not (left.isdigit() and right.isdigit()):
                raise ValueError(f"Invalid port range: {token}")

            start, end = int(left), int(right)
            if start > end:
                raise ValueError(f"Invalid port range: {token}")

            ports.update(range(_check_port(start), _check_port(end) + 1))

        elif token.isdigit():
            ports.add(_check_port(int(token)))

        else:
            raise ValueError(f"Invalid port: {token}")

    if not ports:
        raise ValueError("Enter at least one port.")

    return sorted(ports)


def preset_ports(name: str) -> list[int]:
    if name.startswith("Common"):
        return list(COMMON_PORTS)
    if name.startswith("Well-known"):
        return list(range(1, 1025))
    if name.startswith("All"):
        return list(range(1, 65536))
    raise ValueError(f"Unknown preset: {name}")


def _resolve(name: str) -> str:
    try:
        return socket.gethostbyname(name)
    except OSError:
        raise ValueError(f"Cannot resolve host: {name}") from None


def parse_targets(text: str) -> list[str]:
    """
    Понимает через запятую/пробел:
      192.168.1.5            один адрес
      my-server              имя хоста
      192.168.1.0/24         подсеть
      192.168.1.10-50        диапазон
      192.168.1.10-192.168.1.50
    Только IPv4.
    """
    hosts: list[str] = []

    for token in re.split(r"[,\s;]+", text.strip()):
        if not token:
            continue

        if "/" in token:
            try:
                net = ipaddress.ip_network(token, strict=False)
            except ValueError:
                raise ValueError(f"Invalid network: {token}") from None

            if net.version != 4:
                raise ValueError("Only IPv4 is supported.")

            if net.num_addresses > MAX_HOSTS + 2:
                raise ValueError(
                    f"{token} is too large (limit {MAX_HOSTS} hosts)."
                )

            found = list(net.hosts()) or [net.network_address]
            hosts.extend(str(ip) for ip in found)
            continue

        if "-" in token:
            left, _, right = token.partition("-")
            try:
                start = ipaddress.IPv4Address(left)
            except ValueError:
                start = None   # это имя хоста с дефисом, например my-pc

            if start is not None:
                try:
                    if right.isdigit() and int(right) <= 255:
                        prefix = left.rsplit(".", 1)[0]
                        end = ipaddress.IPv4Address(f"{prefix}.{right}")
                    else:
                        end = ipaddress.IPv4Address(right)
                except ValueError:
                    raise ValueError(f"Invalid range: {token}") from None

                if int(end) < int(start):
                    raise ValueError(f"Invalid range: {token}")

                if int(end) - int(start) + 1 > MAX_HOSTS:
                    raise ValueError(
                        f"{token} is too large (limit {MAX_HOSTS} hosts)."
                    )

                hosts.extend(
                    str(ipaddress.IPv4Address(n))
                    for n in range(int(start), int(end) + 1)
                )
                continue

        try:
            hosts.append(str(ipaddress.IPv4Address(token)))
        except ValueError:
            hosts.append(_resolve(token))

    hosts = list(dict.fromkeys(hosts))

    if not hosts:
        raise ValueError("Enter a host, a network (192.168.1.0/24) or a range.")

    if len(hosts) > MAX_HOSTS:
        raise ValueError(f"Too many hosts ({len(hosts)}), limit is {MAX_HOSTS}.")

    return hosts


# ---------------------------------------------------------
# Scope safety
# ---------------------------------------------------------

def is_local_target(host: str) -> bool:
    ip = ipaddress.ip_address(host)
    return ip.is_private or ip.is_loopback or ip.is_link_local


def has_public(hosts: list[str]) -> bool:
    return any(not is_local_target(h) for h in hosts)


def check_scope(hosts: list[str], allow_public: bool = False):
    """Возвращает текст ошибки или None."""
    public = [h for h in hosts if not is_local_target(h)]

    if not public:
        return None

    if not allow_public:
        return (
            f"{public[0]} is not a local or private address.\n\n"
            "By default only localhost and private networks "
            "(10.x, 172.16-31.x, 192.168.x) can be scanned."
        )

    if len(hosts) > 1:
        return "Public addresses: only a single host can be scanned."

    return None


def local_network() -> str:
    """Подсеть /24 этого компьютера. Пакеты не отправляются."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("10.255.255.255", 1))
            ip = sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"

    if ip.startswith("127."):
        return "127.0.0.1"

    return str(ipaddress.ip_network(f"{ip}/24", strict=False))


# ---------------------------------------------------------
# Scanning
# ---------------------------------------------------------

def service_name(port: int) -> str:
    if port in SERVICE_NAMES:
        return SERVICE_NAMES[port]
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return ""


def _clean_banner(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    line = lines[0] if lines else ""
    line = "".join(ch if ch.isprintable() else " " for ch in line).strip()
    return line[:100]


def probe(host: str, port: int, timeout: float, grab_banner: bool = False):
    """TCP connect. Возвращает (открыт ли порт, баннер)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        if sock.connect_ex((host, port)) != 0:
            return False, ""

        banner = ""
        if grab_banner:
            # пассивно: только читаем то, что сервис сам присылает
            # (SSH, FTP, SMTP), ничего не отправляя
            try:
                sock.settimeout(1.0)
                banner = _clean_banner(sock.recv(256))
            except OSError:
                pass

        return True, banner

    except OSError:
        return False, ""

    finally:
        sock.close()


class Scanner:
    """
    Многопоточный TCP connect-сканер.
    results   - очередь (host, port, service, banner) для интерфейса
    done/total - прогресс, читать можно из любого потока
    """

    def __init__(self, hosts, ports, timeout=0.5, workers=200, banners=False):
        self.hosts = list(hosts)
        self.ports = list(ports)
        self.timeout = timeout
        self.workers = max(1, min(int(workers), MAX_WORKERS))
        self.banners = banners

        self.total = len(self.hosts) * len(self.ports)
        self.done = 0
        self.results: queue.Queue = queue.Queue()

        self.stop_event = threading.Event()
        self.finished = threading.Event()

        self.started_at = 0.0
        self.elapsed = 0.0

        self._lock = threading.Lock()
        self._pairs = ((h, p) for h in self.hosts for p in self.ports)
        self._alive = 0

    @property
    def stopped(self) -> bool:
        return self.stop_event.is_set()

    def start(self):
        self.started_at = time.monotonic()

        count = min(self.workers, max(1, self.total))
        self._alive = count

        if self.total == 0:
            self.elapsed = 0.0
            self.finished.set()
            return

        for _ in range(count):
            threading.Thread(target=self._worker, daemon=True).start()

    def stop(self):
        self.stop_event.set()

    def _next(self):
        with self._lock:
            if self.stop_event.is_set():
                return None
            return next(self._pairs, None)

    def _worker(self):
        try:
            while True:
                pair = self._next()
                if pair is None:
                    break

                host, port = pair
                is_open, banner = probe(host, port, self.timeout, self.banners)

                with self._lock:
                    self.done += 1

                if is_open:
                    self.results.put((host, port, service_name(port), banner))
        finally:
            with self._lock:
                self._alive -= 1
                last = self._alive == 0

            if last:
                self.elapsed = time.monotonic() - self.started_at
                self.finished.set()
