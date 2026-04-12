import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor

# ================= 配置区 =================
# 搜索关键词：这些是节点订阅文件最常见的特征词
SEARCH_QUERIES = [
    "filename:subscribes.txt",
    "filename:clash.yaml proxies",
    "filename:proxies.yaml",
    "filename:v2ray.txt",
    "filename:nodes.txt"
]
MY_TOKEN = os.getenv("GITHUB_TOKEN") 

SAVE_PATH = "filter_subs.txt" 

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Mozilla/5.0",
}

if MY_TOKEN:
    HEADERS["Authorization"] = f"token {MY_TOKEN}"

def github_search_code(query):
    """通过代码搜索接口获取全网文件"""
    print(f"[*] 正在全网搜索: {query}...")
    url = f"https://api.github.com/search/code?q={query}&per_page=100"
    urls = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            items = res.json().get('items', [])
            for item in items:
                # 获取文件的原始下载地址，将 blob 替换为 raw
                raw_url = item.get('html_url', '').replace('/blob/', '/raw/')
                if raw_url:
                    urls.append(raw_url)
        elif res.status_code == 403:
            print(f"[!] 触发搜索频率限制 ({query})，等待中...")
            time.sleep(10)
    except Exception as e:
        print(f"[!] 搜索 {query} 时发生错误: {e}")
    return urls

def main():
    print(f"[*] 启动全网深度搜刮模式...")
    all_found_links = []

    # 1. 执行多维度代码搜索
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(github_search_code, SEARCH_QUERIES))
        for r in results:
            all_found_links.extend(r)

    # 2. 针对特定“大户”进行专项扫描
    special_users = ["Hugh0306", "Yueby", "wzdnzd", "vpei", "ssrsub"]
    print(f"[*] 正在专项扫描大户 Gist: {special_users}...")
    
    def scan_user_gists(user):
        u_links = []
        api_url = f"https://api.github.com/users/{user}/gists?per_page=50"
        try:
            res = requests.get(api_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                for gist in res.json():
                    for f_name, f_info in gist['files'].items():
                        # 过滤常见的文本和配置文件后缀
                        if f_name.lower().endswith(('.txt', '.yaml', '.yml')):
                            u_links.append(f_info['raw_url'])
        except Exception as e:
            print(f"[!] 扫描用户 {user} 时发生错误: {e}")
        return u_links

    with ThreadPoolExecutor(max_workers=5) as executor:
        gist_results = list(executor.map(scan_user_gists, special_users))
        for gr in gist_results:
            all_found_links.extend(gr)

    # 3. 去重与排序
    final_urls = sorted(list(set(all_found_links)))
    
    # 4. 保存文件到根目录
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(final_urls))
        
        print(f"\n[+] 搜刮报表")
        print(f" └─ 总计发现有效 Raw 链接: {len(final_urls)} 条")
        print(f" └─ 存储路径: {os.path.abspath(SAVE_PATH)}")
    except Exception as e:
        print(f"[!] 保存文件失败: {e}")

if __name__ == "__main__":
    main()
