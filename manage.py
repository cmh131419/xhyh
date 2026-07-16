#!/usr/bin/env python3
"""
鏄熺鍏冧酣 路 鏈湴绠＄悊鏈嶅姟
鍚姩: python manage.py
鍚庡彴: local admin preview
缃戠珯: local site preview
"""

import http.server
import json
import os
import socket
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

# Fix Windows GBK encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
CASES_FILE = DATA_DIR / "cases.json"


# ============================================================
# 鏁版嵁璇诲啓
# ============================================================

def read_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_id(data):
    if not data:
        return 1
    return max(item.get("id", 0) for item in data) + 1


# ============================================================
# API 璺敱
# ============================================================

def api_list(file_path):
    return 200, read_json(file_path)


def api_create(file_path, body):
    data = read_json(file_path)
    body["id"] = next_id(data)
    data.append(body)
    write_json(file_path, data)
    return 201, body


def api_update(file_path, item_id, body):
    data = read_json(file_path)
    for item in data:
        if item.get("id") == item_id:
            item.update(body)
            item["id"] = item_id  # 涓嶅厑璁告敼 ID
            write_json(file_path, data)
            return 200, item
    return 404, {"error": "not found"}


def api_delete(file_path, item_id):
    data = read_json(file_path)
    new_data = [item for item in data if item.get("id") != item_id]
    if len(new_data) == len(data):
        return 404, {"error": "not found"}
    write_json(file_path, new_data)
    return 200, {"ok": True}


def api_publish():
    """Git add + commit + push (鍚庡彴绾跨▼鎵ц)"""
    import threading

    def do_publish():
        try:
            subprocess.run(
                ["git", "add", "data/", "index.html"],
                cwd=str(ROOT), capture_output=True, text=True, check=True
            )
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(ROOT), capture_output=True, text=True
            )
            if not status.stdout.strip():
                return
            from datetime import datetime
            msg = f"馃摑 鍚庡彴鏇存柊 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=str(ROOT), capture_output=True, text=True
            )
            subprocess.run(
                ["git", "push"],
                cwd=str(ROOT), capture_output=True, text=True, check=True
            )
            sys.stdout.write("  鉁?鍙戝竷鎴愬姛锛乗n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(f"  鉂?鍙戝竷澶辫触: {e}\n")
            sys.stdout.flush()

    threading.Thread(target=do_publish, daemon=True).start()
    return 200, {"message": "鍙戝竷宸叉彁浜わ紝1-2鍒嗛挓鍚庣敓鏁堛€?, "url": "https://cmh131419.github.io/xhyh/"}


# ============================================================
# HTTP 璇锋眰澶勭悊鍣?
# ============================================================

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        # 绠€娲佹棩蹇?
        sys.stdout.write(f"  [{self.command}] {args[0]}\n")
        sys.stdout.flush()

    def end_headers(self):
        # CORS 鈥斺€?鍏佽鍚庡彴椤甸潰鐨勮法鍩熻姹傦紙铏界劧鍚屾簮锛屼絾鍔犱笂鏇村畨鍏級
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def get_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    # ---- API 璺敱鍒嗗彂 ----
    def handle_api(self, method):
        path = urllib.parse.urlparse(self.path).path

        # GET /api/articles  or  GET /api/cases
        if method == "GET":
            if path == "/api/articles":
                return self.send_json(*api_list(ARTICLES_FILE))
            elif path == "/api/cases":
                return self.send_json(*api_list(CASES_FILE))

        # POST /api/articles  or  POST /api/cases
        if method == "POST":
            body = self.get_body()
            if path == "/api/articles":
                return self.send_json(*api_create(ARTICLES_FILE, body))
            elif path == "/api/cases":
                return self.send_json(*api_create(CASES_FILE, body))
            elif path == "/api/publish":
                return self.send_json(*api_publish())

        # PUT /api/articles/3  or  PUT /api/cases/3
        if method == "PUT":
            body = self.get_body()
            parts = path.split("/")
            if len(parts) == 4:
                resource = parts[2]
                item_id = int(parts[3])
                if resource == "articles":
                    return self.send_json(*api_update(ARTICLES_FILE, item_id, body))
                elif resource == "cases":
                    return self.send_json(*api_update(CASES_FILE, item_id, body))

        # DELETE /api/articles/3  or  DELETE /api/cases/3
        if method == "DELETE":
            parts = path.split("/")
            if len(parts) == 4:
                resource = parts[2]
                item_id = int(parts[3])
                if resource == "articles":
                    return self.send_json(*api_delete(ARTICLES_FILE, item_id))
                elif resource == "cases":
                    return self.send_json(*api_delete(CASES_FILE, item_id))

        self.send_json(404, {"error": "API route not found"})

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/api/"):
            return self.handle_api("GET")

        # 鍙嬪ソ鐨?URL 閲嶅啓
        if path == "/admin" or path == "/admin/":
            self.path = "/admin/admin.html"

        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.handle_api("POST")
        self.send_json(405, {"error": "method not allowed"})

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self.handle_api("PUT")
        self.send_json(405, {"error": "method not allowed"})

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self.handle_api("DELETE")
        self.send_json(405, {"error": "method not allowed"})


# ============================================================
# 鍚姩
# ============================================================

def main():
    # 纭繚 data 鐩綍瀛樺湪
    DATA_DIR.mkdir(exist_ok=True)
    for f, default in [(ARTICLES_FILE, []), (CASES_FILE, [])]:
        if not f.exists():
            write_json(f, default)

    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print()
    print("  鈿?鏄熺鍏冧酣 路 鏈湴绠＄悊鏈嶅姟")
    print("  鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€")
    print(f"  鍚庡彴绠＄悊: http://{HOST}:{PORT}/admin/")
    print(f"  缃戠珯棰勮: http://{HOST}:{PORT}/")
    print(f"  API 鍦板潃: http://{HOST}:{PORT}/api/")
    print()
    print("  鎸?Ctrl+C 鍋滄鏈嶅姟")
    print()

    # 鑷姩鎵撳紑娴忚鍣紙Windows 鍙兘闃诲锛屾墜鍔ㄦ墦寮€锛?
    # webbrowser.open(f"http://{HOST}:{PORT}/admin/")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  馃憢 宸插仠姝?)
        server.server_close()


if __name__ == "__main__":
    main()

