import os
import time
import re
import requests
from datetime import datetime, timezone

SAVE_PATH = "filter_subs_24h.txt"
WITHIN_HOURS = 24

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Mozilla/5.0",
}
MY_TOKEN = os.getenv("GITHUB_TOKEN")
if MY_TOKEN:
    HEADERS["Authorization"] = f"token {MY_TOKEN}"

# 内容特征：你给的这些词（这里做成“不区分大小写”的子串）
TARGET_KEYWORDS = [
    "subscribes.txt",
    "clash.yaml",
    "proxies.yaml",
    "proxies",
    "v2ray.txt",
    "nodes.txt",
]

# 先用后缀缩小候选（减少请求 raw 的数量）
CANDIDATE_SUFFIXES = (".txt", ".yaml", ".yml")

# 拉取 raw 内容时限制最大读取字节，避免超大文件拖垮
MAX_RAW_BYTES = 200_000  # 约200KB
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


def raw_content_hits(raw_url: str) -> bool:
    try:
        # 直接用 requests 流式读，尽量少读
        r = requests.get(raw_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT, stream=True)
        if r.status_code != 200:
            return False

        content = b""
        for chunk in r.iter_content(chunk_size=4096):
            if not chunk:
                break
            content += chunk
            if len(content) >= MAX_RAW_BYTES:
                break

        # 尝试按 utf-8/gzip? 这里按忽略错误解码更稳
        text = content.decode("utf-8", errors="ignore").lower()

        # 命中任一关键词即可
        return any(kw.lower() in text for kw in TARGET_KEYWORDS)

    except Exception:
        return False


def main():
    print(f"[*] 扫描 public gists；仅保留 {WITHIN_HOURS}h 内更新，且 raw 内容命中关键词：{TARGET_KEYWORDS}")
    print("[*] 候选文件后缀：", CANDIDATE_SUFFIXES)

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

                if raw_content_hits(raw_url):
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
