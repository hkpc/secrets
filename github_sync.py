import os
import time
import requests
from datetime import datetime, timezone

SAVE_PATH = "filter_subs_24h.txt"

# 只保留更新时间在过去多少小时内的 gist
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


def github_get(url, params=None, timeout=20):
    while True:
        res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)

        if res.status_code == 403:
            reset = res.headers.get("X-RateLimit-Reset")
            if reset:
                wait_s = max(1, int(reset) - int(time.time())) + 1
                print(f"[!] 触发限流(403)，等待 {wait_s}s 后重试...")
                time.sleep(wait_s)
                continue
            print("[!] 403(Forbidden) 但未拿到 reset，等待 10s 重试...")
            time.sleep(10)
            continue

        res.raise_for_status()
        return res.json()


def is_allowed_file(filename: str) -> bool:
    if not filename:
        return False
    lower = filename.lower()
    return any(lower.endswith(suf) for suf in ALLOWED_SUFFIXES)


def within_last_hours(dt_str: str, hours: int) -> bool:
    """
    dt_str: GitHub 返回的 updated_at，例如 "2024-01-01T12:34:56Z"
    """
    if not dt_str:
        return False
    # 统一按 UTC 解析
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = now - dt
    return delta.total_seconds() <= hours * 3600


def main():
    print(f"[*] 开始扫描所有公共 Gist（仅保留过去 {WITHIN_HOURS} 小时内更新）...")

    all_raw_urls = set()
    page = 1
    per_page = 100
    api_url = "https://api.github.com/gists/public"

    while True:
        data = github_get(api_url, params={"per_page": per_page, "page": page})

        if not data:
            break

        print(f"[*] 第 {page} 页：抓到 {len(data)} 个 public gist")

        for gist in data:
            updated_at = gist.get("updated_at")
            if not within_last_hours(updated_at, WITHIN_HOURS):
                # 因为 /gists/public 默认按 updated 排序的话，
                # 这里可以选择“提前停止”。但为了稳妥，先不做 break。
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
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(final_urls))

        print("\n[+] 扫描完成")
        print(f" └─ 总计发现：{len(final_urls)} 条 Raw 链接（{WITHIN_HOURS}h 内更新）")
        print(f" └─ 存储路径：{os.path.abspath(SAVE_PATH)}")
    except Exception as e:
        print(f"[!] 保存文件失败: {e}")


if __name__ == "__main__":
    main()
