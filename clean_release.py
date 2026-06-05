"""
v1.2.0 release'den onefile EXE'leri siler, sadece ZIP + install.bat bırakır.
Kullanim: python clean_release.py <GITHUB_TOKEN>
"""
import json, os, sys, urllib.request, urllib.error

if len(sys.argv) < 2:
    print("Kullanim: python clean_release.py <GITHUB_TOKEN>")
    sys.exit(1)

TOKEN = sys.argv[1]
USER  = "Xecutloner"
REPO  = "klavyemacro"
TAG   = "v1.2.0"

# Silinecek asset adları (onefile EXE'ler - DLL sorunu yaratıyor)
TO_DELETE = {"KlavyeMacro.exe", "KlavyeMacro_setup.exe"}

H = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "KlavyeMacro-Releaser/1.0"
}

# 1. Release bilgisini al
print(f"[1] {TAG} asset listesi aliniyor...")
req = urllib.request.Request(
    f"https://api.github.com/repos/{USER}/{REPO}/releases/tags/{TAG}",
    headers=H
)
with urllib.request.urlopen(req, timeout=15) as r:
    rel = json.loads(r.read())

assets = rel.get("assets", [])
print(f"  Toplam asset: {len(assets)}")
for a in assets:
    print(f"  - {a['name']} ({a['size']//1024//1024} MB) id={a['id']}")

# 2. Problematik asset'leri sil
print(f"\n[2] Onefile EXE'ler siliniyor...")
for asset in assets:
    if asset["name"] in TO_DELETE:
        print(f"  Siliniyor: {asset['name']} (id={asset['id']})...")
        del_req = urllib.request.Request(
            f"https://api.github.com/repos/{USER}/{REPO}/releases/assets/{asset['id']}",
            headers=H, method="DELETE"
        )
        try:
            with urllib.request.urlopen(del_req, timeout=15) as r:
                pass
            print(f"  OK: {asset['name']} silindi")
        except urllib.error.HTTPError as e:
            print(f"  HATA ({e.code}): {e.read().decode()[:200]}")

print(f"\nTAMAMLANDI!")
print(f"https://github.com/{USER}/{REPO}/releases/tag/{TAG}")
