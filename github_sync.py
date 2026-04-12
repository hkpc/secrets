import os
import time
import requests
from datetime import datetime, timezone

SAVE_PATH = "filter_subs_24h.txt"
WITHIN_HOURS = 24

HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "Mozilla/5.0"}
MY_TOKEN = os.getenv("GITHUB_TOKEN")
if MY_TOKEN:
    HEADERS["Authorization"] = f"token {MY_TOKEN}"

# 关键词：用于“先命中候选”
TARGET_KEYWORDS = [
    "subscribes.txt",
    "clash.yaml",
    "proxies.yaml",
    "v2ray.txt",
    "nodes.txt",
    "proxies",
    "clash",
    "v2ray",
    "node",
]

# 结构性特征：用于“排除误报”
# 只要命中其一就认为更像节点/配置文件
STRUCTURE_HINTS = [
    # Clash / Mihomo YAML
    "proxies:",
    "proxy-groups:",
    "rules:",
    "rule-providers:",
    "domain-suffix",
    "domain-keyword",
    "port: ",
    "- name:",

    # V2Ray / Xray JSON/YAML
    "outbounds:",
    "inbounds:",
    "routing:",
    "transport:",

    # 订阅链接（常见于文本节点列表）
    "ss://",
    "vmess://",
    "trojan://",
    "vless://",
]

CANDIDATE_SUFFIXES = (".txt", ".yaml", ".yml")

MAX_RAW_BYTES = 250_000
TIMEOUT = 20


def github_get(url, params=None, timeout=TIMEOUT, max_retries=5):
    for _ in range(max_retries):
        res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        if res.status_code in (404, 422):
            return None
        if res.status_code == 403:
            reset = res.headers.get("X-RateLimit-Reset")
            if reset:
                wait_s = max(1, int(reset) - int(time.time())) + 1
                print(f"[!] 403限流，等待 {wait_s}s 后重试...")
                time.sleep(wait_s)
                continue
            time.sleep(10)
            continue
        if res.status_code != 200:
            time.sleep(2)
            continue
        return res.json()
    return None


def within_last_hours(dt_str: str, hours: int) -> bool:
    if not dt_str:
        return False
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() <= hours * 3600


def is_candidate_by_filename(fname: str) -> bool:
    if not fname:
        return False
    lower = fname.lower()
    return any(lower.endswith(suf) for suf in CANDIDATE_SUFFIXES)


def download_snippet(raw_url: str) -> str:
    r = requests.get(raw_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT, stream=True)
    if r.status_code != 200:
        return ""
    content = b""
    for chunk in r.iter_content(chunk_size=4096):
        if not chunk:
            break
        content += chunk
        if len(content) >= MAX_RAW_BYTES:
            break
    return content.decode("utf-8", errors="ignore").lower()


def raw_content_matches(raw_url: str) -> bool:
    text = download_snippet(raw_url)
    if not text:
        return False

    # 第一步：关键词先命中
    if not any(kw.lower() in text for kw in TARGET_KEYWORDS):
        return False

    # 第二步：结构性特征必须命中（防止像 Bug Bounty Resources 这种误报）
    if not any(hint.lower() in text for hint in STRUCTURE_HINTS):
        return False

    return True


def main():
    print(f"[*] 扫描 public gists；仅保留 {WITHIN_HOURS}h 内更新，并做结构性校验（防止误报）")

    all_raw_urls = set()
    page = 1
    per_page = 100
    api_url = "https://api.github.com/gists/public"

    while True:
        data = github_get(api_url, params={"per_page": per_page, "page": page})
        if data is None:
            print(f"[*] 第 {page} 页返回 422/404 或无法继续，停止分页。")
            break
        if not data:
            print(f"[*] 第 {page} 页返回空，停止分页。")
            break

        print(f"[*] 第 {page} 页：抓到 {len(data)} 个 public gist")

        for gist in data:
            updated_at = gist.get("updated_at")
            if not within_last_hours(updated_at, WITHIN_HOURS):
                continue

            files = gist.get("files") or {}
            for fname, finfo in files.items():
                if not is_candidate_by_filename(fname):
                    continue

                raw_url = finfo.get("raw_url")
                if not raw_url:
                    continue

                if raw_content_matches(raw_url):
                    all_raw_urls.add(raw_url)

        page += 1
        time.sleep(0.15)

    final_urls = sorted(all_raw_urls)
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(final_urls))

    print("\n[+] 完成")
    print(f" └─ 总计输出：{len(final_urls)} 条 raw_url")
    print(f" └─ 存储路径：{os.path.abspath(SAVE_PATH)}")


if __name__ == "__main__":
    main()
