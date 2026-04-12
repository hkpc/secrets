import os
import time
import requests
from datetime import datetime, timezone

SAVE_PATH = "filter_subs_24h.txt"
WITHIN_HOURS = 24

ALLOWED_SUFFIXES = (
    ".txt", ".yaml", ".yml", ".conf", ".config", ".json",
    ".md", ".list", ".cfg", ".properties"
)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Mozilla/5.0",
}

MY_TOKEN = os.getenv("GITHUB_TOKEN")
if MY_TOKEN:
    HEADERS["Authorization"] = f"token {MY_TOKEN}"


def github_get(url, params=None, timeout=20, max_retries=5):
    """
    返回 JSON；遇到 422/404 直接抛出特殊异常让上层停止分页。
    """
    for attempt in range(max_retries):
        res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)

        # rate limit / forbidden
        if res.status_code == 403:
            reset = res.headers.get("X-RateLimit-Reset")
            if reset:
                wait_s = max(1, int(reset) - int(time.time())) + 1
                print(f"[!] 403限流，等待 {wait_s}s 后重试...")
                time.sleep(wait_s)
                continue
            print("[!] 403(Forbidden) 但无 reset，等待 10s 后重试...")
            time.sleep(10)
            continue

        # 分页到尽头/接口保护时常见
        if res.status_code in (404, 422):
            # 抛出让 main 处理
            return None

        if res.status_code != 200:
            print(f"[!] 请求失败: HTTP {res.status_code}，尝试 {attempt+1}/{max_retries} ...")
            time.sleep(2)
            continue

        return res.json()

    print("[!] 达到最大重试次数，放弃本次请求")
    return None


def is_allowed_file(filename: str) -> bool:
    if not filename:
        return False
    lower = filename.lower()
    return any(lower.endswith(suf) for suf in ALLOWED_SUFFIXES)


def within_last_hours(dt_str: str, hours: int) -> bool:
    if not dt_str:
        return False
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - dt).total_seconds() <= hours * 3600


def main():
    print(f"[*] 开始扫描所有公共 Gist（仅保留过去 {WITHIN_HOURS} 小时内更新）...")

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
            print(f"[*] 第 {page} 页返回空数据，停止分页。")
            break

        print(f"[*] 第 {page} 页：抓到 {len(data)} 个 public gist")

        for gist in data:
            updated_at = gist.get("updated_at")
            if not within_last_hours(updated_at, WITHIN_HOURS):
                continue

            files = gist.get("files") or {}
            for fname, finfo in files.items():
                if is_allowed_file(fname):
                    raw_url = finfo.get("raw_url")
                    if raw_url:
                        all_raw_urls.add(raw_url)

        page += 1
        time.sleep(0.2)

    final_urls = sorted(all_raw_urls)
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(final_urls))

    print("\n[+] 扫描完成")
    print(f" └─ 总计发现：{len(final_urls)} 条 Raw 链接（{WITHIN_HOURS}h 内更新）")
    print(f" └─ 存储路径：{os.path.abspath(SAVE_PATH)}")


if __name__ == "__main__":
    main()
