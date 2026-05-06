"""
Android App Version History — Source Diagnostic
================================================
Tests all plausible public sources for version numbers, release dates,
and release notes across 15+ source categories.

Run:
    pip install requests beautifulsoup4 lxml
    python diagnose_android_sources.py

Output: printed summary + source_diagnostic_android.json
"""

import json, re, time
from datetime import datetime
from typing import Optional
import requests
from bs4 import BeautifulSoup

ANDROID_APPS = [
    {"name": "YouTube",             "pkg": "com.google.android.youtube",    "apkmirror_slug": "google-inc/youtube",                    "apkpure_slug": "youtube"},
    {"name": "TikTok",              "pkg": "com.zhiliaoapp.musically",       "apkmirror_slug": "tiktok-pte-ltd/tik-tok-including-musical-ly", "apkpure_slug": "tik-tok"},
    {"name": "ChatGPT",             "pkg": "com.openai.chatgpt",             "apkmirror_slug": "openai/chatgpt",                        "apkpure_slug": "chatgpt"},
    {"name": "Claude by Anthropic", "pkg": "com.anthropic.claude",           "apkmirror_slug": "anthropic/claude-ai",                   "apkpure_slug": "claude-ai"},
    {"name": "WhatsApp Messenger",  "pkg": "com.whatsapp",                   "apkmirror_slug": "whatsapp-inc/whatsapp",                  "apkpure_slug": "whatsapp-messenger"},
    {"name": "CapCut",              "pkg": "com.lemon.lvoverseas",            "apkmirror_slug": "tiktok-pte-ltd/capcut",                  "apkpure_slug": "capcut"},
    {"name": "Instagram",           "pkg": "com.instagram.android",          "apkmirror_slug": "instagram/instagram-instagram",          "apkpure_slug": "instagram"},
    {"name": "LinkedIn",            "pkg": "com.linkedin.android",           "apkmirror_slug": "linkedin/linkedin",                      "apkpure_slug": "linkedin"},
    {"name": "Tinder",              "pkg": "com.tinder",                     "apkmirror_slug": "tinder/tinder",                          "apkpure_slug": "tinder"},
    {"name": "Spotify",             "pkg": "com.spotify.music",              "apkmirror_slug": "spotify-ab/spotify-music",               "apkpure_slug": "spotify-music"},
]

PRIMARY = ANDROID_APPS[8]   # Tinder — mid-size, well-established

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

RESULTS: dict[str, dict] = {}

def safe_get(url, **kw):
    try:
        return SESSION.get(url, timeout=20, **kw)
    except Exception:
        return None

def vers_in(text):
    return len(set(re.findall(r'\b\d+\.\d+(?:\.\d+)*\b', text)))

def dates_in(text):
    return len(re.findall(
        r'\d{4}-\d{2}-\d{2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* \d{1,2},? \d{4}\b',
        text))

def notes_in(text):
    return bool(re.search(r'release notes|what.s new|changelog|whats new', text, re.I))

def record(name, accessible, versions, has_dates, has_notes, sample="", notes="", url=""):
    RESULTS[name] = {
        "accessible": accessible, "versions_found": versions,
        "has_dates": has_dates, "has_notes": has_notes,
        "sample": sample, "notes": notes, "url": url,
    }
    icon = "✅" if accessible and versions > 0 else ("⚠️ " if accessible else "❌")
    print(f"\n{icon} [{name}]")
    print(f"   accessible={accessible}  versions={versions}  dates={has_dates}  notes={has_notes}")
    if sample: print(f"   sample: {sample[:120]}")
    if notes:  print(f"   note: {notes}")

# ── 1. Google Play Store (official page) ──────────────────────────────────────
def check_play_store():
    app = PRIMARY
    url = f"https://play.google.com/store/apps/details?id={app['pkg']}&hl=en"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("1_Google_Play_Store", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    # Play Store embeds current version + notes in JSON-like structures
    ver_m   = re.search(r'\[\[\["(\d+\.\d+[\.\d]*)"\]\]', raw)
    notes_m = re.search(r'"What.s New".*?"([^"]{30,500})"', raw, re.S)
    ver = ver_m.group(1) if ver_m else ""
    record("1_Google_Play_Store", True, 1 if ver else vers_in(raw),
           False, bool(notes_m) or notes_in(raw),
           f"ver={ver} | page_len={len(raw)}",
           "Only current version + notes — no history", url=url)

# ── 2. APKMirror (version list page) ─────────────────────────────────────────
def check_apkmirror_list():
    app = PRIMARY
    url = f"https://www.apkmirror.com/apk/{app['apkmirror_slug']}/"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("2_APKMirror_list", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    v = vers_in(raw); d = dates_in(raw)
    # APKMirror lists versions in blocks like "9.1.44 (Android 5.0+)"
    ver_entries = re.findall(r'(\d+\.\d+[\.\d]*)\s*\(Android', raw)
    record("2_APKMirror_list", True, len(set(ver_entries)) or v, d > 0, False,
           f"{len(set(ver_entries))} vers with Android tag | {d} dates | page_len={len(raw)}",
           url=url)

# ── 3. APKMirror (paginated — page 2 to check depth) ─────────────────────────
def check_apkmirror_paged():
    app = PRIMARY
    url = f"https://www.apkmirror.com/apk/{app['apkmirror_slug']}/page/2/"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("3_APKMirror_page2", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    ver_entries = re.findall(r'(\d+\.\d+[\.\d]*)\s*\(Android', raw)
    d = dates_in(raw)
    record("3_APKMirror_page2", True, len(set(ver_entries)), d > 0, False,
           f"{len(set(ver_entries))} vers page 2 | {d} dates",
           "Pagination works — can scrape N pages for full history", url=url)

# ── 4. APKMirror individual release page (version + notes check) ──────────────
def check_apkmirror_release():
    app = PRIMARY
    # First get the list, then try clicking into one release
    list_url = f"https://www.apkmirror.com/apk/{app['apkmirror_slug']}/"
    r = safe_get(list_url)
    if not r or r.status_code != 200:
        record("4_APKMirror_release", False, 0, False, False, url=list_url)
        return
    soup = BeautifulSoup(r.text, "lxml")
    # Find first release link
    link = soup.select_one("a.fontBlack")
    if not link or not link.get("href"):
        record("4_APKMirror_release", True, 0, False, False,
               "Could not find release link on list page", url=list_url)
        return
    rel_url = "https://www.apkmirror.com" + link["href"]
    r2 = safe_get(rel_url)
    time.sleep(1)
    if not r2 or r2.status_code != 200:
        record("4_APKMirror_release", False, 0, False, False, f"HTTP {r2.status_code if r2 else 'N/A'}", url=rel_url)
        return
    raw2 = r2.text
    ver_m   = re.search(r'(\d+\.\d+[\.\d]*)', link.get_text())
    date_m  = re.search(r'\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* \d{1,2},? \d{4}', raw2)
    notes_m = re.search(r'(?:What.s New|Release Notes|Changelog)[^>]*>([^<]{20,500})', raw2, re.I | re.S)
    record("4_APKMirror_release", True,
           1 if ver_m else 0, bool(date_m), bool(notes_m),
           f"ver={ver_m.group(1) if ver_m else '?'} | date={date_m.group() if date_m else '?'} | notes={'YES: '+notes_m.group(1)[:60] if notes_m else 'NO'}",
           url=rel_url)

# ── 5. APKPure (version list) ─────────────────────────────────────────────────
def check_apkpure_list():
    app = PRIMARY
    url = f"https://apkpure.com/{app['apkpure_slug']}/{app['pkg']}/versions"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("5_APKPure_list", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    v = vers_in(raw); d = dates_in(raw)
    record("5_APKPure_list", True, v, d > 2, notes_in(raw),
           f"{v} vers | {d} dates | page_len={len(raw)}", url=url)

# ── 6. APKPure individual app page ────────────────────────────────────────────
def check_apkpure_main():
    app = PRIMARY
    url = f"https://apkpure.com/{app['apkpure_slug']}/{app['pkg']}"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("6_APKPure_main", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    v = vers_in(raw); d = dates_in(raw)
    n = notes_in(raw)
    record("6_APKPure_main", True, v, d > 2, n,
           f"{v} vers | {d} dates | notes={'YES' if n else 'NO'} | page_len={len(raw)}", url=url)

# ── 7. Apptopia Android ───────────────────────────────────────────────────────
def check_apptopia_android():
    app = PRIMARY
    url = f"https://apptopia.com/google-play/app/{app['pkg']}/about"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("7_Apptopia_Android", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    v = vers_in(raw); d = dates_in(raw)
    record("7_Apptopia_Android", True, v, d > 2, notes_in(raw),
           f"{v} vers | {d} dates | page_len={len(raw)}", url=url)

# ── 8. AppBrain ───────────────────────────────────────────────────────────────
def check_appbrain():
    app = PRIMARY
    url = f"https://www.appbrain.com/app/{app['apkpure_slug']}/{app['pkg']}"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("8_AppBrain", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    v = vers_in(raw); d = dates_in(raw)
    record("8_AppBrain", True, v, d > 2, notes_in(raw),
           f"{v} vers | {d} dates | page_len={len(raw)}", url=url)

# ── 9. AppBrain version history tab ───────────────────────────────────────────
def check_appbrain_history():
    app = PRIMARY
    url = f"https://www.appbrain.com/app/{app['apkpure_slug']}/{app['pkg']}/history"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("9_AppBrain_history", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    raw = r.text
    v = vers_in(raw); d = dates_in(raw)
    record("9_AppBrain_history", True, v, d > 2, notes_in(raw),
           f"{v} vers | {d} dates | page_len={len(raw)}", url=url)

# ── 10. Google Play unofficial JSON endpoint ──────────────────────────────────
def check_play_json():
    app = PRIMARY
    # Unofficial gplayapi-style endpoint (no auth)
    url = f"https://play.google.com/store/apps/details?id={app['pkg']}&hl=en&gl=us"
    r = safe_get(url, headers={"Accept": "application/json"})
    if not r:
        record("10_Play_JSON_endpoint", False, 0, False, False, url=url)
        return
    # Check if there's any version data in response
    raw = r.text
    # Play embeds data in JS arrays — look for version patterns in dataset
    ver_m = re.search(r'"(\d+\.\d+[\.\d]*)"', raw)
    record("10_Play_JSON_endpoint", r.status_code==200, 1 if ver_m else 0, False, notes_in(raw),
           f"HTTP {r.status_code} | ver_found={bool(ver_m)} | page_len={len(raw)}",
           "Same as Play Store HTML — single version", url=url)

# ── 11. Wayback CDX for Google Play ──────────────────────────────────────────
def check_wayback_play_cdx():
    app = PRIMARY
    url = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url=play.google.com/store/apps/details%3Fid%3D{app['pkg']}"
        f"&output=json&limit=20&from=20230101"
    )
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("11_Wayback_Play_CDX", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=url)
        return
    try:
        rows = r.json()
        data = rows[1:] if len(rows) > 1 else []
        ts_col = rows[0].index("timestamp") if rows else 1
        stamps = [row[ts_col] for row in data]
        record("11_Wayback_Play_CDX", True, 0, len(stamps) > 0, False,
               f"{len(stamps)} Play Store snapshots | {stamps[:3]}",
               "Fetch snapshots for version extraction", url=url)
    except Exception as e:
        record("11_Wayback_Play_CDX", True, 0, False, False, f"Parse err: {e}", url=url)

# ── 12. Wayback snapshot content — Play Store page ────────────────────────────
def check_wayback_play_snap():
    app = PRIMARY
    snap_url = f"https://web.archive.org/web/20230601120000/https://play.google.com/store/apps/details?id={app['pkg']}&hl=en"
    r = safe_get(snap_url)
    if not r or r.status_code not in (200, 302):
        record("12_Wayback_Play_snap", False, 0, False, False, f"HTTP {r.status_code if r else 'N/A'}", url=snap_url)
        return
    raw = r.text
    ver_m   = re.search(r'"(\d+\.\d+[\.\d]*)"', raw)
    notes_m = re.search(r'(?:What.s New|Recent changes)[^>]*>(.*?)</div>', raw, re.S | re.I)
    record("12_Wayback_Play_snap", True,
           1 if ver_m else 0, False, bool(notes_m),
           f"ver={ver_m.group(1) if ver_m else '?'} | notes={'YES' if notes_m else 'NO'} | page_len={len(raw)}",
           "Single snapshot test — scale for history", url=snap_url)

# ── 13. APKMirror changelog/whatsnew tab ─────────────────────────────────────
def check_apkmirror_whatsnew():
    app = PRIMARY
    list_url = f"https://www.apkmirror.com/apk/{app['apkmirror_slug']}/"
    r = safe_get(list_url)
    if not r or r.status_code != 200:
        record("13_APKMirror_whatsnew", False, 0, False, False, url=list_url)
        return
    soup = BeautifulSoup(r.text, "lxml")
    # APKMirror embeds changelog on release pages via "What's new" sections
    wn_blocks = soup.select("div.whatsnew, div[class*='whats'], section[class*='new']")
    wn_text = " ".join(b.get_text() for b in wn_blocks)
    record("13_APKMirror_whatsnew", True, vers_in(r.text), dates_in(r.text) > 0, bool(wn_blocks),
           f"{len(wn_blocks)} what's-new blocks found | sample: {wn_text[:80]}",
           "Release-level notes — need to fetch each release page", url=list_url)

# ── 14. AppFollow Android public page ────────────────────────────────────────
def check_appfollow_android():
    app = PRIMARY
    url = f"https://appfollow.io/apps/{app['apkpure_slug']}/android/{app['pkg']}"
    r = safe_get(url)
    if not r:
        record("14_AppFollow_Android", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    record("14_AppFollow_Android", r.status_code==200, vers_in(raw), dates_in(raw)>2, notes_in(raw),
           f"HTTP {r.status_code} | {vers_in(raw)} vers | {dates_in(raw)} dates", url=url)

# ── 15. AppShopper Android ────────────────────────────────────────────────────
def check_appshopper_android():
    app = PRIMARY
    url = f"https://appshopper.com/android/app/{app['apkpure_slug']}/{app['pkg']}"
    r = safe_get(url)
    if not r:
        record("15_AppShopper_Android", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    record("15_AppShopper_Android", r.status_code==200, vers_in(raw), dates_in(raw)>2, notes_in(raw),
           f"HTTP {r.status_code} | {vers_in(raw)} vers | {dates_in(raw)} dates", url=url)

# ── 16. Google Play unofficial gplay-scraper style endpoint ──────────────────
def check_play_internal_api():
    """Test the internal batch endpoint Google Play UI uses."""
    app = PRIMARY
    url  = "https://play.google.com/_/PlayStoreUi/data/batchexecute"
    body = f'f.req=%5B%5B%5B%22xdSrCf%22%2C%22%5B%5B%5B%5C%22{app["pkg"]}%5C%22%2C7%5D%5D%5D%22%2Cnull%2C%221%22%5D%5D%5D'
    try:
        r = SESSION.post(url, data=body,
                         headers={"Content-Type": "application/x-www-form-urlencoded"},
                         timeout=15)
        raw = r.text
        ver_m = re.search(r'"(\d+\.\d+[\.\d]*)"', raw)
        record("16_Play_batchexecute", r.status_code==200,
               1 if ver_m else 0, False, False,
               f"HTTP {r.status_code} | ver={ver_m.group(1) if ver_m else '?'} | len={len(raw)}",
               "Internal API — may return structured data if not blocked", url=url)
    except Exception as e:
        record("16_Play_batchexecute", False, 0, False, False, str(e)[:80], url=url)

# ── 17. APKCombo ──────────────────────────────────────────────────────────────
def check_apkcombo():
    app = PRIMARY
    url = f"https://apkcombo.com/apk-downloader/?package={app['pkg']}"
    r = safe_get(url)
    if not r:
        record("17_APKCombo", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    record("17_APKCombo", r.status_code==200, vers_in(raw), dates_in(raw)>2, notes_in(raw),
           f"HTTP {r.status_code} | {vers_in(raw)} vers | {dates_in(raw)} dates", url=url)

# ── 18. APK Fab ───────────────────────────────────────────────────────────────
def check_apkfab():
    app = PRIMARY
    url = f"https://apkfab.com/apk/{app['apkpure_slug']}/{app['pkg']}"
    r = safe_get(url)
    if not r:
        record("18_APKFab", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    record("18_APKFab", r.status_code==200, vers_in(raw), dates_in(raw)>2, notes_in(raw),
           f"HTTP {r.status_code} | {vers_in(raw)} vers | {dates_in(raw)} dates", url=url)

# ── 19. APKFab version list ───────────────────────────────────────────────────
def check_apkfab_versions():
    app = PRIMARY
    url = f"https://apkfab.com/apk/{app['apkpure_slug']}/{app['pkg']}/versions"
    r = safe_get(url)
    if not r:
        record("19_APKFab_versions", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    record("19_APKFab_versions", r.status_code==200, vers_in(raw), dates_in(raw)>2, notes_in(raw),
           f"HTTP {r.status_code} | {vers_in(raw)} vers | {dates_in(raw)} dates", url=url)

# ── 20. Multi-app spot check (run winner sources on all 10 apps) ──────────────
def check_all_apps_on_winners():
    """After individual checks, spot-test the best source on all 10 apps."""
    print("\n\n" + "─"*66)
    print("  Multi-app spot check: APKMirror + APKPure on all 10 apps")
    print("─"*66)
    for app in ANDROID_APPS:
        results = {}
        for label, url in [
            ("APKMirror", f"https://www.apkmirror.com/apk/{app['apkmirror_slug']}/"),
            ("APKPure",   f"https://apkpure.com/{app['apkpure_slug']}/{app['pkg']}/versions"),
            ("Apptopia",  f"https://apptopia.com/google-play/app/{app['pkg']}/about"),
        ]:
            r = safe_get(url)
            if r and r.status_code == 200:
                v = vers_in(r.text)
                d = dates_in(r.text)
                results[label] = f"v={v}, d={d}"
            else:
                results[label] = f"HTTP {r.status_code if r else 'ERR'}"
            time.sleep(0.8)
        parts = " | ".join(f"{k}: {v}" for k, v in results.items())
        print(f"  {app['name']:<22} {parts}")
        time.sleep(1.0)

def print_summary():
    print("\n\n" + "═"*78)
    print("  ANDROID SOURCE DIAGNOSTIC SUMMARY")
    print("═"*78)
    header = f"  {'Source':<35} {'OK':>4} {'Vers':>6} {'Dates':>6} {'Notes':>6}"
    print(header)
    print("  " + "─"*58)
    winners = []
    for name, res in RESULTS.items():
        ok = "✅" if res["accessible"] and res["versions_found"] > 0 else ("🔓" if res["accessible"] else "❌")
        d  = "✅" if res["has_dates"] else "❌"
        n  = "✅" if res["has_notes"] else "❌"
        v  = str(res["versions_found"]) if res["versions_found"] else "-"
        print(f"  {name:<35} {ok:>4} {v:>6} {d:>6} {n:>6}")
        if res["accessible"] and res["versions_found"] > 0 and res["has_dates"]:
            winners.append(name)

    print("\n" + "═"*78)
    print("  🏆 BEST SOURCES (accessible + versions + dates):")
    if winners:
        for w in winners:
            print(f"     → {w}")
            print(f"       URL: {RESULTS[w]['url']}")
            if RESULTS[w]["has_notes"]:
                print(f"       ↳ Also has release NOTES!")
    else:
        print("     None found with all three criteria.")
    print("═"*78)

if __name__ == "__main__":
    print(f"Android Version History — Source Diagnostic")
    print(f"Test app: {PRIMARY['name']} ({PRIMARY['pkg']})")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    checks = [
        ("Google Play Store",           check_play_store),
        ("APKMirror list",              check_apkmirror_list),
        ("APKMirror page 2",            check_apkmirror_paged),
        ("APKMirror release page",      check_apkmirror_release),
        ("APKPure versions",            check_apkpure_list),
        ("APKPure main",                check_apkpure_main),
        ("Apptopia Android",            check_apptopia_android),
        ("AppBrain",                    check_appbrain),
        ("AppBrain history",            check_appbrain_history),
        ("Play JSON endpoint",          check_play_json),
        ("Wayback Play CDX",            check_wayback_play_cdx),
        ("Wayback Play snapshot",       check_wayback_play_snap),
        ("APKMirror whats new",         check_apkmirror_whatsnew),
        ("AppFollow Android",           check_appfollow_android),
        ("AppShopper Android",          check_appshopper_android),
        ("Play batchexecute API",       check_play_internal_api),
        ("APKCombo",                    check_apkcombo),
        ("APKFab main",                 check_apkfab),
        ("APKFab versions",             check_apkfab_versions),
    ]

    for label, fn in checks:
        print(f"\n{'─'*58}")
        print(f"  Checking: {label}")
        print(f"{'─'*58}")
        try:
            fn()
        except Exception as e:
            print(f"  !! Error: {e}")
        time.sleep(1.2)

    print_summary()
    check_all_apps_on_winners()

    with open("source_diagnostic_android.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\nResults saved to: source_diagnostic_android.json")