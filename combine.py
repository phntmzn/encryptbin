#!/usr/bin/env python3
"""
All-in-one: AppleScript app + PyInstaller build + Fernet encryption
Usage:
    python build_encrypt.py              # build & encrypt
    python build_encrypt.py --password SECRET
    python build_encrypt.py --windowed
    python build_encrypt.py --onedir
"""

import argparse
import base64
import glob
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# SECTION 1 — The application logic (written to disk, then built)
# ─────────────────────────────────────────────────────────────

APP_SOURCE = '''#!/usr/bin/env python3
"""
Sample application that uses AppleScript functionality
"""
import subprocess
import sys
import os
import json

def run_applescript(script):
    """Run AppleScript and return result"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"AppleScript Error: {e.stderr}")
        return None

def get_system_info():
    """Get Mac system information using AppleScript"""
    script = """
    set sysInfo to system info
    set os_version to system version of sysInfo
    set computer_name to computer name of sysInfo
    set user_name to short user name of sysInfo
    return os_version & "|" & computer_name & "|" & user_name
    """
    result = run_applescript(script)
    if result:
        parts = result.split("|")
        return {
            "os_version":    parts[0],
            "computer_name": parts[1],
            "user_name":     parts[2],
        }
    return None

def show_notification(title, message):
    """Show macOS notification"""
    script = f\'\'\'display notification "{message}" with title "{title}"\'\'\'
    run_applescript(script)

def main():
    print("=" * 50)
    print("My Protected AppleScript Application")
    print("=" * 50)

    print("\\n📊 System Information:")
    info = get_system_info()
    if info:
        for key, value in info.items():
            print(f"  {key}: {value}")

    print("\\n🔔 Showing notification...")
    show_notification("Hello from Protected App",
                      "This app was built with PyInstaller and encrypted!")

    print("\\n💻 Doing some work...")
    script = """
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
    end tell
    return frontApp
    """
    front_app = run_applescript(script)
    if front_app:
        print(f"  Frontmost application: {front_app}")

    print("\\n✅ Application completed successfully!")

if __name__ == "__main__":
    main()
'''

# ─────────────────────────────────────────────────────────────
# SECTION 2 — Build helpers
# ─────────────────────────────────────────────────────────────

DIST_DIR      = "dist"
BUILD_DIR     = "build"
ENCRYPTED_DIR = "encrypted_dist"
APP_SCRIPT    = "_app_entry.py"          # temp file written before PyInstaller runs
APP_NAME      = "MyProtectedApp"


def clean_previous_builds():
    print("🧹 Cleaning previous builds...")
    for d in [DIST_DIR, BUILD_DIR, ENCRYPTED_DIR, APP_SCRIPT]:
        if os.path.isdir(d):
            shutil.rmtree(d)
        elif os.path.isfile(d):
            os.remove(d)
    print("✅ Clean complete")


def write_app_source():
    """Write the embedded app source to a temp file for PyInstaller."""
    with open(APP_SCRIPT, "w") as f:
        f.write(APP_SOURCE)
    print(f"📝 App source written to {APP_SCRIPT}")


def build_with_pyinstaller(one_file=True, windowed=False):
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        sys.exit("❌ PyInstaller is not installed. Run: pip install pyinstaller")

    print(f"\n🔨 Building {APP_NAME} with PyInstaller...")

    args = [
        APP_SCRIPT,
        "--name",      APP_NAME,
        "--distpath",  DIST_DIR,
        "--workpath",  BUILD_DIR,
        "--specpath",  BUILD_DIR,
        "--clean",
        "--noconfirm",
        "--hidden-import", "subprocess",
    ]

    args.append("--onefile" if one_file else "--onedir")
    if windowed:
        args.append("--windowed")

    pyi.run(args)
    print("✅ PyInstaller build complete")

    if one_file:
        pattern = (
            f"{DIST_DIR}/{APP_NAME}.app" if windowed
            else f"{DIST_DIR}/{APP_NAME}"
        )
    else:
        pattern = f"{DIST_DIR}/{APP_NAME}/*"

    return glob.glob(pattern)


# ─────────────────────────────────────────────────────────────
# SECTION 3 — Encryption helpers
# ─────────────────────────────────────────────────────────────

def encrypt_binary(binary_path, password=None):
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        sys.exit("❌ cryptography is not installed. Run: pip install cryptography")

    print(f"\n🔐 Encrypting: {binary_path}")

    if password:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(password.encode()).digest()[:32]
        )
    else:
        key = Fernet.generate_key()

    cipher = Fernet(key)

    with open(binary_path, "rb") as f:
        binary_data = f.read()

    metadata = {
        "original_name":     os.path.basename(binary_path),
        "size":              len(binary_data),
        "build_time":        datetime.now().isoformat(),
        "encryption_method": "Fernet",
        "hash":              hashlib.sha256(binary_data).hexdigest(),
    }

    metadata_bytes = json.dumps(metadata).encode()
    encrypted_binary = cipher.encrypt(binary_data)

    os.makedirs(ENCRYPTED_DIR, exist_ok=True)

    base = os.path.basename(binary_path)
    enc_path  = os.path.join(ENCRYPTED_DIR, f"{base}.encrypted")
    key_path  = os.path.join(ENCRYPTED_DIR, f"{base}.key")
    meta_path = os.path.join(ENCRYPTED_DIR, f"{base}.meta.json")

    # Format: [4-byte metadata length][metadata JSON][Fernet-encrypted binary]
    with open(enc_path, "wb") as f:
        f.write(struct.pack(">I", len(metadata_bytes)))
        f.write(metadata_bytes)
        f.write(encrypted_binary)

    with open(key_path, "wb") as f:
        f.write(key)

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Encrypted  → {enc_path}")
    print(f"   Key        → {key_path}")
    print(f"   Metadata   → {meta_path}")
    print(f"   Original size:  {metadata['size']:,} bytes")
    print(f"   Encrypted size: {len(encrypted_binary):,} bytes")

    return enc_path, key_path, metadata


def verify_encryption(enc_path, key_path):
    from cryptography.fernet import Fernet

    print("\n🔍 Verifying encryption...")

    with open(enc_path, "rb") as f:
        meta_len = struct.unpack(">I", f.read(4))[0]
        metadata = json.loads(f.read(meta_len))
        encrypted_binary = f.read()

    with open(key_path, "rb") as f:
        key = f.read()

    cipher = Fernet(key)
    decrypted = cipher.decrypt(encrypted_binary)
    ok = hashlib.sha256(decrypted).hexdigest() == metadata["hash"]

    print("✅ Verification passed — hashes match." if ok
          else "❌ Verification FAILED — hashes do not match!")
    return ok


def create_launcher(enc_path, key_path):
    """Write a minimal Python launcher that decrypts and runs the binary."""
    launcher_code = f'''\
#!/usr/bin/env python3
"""Secure launcher — decrypts and executes the protected binary."""
import os, struct, json, stat, tempfile, subprocess
from cryptography.fernet import Fernet

ENC_FILE = {repr(os.path.abspath(enc_path))}
KEY_FILE = {repr(os.path.abspath(key_path))}

def main():
    print("🔐 Decrypting application...")
    with open(ENC_FILE, "rb") as f:
        meta_len = struct.unpack(">I", f.read(4))[0]
        f.read(meta_len)                    # skip metadata
        encrypted = f.read()

    with open(KEY_FILE, "rb") as f:
        key = f.read()

    from cryptography.fernet import Fernet
    binary = Fernet(key).decrypt(encrypted)

    with tempfile.NamedTemporaryFile(delete=False, suffix="_app") as tmp:
        tmp.write(binary)
        tmp_path = tmp.name

    os.chmod(tmp_path, stat.S_IRWXU)
    print("🚀 Launching...")
    try:
        subprocess.run([tmp_path], check=True)
    finally:
        os.remove(tmp_path)

if __name__ == "__main__":
    main()
'''
    launcher_path = os.path.join(ENCRYPTED_DIR, "launcher.py")
    with open(launcher_path, "w") as f:
        f.write(launcher_code)
    print(f"\n📝 Launcher written → {launcher_path}")
    return launcher_path


def create_zip_package():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name  = f"{APP_NAME}_secure_{timestamp}.zip"

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(ENCRYPTED_DIR):
            for fname in files:
                fpath  = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, ENCRYPTED_DIR)
                zf.write(fpath, arcname)

    print(f"\n📦 Distribution package → {zip_name}")
    return zip_name


# ─────────────────────────────────────────────────────────────
# SECTION 4 — Entry point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build and encrypt a PyInstaller macOS app in one step."
    )
    parser.add_argument("--password",  help="Optional password for key derivation")
    parser.add_argument("--windowed",  action="store_true", help="Build .app bundle (no console)")
    parser.add_argument("--onedir",    action="store_true", help="Build as directory instead of single file")
    args = parser.parse_args()

    try:
        # 1. Clean
        clean_previous_builds()

        # 2. Write app source
        write_app_source()

        # 3. Build
        built_files = build_with_pyinstaller(
            one_file=not args.onedir,
            windowed=args.windowed,
        )

        if not built_files:
            sys.exit("❌ PyInstaller produced no output files.")

        print("\n📁 Built files:")
        for f in built_files:
            size = os.path.getsize(f) if os.path.isfile(f) else "dir"
            print(f"   {f}  ({size} bytes)")

        # 4. Resolve the executable to encrypt
        main_binary = None
        for f in built_files:
            if args.windowed and f.endswith(".app"):
                candidate = os.path.join(f, "Contents", "MacOS", APP_NAME)
                if os.path.exists(candidate):
                    main_binary = candidate
            elif os.path.isfile(f):
                main_binary = f
            if main_binary:
                break

        if not main_binary:
            sys.exit("❌ Could not locate the executable to encrypt.")

        # 5. Encrypt
        enc_path, key_path, _ = encrypt_binary(main_binary, args.password)

        # 6. Verify
        if not verify_encryption(enc_path, key_path):
            sys.exit("❌ Encryption verification failed — aborting.")

        # 7. Launcher
        create_launcher(enc_path, key_path)

        # 8. Zip package
        package = create_zip_package()

        print("\n🎉 Done!")
        print(f"   Secure package: {package}")
        print("\n📋 Next steps:")
        print("   1. Share the .encrypted file")
        print("   2. Send the .key file via a separate secure channel")
        print("   3. Recipient runs launcher.py to decrypt and execute")

    except Exception as exc:
        import traceback
        print(f"\n❌ Fatal error: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up temp source file
        if os.path.isfile(APP_SCRIPT):
            os.remove(APP_SCRIPT)


if __name__ == "__main__":
    main()
