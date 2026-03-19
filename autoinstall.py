#!/usr/bin/env python3
"""
Gofile Auto Download & Install Tool
Termux Android (Root) | Version 2.1
- Multi-folder support
- GitHub version check
- Auto password fill
"""

import os
import sys
import hashlib
import subprocess
import requests
from tqdm import tqdm
from packaging import version  # pip install packaging

# ─── CẤU HÌNH ───────────────────────────────────────────────
CURRENT_VERSION = "1.0.0"      # Phiên bản hiện tại của tool này

# Link raw GitHub tới file version.json của bạn
VERSION_CHECK_URL = "https://raw.githubusercontent.com/zam2109/Auto-Install/refs/heads/main/version.json"

API_TOKEN  = "PCCB1VRHKM3QHVO2ABEPJUYEtWkDhHxM"
ACCOUNT_ID = "fe6763c0-77b1-4997-a1ab-15ef4909d0d7"
DOWNLOAD_DIR = "/sdcard/GofileDownloads"

HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# Password mặc định cho folder có bảo vệ (ẩn, không hiển thị)
_DEFAULT_PASS = "taphoacloudchamstore"

# ─── DANH SÁCH FOLDER ────────────────────────────────────────
FOLDERS = {
    "1": {
        "name": "📂 FREE  -  Executor Collection",
        "id": None,
        "subfolders": {
            "1": {"name": "⚡ Delta QT",   "id": "a47d8047-023d-4680-918f-f18de2266054"},
            "2": {"name": "⚡ Delta VNG",  "id": "8ce37c67-8b61-42b0-8c56-09a5068c2be0"},
            "3": {"name": "⚡ Arceus QT",  "id": "862205a5-f277-40d5-a59d-0daab3fb89f6"},
            "4": {"name": "⚡ Arceus VNG", "id": "8347e4d6-922a-43d3-b1f0-ff23be8f3f21"},
        },
    },
    "2": {
        "name": "💎 PREMIUM  -  [Chưa cấu hình]",
        "id": "YOUR_PREMIUM_FOLDER_ID",
        "subfolders": {},
    },
}

INSTALLABLE = {
    ".apk": "pm install -r",
    ".zip": "unzip -o",
    ".sh":  "bash",
    ".deb": "dpkg -i",
}
# ────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════
#  VERSION CHECK
# ════════════════════════════════════════════════════════════

def compare_versions(v1, v2):
    """So sánh 2 version string. Return: 1 nếu v1 > v2, -1 nếu v1 < v2, 0 nếu bằng."""
    parts1 = [int(x) for x in v1.strip().split(".")]
    parts2 = [int(x) for x in v2.strip().split(".")]
    # Cân bằng độ dài
    while len(parts1) < len(parts2): parts1.append(0)
    while len(parts2) < len(parts1): parts2.append(0)
    for a, b in zip(parts1, parts2):
        if a > b: return 1
        if a < b: return -1
    return 0


def check_version():
    """
    Kiểm tra version từ GitHub raw URL.
    - Nếu version hiện tại >= version trên GitHub → True (tiếp tục chạy)
    - Nếu version hiện tại < version trên GitHub → False (lỗi thời → thoát)
    - Nếu không kết nối được → cảnh báo nhưng vẫn cho chạy
    """
    print("  🔄 Đang kiểm tra phiên bản tool...")

    try:
        resp = requests.get(VERSION_CHECK_URL, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        latest  = data.get("version", "0.0.0").strip()
        status  = data.get("status", "active").strip().lower()
        message = data.get("message", "")

        # Nếu server đánh dấu tool bị vô hiệu hoá cứng
        if status in ("disabled", "blocked", "inactive"):
            print(f"\n  ╔══════════════════════════════════════════╗")
            print(f"  ║  ❌  TOOL ĐÃ BỊ VÔ HIỆU HOÁ             ║")
            print(f"  ╠══════════════════════════════════════════╣")
            print(f"  ║  {message[:42]:<42}║")
            print(f"  ╚══════════════════════════════════════════╝\n")
            sys.exit(1)

        cmp = compare_versions(CURRENT_VERSION, latest)

        if cmp >= 0:
            # Phiên bản hiện tại mới hơn hoặc bằng → OK
            print(f"  ✅ Phiên bản: {CURRENT_VERSION}  |  Mới nhất: {latest}  →  UP TO DATE\n")
            if message:
                print(f"  📢 {message}\n")
            return True
        else:
            # Phiên bản lỗi thời
            print(f"\n  ╔══════════════════════════════════════════╗")
            print(f"  ║  ⚠️   PHIÊN BẢN LỖI THỜI!               ║")
            print(f"  ╠══════════════════════════════════════════╣")
            print(f"  ║  Hiện tại : v{CURRENT_VERSION:<29}║")
            print(f"  ║  Mới nhất : v{latest:<29}║")
            if message:
                print(f"  ║  {message[:42]:<42}║")
            print(f"  ╠══════════════════════════════════════════╣")
            print(f"  ║  ❌ Vui lòng cập nhật tool trước khi    ║")
            print(f"  ║     tiếp tục sử dụng.                   ║")
            print(f"  ╚══════════════════════════════════════════╝\n")
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("  ⚠️  Không có mạng, bỏ qua kiểm tra phiên bản.\n")
        return True
    except requests.exceptions.Timeout:
        print("  ⚠️  Kiểm tra version timeout, tiếp tục...\n")
        return True
    except Exception as e:
        print(f"  ⚠️  Lỗi kiểm tra version: {e}, tiếp tục...\n")
        return True


# ════════════════════════════════════════════════════════════
#  PASSWORD AUTO-FILL
# ════════════════════════════════════════════════════════════

def get_password(prompt_visible=False):
    """
    Hỏi user có muốn nhập password không.
    Nếu Enter (để trống) → tự dùng default password (không hiển thị).
    Nếu nhập 'none' → không dùng password.
    """
    if prompt_visible:
        raw = input("  🔒 Mật khẩu folder (Enter = tự động, 'none' = không dùng): ").strip()
    else:
        raw = input("  🔒 Mật khẩu (Enter = tự động, 'none' = bỏ qua): ").strip()

    if raw.lower() == "none":
        return None
    elif raw == "":
        # Tự dùng password mặc định, không log ra
        return _DEFAULT_PASS
    else:
        return raw


def hash_password(pwd):
    """SHA-256 hash password trước khi gửi lên API."""
    if pwd is None:
        return None
    return hashlib.sha256(pwd.encode()).hexdigest()


# ════════════════════════════════════════════════════════════
#  UI HELPERS
# ════════════════════════════════════════════════════════════

def clear():
    os.system("clear")


def banner():
    print(f"""
  ╔══════════════════════════════════════════════════╗
  ║       🚀 GOFILE TOOL - TERMUX ANDROID 🚀        ║
  ║         Auto Download & Install  v{CURRENT_VERSION}          ║
  ╚══════════════════════════════════════════════════╝
""")


def check_root():
    try:
        r = subprocess.run(
            "su -c 'echo OK'", shell=True,
            capture_output=True, text=True, timeout=5
        )
        if "OK" in r.stdout:
            print("  🔐 Root: ✅ Đã có quyền root\n")
            return True
    except Exception:
        pass
    print("  ⚠️  Root: ❌ Không có root (cài APK có thể thất bại)\n")
    return False


# ════════════════════════════════════════════════════════════
#  FOLDER SELECTION
# ════════════════════════════════════════════════════════════

def select_main_folder():
    print("  ╔══════════════════════════════════════════╗")
    print("  ║          CHỌN LOẠI FOLDER                ║")
    print("  ╠══════════════════════════════════════════╣")
    for key, folder in FOLDERS.items():
        print(f"  ║  [{key}] {folder['name']:<36}║")
    print("  ║  [0] Thoát                               ║")
    print("  ╚══════════════════════════════════════════╝")
    choice = input("\n  👉 Chọn folder: ").strip()
    if choice == "0":
        sys.exit(0)
    if choice not in FOLDERS:
        print("  [!] Lựa chọn không hợp lệ.")
        sys.exit(1)
    return choice


def select_sub_folder(main_key):
    folder = FOLDERS[main_key]
    subs = folder.get("subfolders", {})
    if not subs:
        if not folder["id"] or "YOUR_" in folder["id"]:
            print("  [!] Folder này chưa được cấu hình.")
            sys.exit(1)
        return folder["id"], folder["name"]

    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  {folder['name']:<40}║")
    print(f"  ╠══════════════════════════════════════════╣")
    for key, sub in subs.items():
        print(f"  ║  [{key}] {sub['name']:<36}║")
    print(f"  ║  [A] Tải tất cả executor                 ║")
    print(f"  ║  [0] Quay lại                             ║")
    print(f"  ╚══════════════════════════════════════════╝")

    choice = input("\n  👉 Chọn executor: ").strip().upper()
    if choice == "0":
        return None, None
    if choice == "A":
        return "ALL", subs
    if choice in subs:
        return subs[choice]["id"], subs[choice]["name"]
    print("  [!] Lựa chọn không hợp lệ.")
    return None, None


# ════════════════════════════════════════════════════════════
#  GOFILE API
# ════════════════════════════════════════════════════════════

def get_folder_contents(folder_id, password=None):
    params = {}
    pwd_hash = hash_password(password)
    if pwd_hash:
        params["password"] = pwd_hash

    url = f"https://api.gofile.io/contents/{folder_id}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"  [LỖI] Kết nối thất bại: {e}")
        return {}

    if data.get("status") != "ok":
        err = data.get("status", "unknown")
        print(f"  [LỖI] API: {err}")
        # Nếu lỗi password, thử lại không có password
        if "password" in str(err).lower():
            print("  [~] Thử lại không dùng password...")
            return get_folder_contents(folder_id, password=None)
        return {}

    children = data["data"].get("children", {})
    return {k: v for k, v in children.items() if v.get("type") == "file"}


def list_and_select_files(files, folder_name):
    if not files:
        print(f"  [!] Không có file nào trong: {folder_name}")
        return []

    file_list = list(files.values())
    print(f"\n  ╔══════════════════════════════════════════════════╗")
    print(f"  ║  📁 {folder_name:<44}║")
    print(f"  ╠════╦══════════════════════════════════╦══════════╣")
    print(f"  ║ No ║ Tên file                         ║   Size   ║")
    print(f"  ╠════╬══════════════════════════════════╬══════════╣")
    for i, f in enumerate(file_list, 1):
        size_mb = f.get("size", 0) / (1024 * 1024)
        name = f["name"][:30]
        print(f"  ║{i:3} ║ {name:<32}║{size_mb:7.1f}MB║")
    print(f"  ╠════╩══════════════════════════════════╩══════════╣")
    print(f"  ║  Nhập số (VD: 1 2 3), 'all' = tất cả, 0 = thoát ║")
    print(f"  ╚══════════════════════════════════════════════════╝")

    choice = input("\n  👉 Chọn file: ").strip().lower()
    if choice == "0":
        return []
    if choice == "all":
        return file_list

    selected = []
    for part in choice.split():
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(file_list):
                selected.append(file_list[idx])
    return selected


# ════════════════════════════════════════════════════════════
#  DOWNLOAD & INSTALL
# ════════════════════════════════════════════════════════════

def download_file(file_info, dest_dir):
    name = file_info["name"]
    download_url = file_info.get("link", "")
    if not download_url:
        print(f"  [!] Không có link tải: {name}")
        return None

    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, name)

    if os.path.exists(dest_path):
        yn = input(f"  [?] '{name}' đã tồn tại. Tải lại? [y/N]: ").strip().lower()
        if yn != "y":
            print(f"  ⏭  Bỏ qua: {name}")
            return dest_path

    print(f"\n  📥 Đang tải: {name}")
    try:
        resp = requests.get(download_url, headers=HEADERS, stream=True, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [LỖI] Tải thất bại: {e}")
        return None

    total = int(resp.headers.get("content-length", 0))
    with open(dest_path, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True,
        desc=f"  {name[:25]}", ncols=55
    ) as bar:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

    print(f"  ✅ Lưu: {dest_path}")
    return dest_path


def install_file(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext not in INSTALLABLE:
        print(f"  [~] '{ext}' không hỗ trợ cài tự động → {file_path}")
        return

    yn = input(f"\n  🔧 Cài đặt '{os.path.basename(file_path)}'? [y/N]: ").strip().lower()
    if yn != "y":
        print("  ⏭  Bỏ qua cài đặt.")
        return

    if ext == ".apk":
        cmd = f"su -c 'pm install -r \"{file_path}\"'"
    elif ext == ".zip":
        out_dir = file_path.replace(".zip", "_extracted")
        os.makedirs(out_dir, exist_ok=True)
        cmd = f"unzip -o \"{file_path}\" -d \"{out_dir}\""
    elif ext == ".sh":
        cmd = f"bash \"{file_path}\""
    elif ext == ".deb":
        cmd = f"dpkg -i \"{file_path}\""
    else:
        return

    print("  ⚙️  Đang cài đặt...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("  ✅ Cài đặt thành công!")
        if result.stdout.strip():
            print(f"  {result.stdout.strip()[:300]}")
    else:
        print(f"  ❌ Cài đặt thất bại (code {result.returncode}):")
        print(f"  {(result.stderr or result.stdout).strip()[:300]}")


def process_folder(folder_id, folder_name, password=None):
    print(f"\n  🔍 Đang load: {folder_name}...")
    files = get_folder_contents(folder_id, password)
    selected = list_and_select_files(files, folder_name)
    if not selected:
        return []

    print(f"\n  📋 Đã chọn {len(selected)} file(s):")
    for f in selected:
        print(f"     • {f['name']}")

    yn = input("\n  ▶ Bắt đầu tải? [y/N]: ").strip().lower()
    if yn != "y":
        return []

    downloaded = []
    dest = os.path.join(DOWNLOAD_DIR, folder_name.replace(" ", "_").replace("/", "-"))
    for f in selected:
        path = download_file(f, dest)
        if path:
            downloaded.append(path)
    return downloaded


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════

def main():
    clear()
    banner()

    # ── BƯỚC 1: Kiểm tra version từ GitHub ──────────────────
    check_version()

    # ── BƯỚC 2: Kiểm tra root ───────────────────────────────
    check_root()

    # ── BƯỚC 3: Hỏi password (auto-fill nếu Enter) ──────────
    password = get_password()

    # ── BƯỚC 4: Chọn folder ─────────────────────────────────
    main_key = select_main_folder()
    folder_data = FOLDERS[main_key]

    downloaded_all = []

    if not folder_data["subfolders"]:
        paths = process_folder(folder_data["id"], folder_data["name"], password)
        downloaded_all.extend(paths)
    else:
        folder_id, folder_name = select_sub_folder(main_key)
        if folder_id is None:
            print("  Đã huỷ.")
            sys.exit(0)
        if folder_id == "ALL":
            for sub in folder_name.values():
                paths = process_folder(sub["id"], sub["name"], password)
                downloaded_all.extend(paths)
        else:
            paths = process_folder(folder_id, folder_name, password)
            downloaded_all.extend(paths)

    # ── BƯỚC 5: Cài đặt ─────────────────────────────────────
    if downloaded_all:
        print(f"\n  {'─'*50}")
        print(f"  📦 GIAI ĐOẠN CÀI ĐẶT ({len(downloaded_all)} file)")
        print(f"  {'─'*50}")
        for path in downloaded_all:
            install_file(path)

    print(f"\n  ✨ Hoàn tất! File lưu tại: {DOWNLOAD_DIR}\n")


if __name__ == "__main__":
    main()
