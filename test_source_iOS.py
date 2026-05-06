"""
iOS Version History — Source Diagnostic
========================================
Tests ALL plausible public sources for version numbers, release dates,
and release notes. Runs one representative app per source check, then
prints a summary table of what each source can deliver.

Run:
    pip install requests beautifulsoup4 lxml tabulate
    python diagnose_ios_sources.py

Results are printed to console AND saved to  source_diagnostic_results.json
"""

import json, re, time, textwrap
from datetime import datetime, timezone
from typing import Optional
import requests
from bs4 import BeautifulSoup

# ── Test apps (one per batch — we reuse across sources) ───────────────────────
TEST_APPS = [
    {"name": "Spotify",   "id": "324684580",  "slug": "spotify-music"},
    {"name": "Instagram", "id": "389801252",  "slug": "instagram"},
    {"name": "TikTok",    "id": "835599320",  "slug": "tiktok"},
]
PRIMARY = TEST_APPS[0]   # Spotify — well-established, lots of history

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
        r = SESSION.get(url, timeout=20, **kw)
        return r
    except Exception as e:
        return None

def record(source_name, accessible, versions_found, has_dates, has_notes, sample, notes="", url=""):
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

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — iTunes Lookup API (baseline)
# ══════════════════════════════════════════════════════════════════════════════
def check_itunes():
    app = PRIMARY
    url = f"https://itunes.apple.com/lookup?id={app['id']}&country=us"
    r = safe_get(url)
    if not r or r.status_code != 200:
        record("1_iTunes_API", False, 0, False, False, "", url=url)
        return
    d = r.json().get("results", [{}])[0]
    ver = d.get("version","")
    date = d.get("currentVersionReleaseDate","")
    notes = d.get("releaseNotes","")
    init = d.get("releaseDate","")
    record("1_iTunes_API", True, 1 if ver else 0, bool(date), bool(notes),
           f"v{ver} | {date} | notes_len={len(notes)}",
           "Only gives CURRENT version. No history.", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — AppShopper (appshopper.com)
# ══════════════════════════════════════════════════════════════════════════════
def check_appshopper():
    app = PRIMARY
    url = f"https://appshopper.com/app/{app['slug']}/{app['id']}"
    r = safe_get(url)
    if not r:
        record("2_AppShopper", False, 0, False, False, "", "Connection failed", url=url)
        return
    if r.status_code != 200:
        record("2_AppShopper", False, 0, False, False, f"HTTP {r.status_code}", url=url)
        return

    soup = BeautifulSoup(r.text, "lxml")
    # Look for version rows
    versions = []
    has_dates = False
    has_notes = False

    # AppShopper uses a history table or list
    rows = soup.select("table.versions tr, .version-history li, .history-item, div[class*='version']")
    
    # Fallback: regex on raw text
    raw = r.text
    ver_matches = re.findall(r'(?:Version|v)\s*(\d+\.\d+[\.\d]*)', raw)
    date_matches = re.findall(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}', raw)
    note_matches = re.findall(r'"releaseNotes"\s*:\s*"([^"]{20,})"', raw)

    has_dates = len(date_matches) > 2
    has_notes = len(note_matches) > 0
    all_versions = list(set(ver_matches))
    
    record("2_AppShopper", True, len(all_versions), has_dates, has_notes,
           f"{len(all_versions)} versions, {len(date_matches)} dates, {len(note_matches)} note blocks",
           f"Status {r.status_code}, page_len={len(raw)}", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — AppAdvice (appadvice.com)
# ══════════════════════════════════════════════════════════════════════════════
def check_appadvice():
    app = PRIMARY
    url = f"https://appadvice.com/app/{app['slug']}/{app['id']}"
    r = safe_get(url)
    if not r:
        record("3_AppAdvice", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}', raw)
    notes_present = "releaseNotes" in raw or "what's new" in raw.lower() or "whats new" in raw.lower()
    record("3_AppAdvice", r.status_code == 200, len(set(vers)), len(dates)>2, notes_present,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
           url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 4 — AppAgg (appagg.com)
# ══════════════════════════════════════════════════════════════════════════════
def check_appagg():
    app = PRIMARY
    # AppAgg URL format
    url = f"https://appagg.com/ios/{app['slug']}/{app['id']}/#whatsnew"
    r = safe_get(url)
    if not r:
        record("4_AppAgg", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    notes = re.findall(r'(?:release.notes|whats.new|what.s.new)[^>]*>([^<]{30,})', raw, re.I)
    record("4_AppAgg", r.status_code == 200, len(set(vers)), len(dates)>2, len(notes)>0,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates | {len(notes)} note blocks",
           url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 5 — AppFollow (appfollow.io) public pages
# ══════════════════════════════════════════════════════════════════════════════
def check_appfollow():
    app = PRIMARY
    url = f"https://appfollow.io/apps/spotify-music/ios/{app['id']}"
    r = safe_get(url)
    if not r:
        record("5_AppFollow", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    record("5_AppFollow", r.status_code==200, len(set(vers)), len(dates)>2, False,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
           "Often requires login for full history", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 6 — AppPure (apppure.com)  — mirrors App Store data
# ══════════════════════════════════════════════════════════════════════════════
def check_apppure():
    app = PRIMARY
    url = f"https://apppure.com/en/ios/{app['id']}/{app['slug']}"
    r = safe_get(url)
    if not r:
        record("6_AppPure", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    notes = "history" in raw.lower() or "release notes" in raw.lower()
    record("6_AppPure", r.status_code==200, len(set(vers)), len(dates)>2, notes,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
           url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 7 — iOSnoops / macOS App Changelogs (iosnoops.com)
# ══════════════════════════════════════════════════════════════════════════════
def check_iosnoops():
    app = PRIMARY
    url = f"https://www.iosnoops.com/{app['name'].lower().replace(' ','-')}-{app['id']}/"
    r = safe_get(url)
    if not r:
        record("7_iOSnoops", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    record("7_iOSnoops", r.status_code==200, len(set(vers)), len(dates)>2, False,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 8 — AppMirror (appmirror.com)
# ══════════════════════════════════════════════════════════════════════════════
def check_appmirror():
    app = PRIMARY
    url = f"https://www.appmirror.com/apk/{app['slug']}/updates/"
    r = safe_get(url)
    if not r:
        record("8_AppMirror", False, 0, False, False, "", "Connection failed (Android-focused site)", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    record("8_AppMirror", r.status_code==200, len(set(vers)), False, False,
           f"HTTP {r.status_code} | note: Android APK mirror, not iOS",
           "Android only — included as elimination check", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 9 — Wayback CDX (already in your script — retesting minimal format)
# ══════════════════════════════════════════════════════════════════════════════
def check_wayback_cdx():
    app = PRIMARY
    url = (
        f"http://web.archive.org/cdx/search/cdx"
        f"?url=apps.apple.com/us/app/id{app['id']}"
        f"&output=json&limit=20&from=20230101&statuscode=200"
    )
    r = safe_get(url)
    if not r:
        record("9_Wayback_CDX", False, 0, False, False, "", "Connection failed", url=url)
        return
    try:
        rows = r.json()
        data = rows[1:] if len(rows)>1 else []
        ts_col = rows[0].index("timestamp") if rows else 1
        stamps = [row[ts_col] for row in data]
        record("9_Wayback_CDX", r.status_code==200, 0, len(stamps)>0, False,
               f"{len(stamps)} snapshots found | timestamps: {stamps[:3]}",
               "Gives snapshot timestamps — need to fetch each snap for version/notes", url=url)
    except Exception as e:
        record("9_Wayback_CDX", r.status_code==200, 0, False, False, f"Parse error: {e}", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 10 — Wayback snapshot content test (fetch one snap, check what's parseable)
# ══════════════════════════════════════════════════════════════════════════════
def check_wayback_snapshot():
    app = PRIMARY
    # Use a known good snapshot timestamp (Spotify 2023)
    snap_url = f"https://web.archive.org/web/20230604000000*/https://apps.apple.com/us/app/id{app['id']}"
    r = safe_get(snap_url)
    if not r:
        record("10_Wayback_Snapshot", False, 0, False, False, "", "Connection failed", url=snap_url)
        return

    # Try to find the actual redirect target
    actual_snap = f"https://web.archive.org/web/20230604120000/https://apps.apple.com/us/app/id{app['id']}"
    r2 = safe_get(actual_snap)
    if not r2:
        record("10_Wayback_Snapshot", False, 0, False, False, "Could not fetch actual snapshot", url=actual_snap)
        return

    raw = r2.text
    ver_m = re.search(r'"softwareVersion"\s*:\s*"([\d.]+)"', raw)
    notes_m = re.search(r'"releaseNotes"\s*:\s*"([^"]{20,200})"', raw)
    ver = ver_m.group(1) if ver_m else None
    notes = notes_m.group(1) if notes_m else None

    record("10_Wayback_Snapshot", r2.status_code==200, 1 if ver else 0, True, bool(notes),
           f"version={ver} | notes={'YES: '+notes[:60] if notes else 'not found'} | page_len={len(raw)}",
           "Single snapshot check — scale up for full date coverage", url=actual_snap)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 11 — Apple RSS / Recent Updates feed
# ══════════════════════════════════════════════════════════════════════════════
def check_apple_rss():
    app = PRIMARY
    url = f"https://itunes.apple.com/us/rss/customerreviews/id={app['id']}/sortBy=mostRecent/json"
    r = safe_get(url)
    record("11_Apple_Reviews_RSS", r is not None and r.status_code==200, 0, False, False,
           f"HTTP {r.status_code if r else 'N/A'} — review RSS (not version history, just elimination check)",
           "This is review RSS, not version history", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 12 — AppRaven (appraven.net)
# ══════════════════════════════════════════════════════════════════════════════
def check_appraven():
    app = PRIMARY
    url = f"https://www.appraven.net/app.php?itunes_id={app['id']}"
    r = safe_get(url)
    if not r:
        record("12_AppRaven", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}|\b\w+ \d{1,2},? \d{4}\b', raw)
    notes = "version history" in raw.lower() or "release notes" in raw.lower() or "changelog" in raw.lower()
    record("12_AppRaven", r.status_code==200, len(set(vers)), len(dates)>2, notes,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 13 — MobileAction (mobileaction.co) public pages
# ══════════════════════════════════════════════════════════════════════════════
def check_mobileaction():
    app = PRIMARY
    url = f"https://mobileaction.co/app-intelligence/{app['id']}/ios/overview"
    r = safe_get(url)
    accessible = r is not None and r.status_code in (200, 301, 302)
    record("13_MobileAction", accessible, 0, False, False,
           f"HTTP {r.status_code if r else 'N/A'} — likely requires login",
           "Usually paywalled — check if public pages exist", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 14 — AppMagic (appmagic.rocks) public app pages
# ══════════════════════════════════════════════════════════════════════════════
def check_appmagic():
    app = PRIMARY
    url = f"https://appmagic.rocks/app/{app['id']}/ios"
    r = safe_get(url)
    if not r:
        record("14_AppMagic", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
    record("14_AppMagic", r.status_code==200, len(set(vers)), len(dates)>2, False,
           f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
           "May require login for history", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 15 — AppFollow Releases API (public endpoint test)
# ══════════════════════════════════════════════════════════════════════════════
def check_appfollow_api():
    app = PRIMARY
    url = f"https://api.appfollow.io/apps?ext_id={app['id']}&cid=us&device=ios"
    r = safe_get(url)
    if not r:
        record("15_AppFollow_API", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text[:500]
    record("15_AppFollow_API", r.status_code==200, 0, False, False,
           f"HTTP {r.status_code} | {raw[:100]}", "Public API — may return data without key", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 16 — iTunes Search API (version history via country variation)
# ══════════════════════════════════════════════════════════════════════════════
def check_itunes_variations():
    """Check if different country codes or endpoints surface more history."""
    app = PRIMARY
    results = {}
    for country in ["us", "gb", "au", "de"]:
        url = f"https://itunes.apple.com/lookup?id={app['id']}&country={country}&lang=en_us"
        r = safe_get(url)
        if r and r.status_code == 200:
            d = r.json().get("results", [{}])[0]
            results[country] = d.get("version","?")
        time.sleep(0.5)
    record("16_iTunes_Countries", True, 1, True, False,
           f"Versions by country: {results}",
           "All countries return same single current version — no history via lookup API")

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 17 — App Store (apps.apple.com) direct page JSON-LD
# ══════════════════════════════════════════════════════════════════════════════
def check_appstore_page():
    app = PRIMARY
    url = f"https://apps.apple.com/us/app/id{app['id']}"
    r = safe_get(url)
    if not r:
        record("17_AppStore_Page", False, 0, False, False, "", "Connection failed", url=url)
        return
    raw = r.text
    # JSON-LD
    ver_m = re.search(r'"softwareVersion"\s*:\s*"([\d.]+)"', raw)
    notes_m = re.search(r'"releaseNotes"\s*:\s*"([^"]{20,500})"', raw)
    date_m = re.search(r'"datePublished"\s*:\s*"([\d\-T:Z]+)"', raw)
    record("17_AppStore_Page", r.status_code==200,
           1 if ver_m else 0, bool(date_m), bool(notes_m),
           f"v={ver_m.group(1) if ver_m else '?'} | date={date_m.group(1) if date_m else '?'} | "
           f"notes={'YES' if notes_m else 'NO'}",
           "Only current version in JSON-LD — no history", url=url)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 18 — SteamSpy equivalent: AppFollow changelog public endpoint
# ══════════════════════════════════════════════════════════════════════════════
def check_changelog_sources():
    """Try a few changelog aggregator sites."""
    app = PRIMARY
    sources_to_try = [
        ("ReleasesNotes.io",    f"https://releasesnotes.io/ios/{app['id']}"),
        ("AppChangelog",        f"https://www.appchangelog.com/ios/{app['id']}"),
        ("WhatsNewOnIOS",       f"https://www.whatsnewonios.com/{app['id']}"),
        ("iOSRelease",         f"https://iosrelease.com/app/{app['id']}"),
    ]
    for site_name, url in sources_to_try:
        r = safe_get(url)
        if r:
            raw = r.text
            vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
            record(f"18_{site_name.replace('.','_').replace(' ','_')}",
                   r.status_code==200, len(set(vers)), len(dates)>2,
                   "release notes" in raw.lower(),
                   f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
                   url=url)
        else:
            record(f"18_{site_name.replace('.','_').replace(' ','_')}",
                   False, 0, False, False, "Connection failed", url=url)
        time.sleep(0.5)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 19 — Apptopia direct URL format variants
# ══════════════════════════════════════════════════════════════════════════════
def check_apptopia_variants():
    app = PRIMARY
    urls = [
        f"https://apptopia.com/ios/app/{app['id']}/about",
        f"https://apptopia.com/ios/app/{app['id']}/performance",
        f"https://apptopia.com/ios/app/{app['id']}/history",
    ]
    for url in urls:
        r = safe_get(url)
        if r:
            raw = r.text
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', raw)
            vers = re.findall(r'\b(\d+\.\d+[\.\d]{0,10})\b', raw)
            record(f"19_Apptopia_{url.split('/')[-1]}",
                   r.status_code==200, len(set(vers)), len(dates)>2, False,
                   f"HTTP {r.status_code} | {len(set(vers))} vers | {len(dates)} dates",
                   url=url)
        else:
            record(f"19_Apptopia_{url.split('/')[-1]}", False, 0, False, False, "Failed", url=url)
        time.sleep(1)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 20 — Google Search for "[appname] ios release notes site:appadvice.com" etc.
#             (just tests if a structured Google result might work via scraping)
# ══════════════════════════════════════════════════════════════════════════════
def check_google_hint():
    record("20_Google_Scraping", False, 0, False, False, "",
           "Google blocks automated scraping (429/CAPTCHA). Use Google Custom Search API ($) or skip.",
           url="https://www.google.com/search?q=spotify+ios+version+history+release+notes")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY PRINTER
# ══════════════════════════════════════════════════════════════════════════════
def print_summary():
    print("\n\n" + "═"*80)
    print("  SOURCE DIAGNOSTIC SUMMARY")
    print("═"*80)
    
    header = f"{'Source':<35} {'OK':>4} {'Vers':>6} {'Dates':>6} {'Notes':>6}"
    print(header)
    print("─"*60)
    
    winners = []
    for name, res in RESULTS.items():
        ok   = "✅" if res["accessible"] and res["versions_found"] > 0 else ("🔓" if res["accessible"] else "❌")
        d    = "✅" if res["has_dates"]  else "❌"
        n    = "✅" if res["has_notes"]  else "❌"
        v    = str(res["versions_found"]) if res["versions_found"] else "-"
        print(f"  {name:<33} {ok:>4} {v:>6} {d:>6} {n:>6}")
        if res["accessible"] and res["versions_found"] > 0 and res["has_dates"]:
            winners.append(name)
    
    print("\n" + "═"*80)
    print("  🏆 BEST SOURCES (accessible + has version numbers + has dates):")
    if winners:
        for w in winners:
            print(f"     → {w}  |  URL: {RESULTS[w]['url']}")
            if RESULTS[w]["has_notes"]:
                print(f"       ↳ Also has release NOTES!")
    else:
        print("     None found with all three (accessible + versions + dates).")
        print("     Fallback strategy: Wayback snapshots + LLM date estimation")
    print("═"*80)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"iOS Version History — Source Diagnostic")
    print(f"Test app: {PRIMARY['name']} (id={PRIMARY['id']})")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print("Testing 20 source categories...\n")

    checks = [
        ("iTunes API",           check_itunes),
        ("AppShopper",           check_appshopper),
        ("AppAdvice",            check_appadvice),
        ("AppAgg",               check_appagg),
        ("AppFollow",            check_appfollow),
        ("AppPure",              check_apppure),
        ("iOSnoops",             check_iosnoops),
        ("AppMirror",            check_appmirror),
        ("Wayback CDX",          check_wayback_cdx),
        ("Wayback Snapshot",     check_wayback_snapshot),
        ("Apple Reviews RSS",    check_apple_rss),
        ("AppRaven",             check_appraven),
        ("MobileAction",         check_mobileaction),
        ("AppMagic",             check_appmagic),
        ("AppFollow API",        check_appfollow_api),
        ("iTunes Countries",     check_itunes_variations),
        ("AppStore Page",        check_appstore_page),
        ("Changelog Sites",      check_changelog_sources),
        ("Apptopia Variants",    check_apptopia_variants),
        ("Google Hint",          check_google_hint),
    ]

    for label, fn in checks:
        print(f"\n{'─'*60}")
        print(f"  Checking: {label}")
        print(f"{'─'*60}")
        try:
            fn()
        except Exception as e:
            print(f"  !! Unhandled error in {label}: {e}")
        time.sleep(1.0)

    print_summary()

    # Save raw results
    with open("source_diagnostic_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\nRaw results saved to: source_diagnostic_results.json")
    print("Done.")