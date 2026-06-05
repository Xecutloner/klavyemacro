import urllib.request, json

url = "https://api.github.com/repos/Xecutloner/klavyemacro/releases/latest"
req = urllib.request.Request(url, headers={"User-Agent": "test", "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())

print("Tag:", data.get("tag_name"))
print("Assets:")
assets = data.get("assets", [])
if assets:
    for a in assets:
        print("  name =", a["name"])
        print("  size =", a["size"])
        print("  url  =", a["browser_download_url"])
else:
    print("  (asset YOK!)")
