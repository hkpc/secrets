import os
import time
import re
import requests
from datetime import datetime, timezone

SAVE_PATH = "filter_subs_24h.txt"
WITHIN_HOURS = 24

HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "Mozilla/5.0"}
MY_TOKEN = os.getenv("GITHUB_TOKEN")
if MY_TOKEN:
    HEADERS["Authorization"] = f"token {MY_TOKEN}"

# 候选：文件名/路径含这些（先缩小数量）
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

CANDIDATE_SUFFIXES = (".txt", ".yaml", ".yml")
MAX_RAW_BYTES = 250_000
TIMEOUT = 20

# 关键词/格式强校验
CLASH_MUST = [
    "proxies:",
]

CLASH_ANY = [
    "proxy-groups:",
    "rules:",
    "port:",
    "- name:",
    "type:",
    "domain-suffix",
]

# base64强校验：只看字符比例与长段长度
BASE64_CHARS_RE = re.compile(r'^[A-Za-z0-9+/=\s]+$')

# 取文本做 base64 估计时的最大样本长度
BASE64_SAMPLE_CHARS = 20000
BASE64_MIN_LEN = 1000
BASE64_MIN_B64_RATIO = 0.65

# 常见订阅链接前缀（如果出现直接通过）
SUB_LINK_PREFIXES = ("vmess://", "vless://", "trojan://", "ss://")

# 日志过滤：命中则直接拒绝（可继续加）
LOG_BLACK_HINTS = ("output_log", "log:", "error", "warning", "traceback")


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
    if not any(lower.endswith(suf) for suf in CANDIDATE_SUFFIXES):
        return False
    # 先做关键词命中缩小
    return any(k.lower() in lower for k in TARGET_KEYWORDS)


def fetch_snippet(raw_url: str) -> str:
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
    return content.decode("utf-8", errors="ignore")


def clash_strong_check(text_lower: str) -> bool:
    # 必须出现 proxies:
    if not any(k in text_lower for k in CLASH_MUST):
        return False
    # 再要求至少出现一个其它结构字段
    return any(k in text_lower for k in CLASH_ANY)


def contains_sub_links(text_lower: str) -> bool:
    return any(p in text_lower for p in SUB_LINK_PREFIXES)


def base64_long_segment_check(text: str) -> bool:
    # 先拒绝明显是日志/短文本
    t = text.strip()
    if not t or len(t) < BASE64_MIN_LEN:
        return False

    sample = t[:BASE64_SAMPLE_CHARS]
    sample_compact = "".join(sample.split())  # 去空白
    if len(sample_compact) < BASE64_MIN_LEN:
        return False

    # 字符集必须像 base64
    if not BASE64_CHARS_RE.match(sample):
        return False

    # 计算 base64 字符占比（不含空白）
    b64_allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    total = len(sample_compact)
    if total == 0:
        return False
    b64_count = sum(1 for c in sample_compact if c in b64_allowed)
    ratio = b64_count / total
    return ratio >= BASE64_MIN_B64_RATIO


def strong_check(raw_url: str, text: str) -> bool:
    low = text.lower()

    # 黑名单拒绝
    if any(h in low for h in LOG_BLACK_HINTS):
        return False

    # Clash 强校验
    if clash_strong_check(low):
        return True

    # 订阅链接前缀
    if contains_sub_links(low):
        return True

    # V2Ray base64 长段强校验
    if base64_long_segment_check(text):
        return True

    return False


def main():
    print(f"[*] 扫描 public gists：{WITHIN_HOURS}h 内候选，并做强格式校验（Clash/Vmess/V2Ray base64）")

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

                text = fetch_snippet(raw_url)
                if not text:
                    continue

                if strong_check(raw_url, text):
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
