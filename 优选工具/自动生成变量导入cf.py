# -*- coding: utf-8 -*-
import os
import csv
import tkinter as tk

# ================= 配置区域 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ENV = os.path.join(BASE_DIR, "worker.env")

# 严格遵循文档分类
PORTS_HTTP = [80, 8080, 8880, 2052, 2082, 2086, 2095]
PORTS_HTTPS = [443, 2053, 2083, 2087, 2096, 8443]
# ===========================================

def get_latest_folder(sub_folder):
    path = os.path.join(BASE_DIR, sub_folder, "History")
    if not os.path.exists(path): return None
    dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    if not dirs: return None
    dirs.sort(reverse=True)
    return os.path.join(path, dirs[0])

def get_top_domains(file_path, count=10):
    if not os.path.exists(file_path): return []
    res = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split("ms")
                if len(parts) > 1:
                    domain = parts[1].strip().lstrip("：:").strip()
                    if domain: res.append(domain)
                if len(res) >= count: break
    except: pass
    return res

def get_top_ips(file_path, count=10):
    if not os.path.exists(file_path): return []
    res = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if row: res.append(row[0].strip())
                if len(res) >= count: break
    except: pass
    return res

def set_clipboard(text):
    try:
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except: return False

def main():
    print(f"🚀 工作目录: {BASE_DIR}")
    dir_dom = get_latest_folder("domain")
    dir_ip  = get_latest_folder("ip")
    if not dir_dom or not dir_ip:
        print("❌ 找不到 History 目录")
        return

    # 提取数据
    list_v4  = get_top_ips(os.path.join(dir_ip, "result.csv"), 10)
    list_v6  = get_top_ips(os.path.join(dir_ip, "result_v6.csv"), 10)
    list_dom = get_top_domains(os.path.join(dir_dom, "CDNym.txt"), 10)

    # 兜底
    if not list_v4: list_v4 = ["1.0.0.1"]
    if not list_dom: list_dom = list_v4

    env = {}
    has_v6 = len(list_v6) > 0
    headers = {} # 用于存储标题位置

    if has_v6:
        print("ℹ️ 检测到 IPv6 数据，启用标准平衡分配模式 (80系:3v4+2v6+2dom | 443系:2v4+2v6+2dom)")
        # --- 80系 (1-7) ---
        for i in range(3): env[f"ip{i+1}"], env[f"pt{i+1}"] = list_v4[i % len(list_v4)], PORTS_HTTP[i]
        for i in range(2): env[f"ip{i+4}"], env[f"pt{i+4}"] = list_v6[i % len(list_v6)], PORTS_HTTP[i+3]
        for i in range(2): env[f"ip{i+6}"], env[f"pt{i+6}"] = list_dom[i % len(list_dom)], PORTS_HTTP[i+5]
        headers = {1: "# IPv4地址", 4: "# IPv6地址", 6: "# Domain域名", 8: "# IPv4地址", 10: "# IPv6地址", 12: "# Domain域名"}
        # --- 443系 (8-13) ---
        for i in range(2): env[f"ip{i+8}"], env[f"pt{i+8}"] = list_v4[(i+3) % len(list_v4)], PORTS_HTTPS[i]
        for i in range(2): env[f"ip{i+10}"], env[f"pt{i+10}"] = list_v6[(i+2) % len(list_v6)], PORTS_HTTPS[i+2]
        for i in range(2): env[f"ip{i+12}"], env[f"pt{i+12}"] = list_dom[(i+2) % len(list_dom)], PORTS_HTTPS[i+4]
    else:
        print("⚠️ 未检测到 IPv6 数据，启用向下兼容分配模式 (80系:4v4+3dom | 443系:3v4+3dom)")
        # --- 80系 (1-7) ---
        for i in range(4): env[f"ip{i+1}"], env[f"pt{i+1}"] = list_v4[i % len(list_v4)], PORTS_HTTP[i]
        for i in range(3): env[f"ip{i+5}"], env[f"pt{i+5}"] = list_dom[i % len(list_dom)], PORTS_HTTP[i+4]
        headers = {1: "# IPv4地址", 5: "# Domain域名", 8: "# IPv4地址", 11: "# Domain域名"}
        # --- 443系 (8-13) ---
        for i in range(3): env[f"ip{i+8}"], env[f"pt{i+8}"] = list_v4[(i+4) % len(list_v4)], PORTS_HTTPS[i]
        for i in range(3): env[f"ip{i+11}"], env[f"pt{i+11}"] = list_dom[(i+3) % len(list_dom)], PORTS_HTTPS[i+3]

    # --- 构造内容 ---
    content_lines = []
    for i in range(1, 14):
        if i == 1: content_lines.append("# === 80系端口 (ip1-7 关TLS) ===")
        if i == 8: content_lines.append("\n# === 443系端口 (ip8-13 开TLS) ===")
        if i in headers: content_lines.append(headers[i])
        
        content_lines.append(f'ip{i}="{env[f"ip{i}"]}"')
        content_lines.append(f'pt{i}="{env[f"pt{i}"]}"')
        
    full_text = "\n".join(content_lines)

    try:
        with open(OUTPUT_ENV, "w", encoding="utf-8") as f: f.write(full_text)
        print("\n" + "="*50 + "\n" + full_text + "\n" + "="*50)
        if set_clipboard(full_text):
            print(f"\n✅ 成功生成并分类！配置已自动复制到剪贴板。")
    except Exception as e: print(f"❌ 失败: {e}")

if __name__ == "__main__":
    main()