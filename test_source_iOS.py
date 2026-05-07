import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

TEST_APPS = [
    {"name": "Spotify",   "id": "324684580",  "slug": "spotify-music"},
    {"name": "Instagram", "id": "389801252",  "slug": "instagram"},
    {"name": "TikTok",    "id": "835599320",  "slug": "tiktok"},
]
PRIMARY = TEST_APPS[0]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

RESULTS: dict[str, dict] = {}


def safe_get(url, **kw):
    try:
        return SESSION.get(url, timeout=20, **kw)
    except Exception:
        return None


def record(source_name, accessible, versions_found, has_dates, has_notes, sample="", notes="", url=""):
    RESULTS[source_name] = {
        "accessible":     accessible,
        "versions_found": versions_found,
        "has_dates":      has_dates,
        "has_notes":      has_notes,
        "sample":         sample,
        "notes":          notes,
        "url":            url,
    }
    icon = "✅" if accessible and versions_found > 0 else ("⚠️ " if accessible else "❌")
    print(f"\n{icon} [{source_name}]")
    print(f"   accessible={accessible}  versions={versions_found}  dates={has_dates}  notes={has_notes}")
    if sample:
        print(f"   sample: {sample[:120]}")
    if notes:
        print(f"   note: {notes}")


def check_itunes():
    url = f"https://itunes.apple.com/lookup?id={PRIMARY['id']}&country=us"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("1_iTunes_API", False, 0, False, False, url=url)
        return
    d = r.json().get("results", [{}])[0]
    ver = d.get("version", "")
    date = d.get("currentVersionReleaseDate", "")
    notes = d.get("releaseNotes", "")
    record("1_iTunes_API", True, 1 if ver else 0, bool(date), bool(notes),
           f"v{ver} | {date} | notes_len={len(notes)}",
           "Only gives current version, no history.", url=url)


def check_appshopper():
    url = f"https://appshopper.com/app/{PRIMARY['slug']}/{PRIMARY['id']}"
    r = safe_get(url)
    if not r:
        record("2_AppShopper", False, 0, False, False, "Connection failed", url=url)
        return
    if r.status_code != 200:
        record("2_AppShopper", False, 0, False, False, f"HTTP {r.status_code}", url=url)
        return
    raw = r.text
    ver_matches = re.findall(r'(?:Version|v)\s*(\d+\.\d+[\.\d]*)', raw)
    date_matches = re.findall(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}', raw)
    note_matches = re.findall(r'"releaseNotes"\s*:\s*"([^"]{20,})"', raw)
    all_versions = list(set(ver_matches))
    record("2_AppShopper", True, len(all_versions), len(date_matches) > 2, len(note_matches) > 0,
           f"{len(all_versions)} versions, {len(date_matches)} dates, {len(note_matches)} note blocks",
           f"Status {r.status_code}, page_len={len(raw)}", url=url)


def check_appadvice():
    url = f"https://appadvice.com/app/{PRIMARY['slug']}/{PRIMARY['id']}"
    r = safe_get(url)
    if not r:
        record("3_AppAdvice", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}', raw)
    notes_present = "releaseNotes" in raw or "what's new" in raw.lower() or "whats new" in raw.lower()
    record("3_AppAdvice", r.status_code == 200, len(set(vers)), len(dates) > 2, notes_present,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)


def check_appagg():
    url = f"https://appagg.com/ios/{PRIMARY['slug']}/{PRIMARY['id']}/#whatsnew"
    r = safe_get(url)
    if not r:
        record("4_AppAgg", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    notes = re.findall(r'(?:release.notes|whats.new|what.s.new)[^>]*>([^<]{30,})', raw, re.I)
    record("4_AppAgg", r.status_code == 200, len(set(vers)), len(dates) > 2, len(notes) > 0,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates | {len(notes)} note blocks", url=url)


def check_appfollow():
    url = f"https://appfollow.io/apps/spotify-music/ios/{PRIMARY['id']}"
    r = safe_get(url)
    if not r:
        record("5_AppFollow", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    record("5_AppFollow", r.status_code == 200, len(set(vers)), len(dates) > 2, False,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
           "Often requires login for full history", url=url)


def check_apppure():
    url = f"https://apppure.com/en/ios/{PRIMARY['id']}/{PRIMARY['slug']}"
    r = safe_get(url)
    if not r:
        record("6_AppPure", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    notes = "history" in raw.lower() or "release notes" in raw.lower()
    record("6_AppPure", r.status_code == 200, len(set(vers)), len(dates) > 2, notes,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)


def check_iosnoops():
    url = f"https://www.iosnoops.com/{PRIMARY['name'].lower().replace(' ', '-')}-{PRIMARY['id']}/"
    r = safe_get(url)
    if not r:
        record("7_iOSnoops", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    record("7_iOSnoops", r.status_code == 200, len(set(vers)), len(dates) > 2, False,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)


def check_appmirror():
    url = f"https://www.appmirror.com/apk/{PRIMARY['slug']}/updates/"
    r = safe_get(url)
    if not r:
        record("8_AppMirror", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    record("8_AppMirror", r.status_code == 200, len(set(vers)), False, False,
           f"HTTP {r.status_code} | Android APK mirror, not iOS",
           "Android only — included as elimination check", url=url)


def check_wayback_cdx():
    url = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url=apps.apple.com/us/app/id{PRIMARY['id']}"
        f"&output=json&limit=20&from=20230101&statuscode=200"
    )
    r = safe_get(url)
    if not r:
        record("9_Wayback_CDX", False, 0, False, False, "Connection failed", url=url)
        return
    try:
        rows = r.json()
        data = rows[1:] if len(rows) > 1 else []
        ts_col = rows[0].index("timestamp") if rows else 1
        stamps = [row[ts_col] for row in data]
        record("9_Wayback_CDX", r.status_code == 200, 0, len(stamps) > 0, False,
               f"{len(stamps)} snapshots found | timestamps: {stamps[:3]}",
               "Timestamps only — need to fetch each snapshot for version/notes", url=url)
    except Exception as e:
        record("9_Wayback_CDX", r.status_code == 200, 0, False, False, f"Parse error: {e}", url=url)


def check_wayback_snapshot():
    snap_url = f"https://web.archive.org/web/20230604000000*/https://apps.apple.com/us/app/id{PRIMARY['id']}"
    r = safe_get(snap_url)
    if not r:
        record("10_Wayback_Snapshot", False, 0, False, False, "Connection failed", url=snap_url)
        return
    actual_snap = f"https://web.archive.org/web/20230604120000/https://apps.apple.com/us/app/id{PRIMARY['id']}"
    r2 = safe_get(actual_snap)
    if not r2:
        record("10_Wayback_Snapshot", False, 0, False, False, "Could not fetch actual snapshot", url=actual_snap)
        return
    raw = r2.text
    ver_m = re.search(r'"softwareVersion"\s*:\s*"([\d.]+)"', raw)
    notes_m = re.search(r'"releaseNotes"\s*:\s*"([^"]{20,200})"', raw)
    ver = ver_m.group(1) if ver_m else None
    notes = notes_m.group(1) if notes_m else None
    record("10_Wayback_Snapshot", r2.status_code == 200, 1 if ver else 0, True, bool(notes),
           f"version={ver} | notes={'YES: ' + notes[:60] if notes else 'not found'} | page_len={len(raw)}",
           "Single snapshot — scale up for full coverage", url=actual_snap)


def check_apple_rss():
    url = f"https://itunes.apple.com/us/rss/customerreviews/id={PRIMARY['id']}/sortBy=mostRecent/json"
    r = safe_get(url)
    record("11_Apple_Reviews_RSS", r is not None and r.status_code == 200, 0, False, False,
           f"HTTP {r.status_code if r else 'N/A'} — review RSS, not version history",
           "Elimination check only", url=url)


def check_appraven():
    url = f"https://www.appraven.net/app.php?itunes_id={PRIMARY['id']}"
    r = safe_get(url)
    if not r:
        record("12_AppRaven", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}|\b\w+ \d{1,2},? \d{4}\b', raw)
    notes = "version history" in raw.lower() or "release notes" in raw.lower() or "changelog" in raw.lower()
    record("12_AppRaven", r.status_code == 200, len(set(vers)), len(dates) > 2, notes,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)


def check_mobileaction():
    url = f"https://mobileaction.co/app-intelligence/{PRIMARY['id']}/ios/overview"
    r = safe_get(url)
    accessible = r is not None and r.status_code in (200, 301, 302)
    record("13_MobileAction", accessible, 0, False, False,
           f"HTTP {r.status_code if r else 'N/A'} — likely requires login",
           "Usually paywalled", url=url)


def check_appmagic():
    url = f"https://appmagic.rocks/app/{PRIMARY['id']}/ios"
    r = safe_get(url)
    if not r:
        record("14_AppMagic", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    record("14_AppMagic", r.status_code == 200, len(set(vers)), len(dates) > 2, False,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
           "May require login for history", url=url)


def check_appfollow_api():
    url = f"https://api.appfollow.io/apps?ext_id={PRIMARY['id']}&cid=us&device=ios"
    r = safe_get(url)
    if not r:
        record("15_AppFollow_API", False, 0, False, False, "Connection failed", url=url)
        return
    record("15_AppFollow_API", r.status_code == 200, 0, False, False,
           f"HTTP {r.status_code} | {r.text[:100]}", "Public API — may return data without key", url=url)


def check_itunes_variations():
    results = {}
    for country in ["us", "gb", "au", "de"]:
        url = f"https://itunes.apple.com/lookup?id={PRIMARY['id']}&country={country}&lang=en_us"
        r = safe_get(url)
        if r and r.status_code == 200:
            d = r.json().get("results", [{}])[0]
            results[country] = d.get("version", "?")
        time.sleep(0.5)
    record("16_iTunes_Countries", True, 1, True, False,
           f"Versions by country: {results}",
           "All countries return same single current version — no history via lookup API")


def check_appstore_page():
    url = f"https://apps.apple.com/us/app/id{PRIMARY['id']}"
    r = safe_get(url)
    if not r:
        record("17_AppStore_Page", False, 0, False, False, "Connection failed", url=url)
        return
    raw = r.text
    ver_m = re.search(r'"softwareVersion"\s*:\s*"([\d.]+)"', raw)
    notes_m = re.search(r'"releaseNotes"\s*:\s*"([^"]{20,500})"', raw)
    date_m = re.search(r'"datePublished"\s*:\s*"([\d\-T:Z]+)"', raw)
    record("17_AppStore_Page", r.status_code == 200,
           1 if ver_m else 0, bool(date_m), bool(notes_m),
           f"v={ver_m.group(1) if ver_m else '?'} | date={date_m.group(1) if date_m else '?'} | "
           f"notes={'YES' if notes_m else 'NO'}",
           "Only current version in JSON-LD — no history", url=url)


def check_changelog_sources():
    sources_to_try = [
        ("ReleasesNotes.io",  f"https://releasesnotes.io/ios/{PRIMARY['id']}"),
        ("AppChangelog",      f"https://www.appchangelog.com/ios/{PRIMARY['id']}"),
        ("WhatsNewOnIOS",     f"https://www.whatsnewonios.com/{PRIMARY['id']}"),
        ("iOSRelease",        f"https://iosrelease.com/app/{PRIMARY['id']}"),
    ]
    for site_name, url in sources_to_try:
        r = safe_get(url)
        key = f"18_{site_name.replace('.', '_').replace(' ', '_')}"
        if r:
            raw = r.text
            vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
            record(key, r.status_code == 200, len(set(vers)), len(dates) > 2,
                   "release notes" in raw.lower(),
                   f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)
        else:
            record(key, False, 0, False, False, "Connection failed", url=url)
        time.sleep(0.5)


def check_apptopia_variants():
    urls = [
        f"https://apptopia.com/ios/app/{PRIMARY['id']}/about",
        f"https://apptopia.com/ios/app/{PRIMARY['id']}/performance",
        f"https://apptopia.com/ios/app/{PRIMARY['id']}/history",
    ]
    for url in urls:
        r = safe_get(url)
        endpoint = url.split("/")[-1]
        if r:
            raw = r.text
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
            vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
            record(f"19_Apptopia_{endpoint}", r.status_code == 200, len(set(vers)), len(dates) > 2, False,
                   f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)
        else:
            record(f"19_Apptopia_{endpoint}", False, 0, False, False, "Failed", url=url)
        time.sleep(1)


def check_google_hint():
    record("20_Google_Scraping", False, 0, False, False, "",
           "Google blocks automated scraping (429/CAPTCHA). Use Custom Search API or skip.",
           url="https://www.google.com/search?q=spotify+ios+version+history+release+notes")


def print_summary():
    print("\n\n" + "═" * 80)
    print("  SOURCE DIAGNOSTIC SUMMARY")
    print("═" * 80)
    print(f"  {'Source':<35} {'OK':>4} {'Vers':>6} {'Dates':>6} {'Notes':>6}")
    print("  " + "─" * 58)

    winners = []
    for name, res in RESULTS.items():
        ok = "✅" if res["accessible"] and res["versions_found"] > 0 else ("🔓" if res["accessible"] else "❌")
        d  = "✅" if res["has_dates"] else "❌"
        n  = "✅" if res["has_notes"] else "❌"
        v  = str(res["versions_found"]) if res["versions_found"] else "-"
        print(f"  {name:<33} {ok:>4} {v:>6} {d:>6} {n:>6}")
        if res["accessible"] and res["versions_found"] > 0 and res["has_dates"]:
            winners.append(name)

    print("\n" + "═" * 80)
    print("  🏆 BEST SOURCES (accessible + version numbers + dates):")
    if winners:
        for w in winners:
            print(f"     → {w}  |  URL: {RESULTS[w]['url']}")
            if RESULTS[w]["has_notes"]:
                print(f"       ↳ Also has release NOTES!")
    else:
        print("     None found with all three criteria.")
        print("     Fallback: Wayback snapshots + LLM date estimation")
    print("═" * 80)


if __name__ == "__main__":
    print(f"iOS Source Diagnostic")
    print(f"App: {PRIMARY['name']} (id={PRIMARY['id']})")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    checks = [
        ("iTunes API",        check_itunes),
        ("AppShopper",        check_appshopper),
        ("AppAdvice",         check_appadvice),
        ("AppAgg",            check_appagg),
        ("AppFollow",         check_appfollow),
        ("AppPure",           check_apppure),
        ("iOSnoops",          check_iosnoops),
        ("AppMirror",         check_appmirror),
        ("Wayback CDX",       check_wayback_cdx),
        ("Wayback Snapshot",  check_wayback_snapshot),
        ("Apple RSS",         check_apple_rss),
        ("AppRaven",          check_appraven),
        ("MobileAction",      check_mobileaction),
        ("AppMagic",          check_appmagic),
        ("AppFollow API",     check_appfollow_api),
        ("iTunes Countries",  check_itunes_variations),
        ("AppStore Page",     check_appstore_page),
        ("Changelog Sites",   check_changelog_sources),
        ("Apptopia Variants", check_apptopia_variants),
        ("Google Hint",       check_google_hint),
    ]

    for label, fn in checks:
        print(f"\n{'─' * 60}")
        print(f"  {label}")
        print(f"{'─' * 60}")
        try:
            fn()
        except Exception as e:
            print(f"  !! Error in {label}: {e}")
        time.sleep(1.0)

    print_summary()

    with open("source_diagnostic_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\nSaved to: source_diagnostic_results.json")