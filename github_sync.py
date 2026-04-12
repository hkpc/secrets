import os
import time
import requests

SAVE_PATH = "filter_subs.txt"

# 你关心的常见订阅/代理配置后缀（可自行增减）
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
    """带基本限流处理的 GET"""
    while True:
        res = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        # rate limit
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


def main():
    print("[*] 开始扫描所有公共 Gist（分页抓取）...")

    all_raw_urls = set()
    page = 1
    per_page = 100

    # Public gists endpoint：/gists/public
    # https://docs.github.com/en/rest/gists/gists?apiVersion=2022-11-28#list-public-gists
    while True:
        api_url = "https://api.github.com/gists/public"
        data = github_get(api_url, params={"per_page": per_page, "page": page})

        if not data:
            break

        print(f"[*] 第 {page} 页：抓到 {len(data)} 个 public gist")

        for gist in data:
            files = gist.get("files") or {}
            for fname, finfo in files.items():
                if is_allowed_file(fname):
                    raw_url = finfo.get("raw_url")
                    # raw_url 有时为空；通常 raw_url 不为空
                    if raw_url:
                        all_raw_urls.add(raw_url)

        page += 1

        # 小睡一下，避免太频繁
        time.sleep(0.2)

    final_urls = sorted(all_raw_urls)
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(final_urls))
        print("\n[+] 扫描完成")
        print(f" └─ 总计发现：{len(final_urls)} 条 Raw 链接")
        print(f" └─ 存储路径：{os.path.abspath(SAVE_PATH)}")
    except Exception as e:
        print(f"[!] 保存文件失败: {e}")


if __name__ == "__main__":
    main()
