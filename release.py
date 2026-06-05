"""
release.py - KlavyeMacro yeni surum cikartma scripti
Kullanim: python release.py <TOKEN> <VERSIYON>
Ornek:    python release.py ghp_xxx... 1.1.0
"""
import json, os, subprocess, sys, urllib.request, urllib.error

if len(sys.argv) < 3:
    print("Kullanim: python release.py <GITHUB_TOKEN> <VERSIYON>")
    print("Ornek:    python release.py ghp_xxx... 1.1.0")
    sys.exit(1)

TOKEN   = sys.argv[1]
VERSION = sys.argv[2].lstrip("v")
TAG     = f"v{VERSION}"
USER    = "Xecutloner"
REPO    = "klavyemacro"
BASE    = os.path.dirname(os.path.abspath(__file__))
EXE     = os.path.join(BASE, "dist", "KlavyeMacro.exe")

H = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json",
     "Content-Type": "application/json", "User-Agent": "KlavyeMacro-Releaser/1.0"}

def api(m, url, body=None):
    d = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=d, headers=H, method=m)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print("  ", out[:200])
    return r.returncode == 0

print(f"\nKlavyeMacro {TAG} release basliyor...\n")

# 1. Commit ve push
print("[1] Kod push'laniyor...")
remote = f"https://{TOKEN}@github.com/{USER}/{REPO}.git"
sh(f'git remote set-url origin "{remote}"')
sh("git add .")
sh(f'git commit -m "Release {TAG}"')
sh("git push origin main")
print("  OK")

# 2. Release olustur
print(f"[2] GitHub Release {TAG} olusturuluyor...")
rel, s = api("POST", f"https://api.github.com/repos/{USER}/{REPO}/releases", {
    "tag_name": TAG,
    "name": f"KlavyeMacro {TAG}",
    "body": (
        f"## KlavyeMacro {TAG}\n\n"
        "### Duzeltmeler\n\n"
        "- **KRITIK PATCH:** Guncelleyici ile v1.1.0 yuklenince 'Failed to load Python DLL' hatasi veren sorun giderildi\n"
        "  - PyInstaller runtime dosyalari artik Windows Temp klasoru yerine EXE'nin yanina cikariliyor\n"
        "  - Antivirus ve Windows Temp temizleyicilerin python311.dll'i silmesi artik soruna yol acmiyor\n"
        "- v1.1.0'daki klavye koruma ozellikleri (keyboard_guard) korundu\n\n"
        "### Nasil Guncellenir\n\n"
        "**v1.0.0 kullanicilari:** Uygulama icerisinden Ayarlar -> Guncelleme Kontrol Et -> Indir ve Yukle\n\n"
        "**v1.1.0 kullanicilari (DLL hatasi alanlar):** "
        "Asagidaki EXE'yi indirip eskisinin uzerine kopyalayin - bu sefer hata olmayacak.\n\n"
        "Makrolariniz ve ayarlariniz korunur."
    ),
    "draft": False
})
if s == 201:
    upload_url = rel["upload_url"].replace("{?name,label}", "")
    print(f"  OK {rel['html_url']}")
else:
    print(f"  ERR ({s}): {rel}")
    sys.exit(1)

# 3. EXE yukle
size_mb = os.path.getsize(EXE) // 1048576
print(f"[3] EXE yukleniyor ({size_mb} MB)...")
with open(EXE, "rb") as f:
    exe_data = f.read()
uh = {"Authorization": f"token {TOKEN}", "Content-Type": "application/octet-stream",
      "User-Agent": "KlavyeMacro-Releaser/1.0"}
req = urllib.request.Request(f"{upload_url}?name=KlavyeMacro.exe",
                             data=exe_data, headers=uh, method="POST")
with urllib.request.urlopen(req, timeout=300) as r:
    ud = json.loads(r.read())
print(f"  OK {ud.get('browser_download_url', '?')}")

print(f"\nTAMAMLANDI! {TAG} yayinda.")
print(f"https://github.com/{USER}/{REPO}/releases/tag/{TAG}")
