"""
v1.2.0 release'e install.bat ekler.
Kullanim: python add_exe_asset.py <GITHUB_TOKEN>
"""
import json, os, sys, urllib.request, urllib.error

if len(sys.argv) < 2:
    print("Kullanim: python add_exe_asset.py <GITHUB_TOKEN>")
    sys.exit(1)

TOKEN = sys.argv[1]
USER  = "Xecutloner"
REPO  = "klavyemacro"
TAG   = "v1.2.0"
BASE  = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("install.bat",              os.path.join(BASE, "install.bat"),              "text/plain"),
    ("KlavyeMacro_setup.exe",    os.path.join(BASE, "dist", "KlavyeMacro_setup.exe"), "application/octet-stream"),
]

H = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "KlavyeMacro-Releaser/1.0"
}

# 1. Release ID'yi bul
print(f"[1] {TAG} release bilgisi aliniyor...")
req = urllib.request.Request(
    f"https://api.github.com/repos/{USER}/{REPO}/releases/tags/{TAG}",
    headers=H
)
with urllib.request.urlopen(req, timeout=15) as r:
    rel = json.loads(r.read())
upload_url = rel["upload_url"].replace("{?name,label}", "")
print(f"  Release: {rel['html_url']}")

# 2. Dosyalari yukle
print("[2] Dosyalar yukleniyor...")
for asset_name, filepath, content_type in FILES:
    if not os.path.exists(filepath):
        print(f"  ATLANDI (bulunamadi): {filepath}")
        continue
    size = os.path.getsize(filepath)
    print(f"  -> {asset_name} ({size//1024} KB) yukleniyor...")
    with open(filepath, "rb") as f:
        data = f.read()
    uh = {"Authorization": f"token {TOKEN}", "Content-Type": content_type,
          "User-Agent": "KlavyeMacro-Releaser/1.0"}
    req2 = urllib.request.Request(
        f"{upload_url}?name={asset_name}",
        data=data, headers=uh, method="POST"
    )
    try:
        with urllib.request.urlopen(req2, timeout=300) as r:
            ud = json.loads(r.read())
        print(f"     OK: {ud.get('browser_download_url', '?')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"     HATA ({e.code}): {body[:200]}")

print(f"\nTAMAMLANDI!")
print(f"https://github.com/{USER}/{REPO}/releases/tag/{TAG}")
