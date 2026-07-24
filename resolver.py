"""
GitHub 加速器 - DNS 解析模块
使用公共 DNS 服务器解析 GitHub 域名，获取最优 IP
"""

import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import dns.resolver

# GitHub 需要加速的域名
GITHUB_DOMAINS = [
    "github.com",
    "github.global.ssl.fastly.net",
    "assets-cdn.github.com",
    "raw.githubusercontent.com",
    "gist.githubusercontent.com",
    "codeload.github.com",
    "api.github.com",
]

# 公共 DNS 服务器
DNS_SERVERS = {
    "Cloudflare": ["1.1.1.1", "1.0.0.1"],
    "Google": ["8.8.8.8", "8.8.4.4"],
    "AliDNS": ["223.5.5.5", "223.6.6.6"],
    "TencentDNS": ["119.29.29.29"],
    "BaiduDNS": ["180.76.76.76"],
    "114DNS": ["114.114.114.114"],
}


@dataclass
class IpResult:
    """IP 解析结果"""
    ip: str
    latency_ms: float  # DNS 查询延迟
    source: str  # 来源 DNS 服务器


@dataclass
class DomainResult:
    """域名解析结果"""
    domain: str
    best_ip: Optional[str]
    all_ips: List[IpResult]


def query_dns(domain: str, dns_server: str, timeout: float = 3.0) -> Tuple[str, float]:
    """
    向指定 DNS 服务器查询域名
    返回 (ip地址, 延迟毫秒) 或抛出异常
    """
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [dns_server]
    resolver.timeout = timeout
    resolver.lifetime = timeout

    start = time.time()
    try:
        answers = resolver.resolve(domain, "A")
        latency = (time.time() - start) * 1000
        ips = [str(rdata) for rdata in answers]
        if ips:
            return ips[0], latency
    except Exception:
        pass
    raise Exception(f"DNS query failed for {domain} via {dns_server}")


def resolve_domain(domain: str, cf_worker_url: Optional[str] = None) -> DomainResult:
    """
    解析单个域名，从所有 DNS 服务器获取结果，返回延迟最低的 IP
    """
    all_ips: List[IpResult] = []

    # 收集所有 DNS 服务器的解析结果
    tasks: List[Tuple[str, str]] = []
    for provider, servers in DNS_SERVERS.items():
        for server in servers:
            tasks.append((server, provider))

    # 如果配置了 Cloudflare Worker，添加到任务列表
    if cf_worker_url:
        tasks.append(("cf_worker", "CloudflareWorker"))

    def query_task(args: Tuple[str, str]) -> Optional[IpResult]:
        server, provider = args
        try:
            if server == "cf_worker":
                ip, latency = query_cf_worker(domain, cf_worker_url)
            else:
                ip, latency = query_dns(domain, server)
            return IpResult(ip=ip, latency_ms=latency, source=provider)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(query_task, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_ips.append(result)

    # 按延迟排序，去重
    seen_ips = set()
    unique_ips = []
    for ip_result in sorted(all_ips, key=lambda x: x.latency_ms):
        if ip_result.ip not in seen_ips:
            seen_ips.add(ip_result.ip)
            unique_ips.append(ip_result)

    best_ip = unique_ips[0].ip if unique_ips else None
    return DomainResult(domain=domain, best_ip=best_ip, all_ips=unique_ips)


def query_cf_worker(domain: str, worker_url: str) -> Tuple[str, float]:
    """
    通过 Cloudflare Worker 查询 DNS
    Worker 应该返回 JSON: {"ip": "x.x.x.x", "latency_ms": 123}
    """
    import requests

    start = time.time()
    resp = requests.get(
        f"{worker_url}?domain={domain}",
        timeout=5,
        headers={"User-Agent": "GitHub-Accelerator/1.0"}
    )
    latency = (time.time() - start) * 1000

    if resp.status_code == 200:
        data = resp.json()
        ip = data.get("ip")
        if ip:
            return ip, latency

    raise Exception("CF Worker query failed")


def resolve_all_domains(cf_worker_url: Optional[str] = None) -> Dict[str, DomainResult]:
    """
    解析所有 GitHub 域名
    返回 {域名: 解析结果}
    """
    results: Dict[str, DomainResult] = {}
    for domain in GITHUB_DOMAINS:
        results[domain] = resolve_domain(domain, cf_worker_url)
    return results


def test_ip_latency(ip: str, port: int = 443, timeout: float = 3.0) -> Optional[float]:
    """
    测试到 IP 的 TCP 连接延迟（毫秒）
    """
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        latency = (time.time() - start) * 1000
        sock.close()
        return latency
    except Exception:
        return None


def test_and_rank_ips(ips: List[str], port: int = 443) -> List[Tuple[str, float]]:
    """
    测试多个 IP 的实际连接延迟，返回排序后的列表
    """
    results = []

    def test_one(ip: str) -> Optional[Tuple[str, float]]:
        latency = test_ip_latency(ip, port)
        return (ip, latency) if latency else None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(test_one, ip) for ip in ips]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return sorted(results, key=lambda x: x[1])
