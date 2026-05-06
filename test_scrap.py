import requests, json

app_ids = [544007664, 835599320, 6448311069, 6473753684, 310633997,
           1500855883, 389801252, 288429040, 547702041, 324684580]
## 1. Youtube, 2. Tiktok, 3. chatgpt, 4. claude, 5. whatsapp, 6. capcut, 7. instagram, 8. linkedin, 9. tinder, 10. spotify

results = []
for app_id in app_ids:
    r = requests.get(f"https://itunes.apple.com/lookup?id={app_id}")
    data = r.json()["results"][0]
    results.append({
        "app_name": data["trackName"],
        "developer": data["artistName"],
        "category": data["primaryGenreName"],
        "current_version": data["version"],
        "current_release_date": data["currentVersionReleaseDate"],
        "initial_release_date": data["releaseDate"],
        "release_notes": data["releaseNotes"]
    })

print(json.dumps(results, indent=2))