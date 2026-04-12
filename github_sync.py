import os
import time
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


# 你要的目标特征（对“文件名/文件路径”做匹配）
# 注意：这里只匹配 gist 接口返回的文件名 key（gist.files 的 key）
TARGET_PATTERNS = [
    "subscribes.txt",
    "clash.yaml",
    "proxies",
    "proxies.yaml",
    "v2ray.txt",
    "nodes.txt",
]

# 可选：如果你想更严格一点，可以改成全等/后缀匹配
# 目前是“包含匹配”，更容易命中你给的那些常见命名


def github_get(url, params=None, timeout=20, max_retries=5):
    for _ in range(max_retries):
        res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)

        if res.status_code == 403:
            reset = res.headers.get("X-RateLimit-Reset")
            if reset:
                wait_s = max(1, int(reset) - int(time.time())) + 1
                print(f"[!] 403限流，等待 {wait_s}s 后重试...")
                time.sleep(wait_s)
                continue
            time.sleep(10)
            continue

        if res.status_code in (404, 422):
            return None

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


def is_target_filename(name: str) -> bool:
    if not name:
        return False
    lower = name.lower()
    # 对每个 pattern 做包含匹配（pattern 也转小写）
    for p in TARGET_PATTERNS:
        if p.lower() in lower:
            return True
    return False


def main():
    print(f"[*] 扫描 public gists，并仅输出：文件名命中 {TARGET_PATTERNS} 且 {WITHIN_HOURS}h 内更新的 raw_url")

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
                if not is_target_filename(fname):
                    continue
                raw_url = finfo.get("raw_url")
                if raw_url:
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
