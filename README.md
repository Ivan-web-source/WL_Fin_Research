# App Version History Scraper

This repository is designed to scrape historical version information for 10 major applications across both **iOS** and **Android** platforms.

The project workflow is divided into two major phases:

1. **Testing and validating available public scraping sources**
2. **Running the actual scraping pipelines to generate structured datasets**

The final output of the project is a formatted Excel spreadsheet containing application version history data.

---

# Targeted Applications 

The repository scrapes version history for:

1. YouTube  
2. TikTok  
3. ChatGPT  
4. Claude  
5. WhatsApp  
6. CapCut  
7. Instagram  
8. LinkedIn  
9. Tinder  
10. Spotify  

---

# Repository Structure

```bash
.
├── test_scrap.py
├── test_source_android.py
├── test_source_iOS.py
├── scraping_android.py
└── scraping_iOS.py
```

---

# File Descriptions

## `test_scrap.py`

Basic iOS API validation script.

This script:
- tests the iTunes Lookup API
- verifies API access
- retrieves:
  - app names
  - developer information
  - categories
  - current versions
  - release dates
  - release notes

This is primarily used as a quick connectivity and metadata validation step.

---

## `test_source_android.py`

Android source diagnostic script.

This file tests multiple Android scraping sources including:

- Google Play Store
- APKMirror
- APKPure
- AppBrain
- Apptopia
- Wayback Machine
- AppFollow
- AppShopper

The script evaluates:
- source accessibility
- version history availability
- release date availability
- release notes availability

This script is used for diagnostics only and does not generate the final dataset.

---

## `test_source_iOS.py`

iOS source diagnostic script.

This file tests multiple iOS scraping sources including:

- iTunes API
- AppShopper
- AppAdvice
- AppAgg
- AppFollow
- AppPure
- iOSNoops
- Wayback Machine
- AppRaven
- AppMagic
- MobileAction

The script validates:
- historical version availability
- release notes availability
- release dates
- source quality

This script is only used for testing and diagnostics.

---

## `scraping_android.py`

Main Android scraping pipeline.

This script:
- scrapes Android app version history
- combines multiple public data sources
- extracts release notes
- extracts release dates
- validates version numbers
- formats the final dataset
- exports the results into Excel

### Generated Output

```bash
android_app_version_history_v3.xlsx
```

---

## `scraping_iOS.py`

Main iOS scraping pipeline.

This script:
- scrapes iOS app version history
- retrieves metadata from the iTunes API
- combines multiple historical sources
- extracts release notes
- extracts release dates
- structures and formats the dataset
- exports the results into Excel

### Generated Output

```bash
ios_app_version_history_v3.xlsx
```

---

# Requirements

- Python 3.9+
- Internet connection
- pip

---

# Dependency Installation

## Create Virtual Environment (Optional but Recommended)

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## Install Required Dependencies

Run the following command:

```bash
pip install pandas requests beautifulsoup4 lxml openpyxl tabulate
```

---

# Step-by-Step Usage

# Step 1 — Test Basic iOS API Connectivity

Run:

```bash
python test_scrap.py
```

This verifies:
- iTunes API access
- metadata retrieval
- JSON response structure

Expected result:
- JSON output printed in terminal

---

# Step 2 — Test Android Scraping Sources

Run:

```bash
python test_source_android.py
```

This script:
- checks Android scraping sources
- tests version history availability
- validates release notes and dates
- prints source diagnostics

Expected outputs:
- terminal diagnostic summary
- JSON diagnostic report

---

# Step 3 — Test iOS Scraping Sources

Run:

```bash
python test_source_iOS.py
```

This script:
- validates iOS scraping sources
- checks historical version availability
- evaluates release notes and release dates
- prints diagnostic summaries

Expected outputs:
- terminal diagnostic summary
- JSON diagnostic report

---

# Step 4 — Run Android Scraper

Run:

```bash
python scraping_android.py
```

The script will:
- scrape Android version history
- merge multiple sources
- clean and validate records
- generate a formatted Excel spreadsheet

Generated output:

```bash
android_app_version_history_v3.xlsx
```

---

# Step 5 — Run iOS Scraper

Run:

```bash
python scraping_iOS.py
```

The script will:
- scrape iOS version history
- merge metadata from multiple sources
- clean and structure records
- generate a formatted Excel spreadsheet

Generated output:

```bash
ios_app_version_history_v3.xlsx
```

---

# Excel Output

The final outputs are Excel spreadsheets containing structured application version history.

The spreadsheets include:

- App Name
- Platform
- Developer / Company
- App Category
- Version Number
- Version Release Date
- Current Version Indicator
- Initial App Release Date
- Update Description / Release Notes
- Update History Source
- Data Quality Notes

The spreadsheets are automatically formatted using `openpyxl`.

---

# Example Full Workflow

```bash
# Clone repository
git clone <repository-url>

# Enter repository
cd <repository-folder>

# Create virtual environment
python -m venv venv

# Activate virtual environment
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Install dependencies
pip install pandas requests beautifulsoup4 lxml openpyxl tabulate

# Test API access
python test_scrap.py

# Test Android sources
python test_source_android.py

# Test iOS sources
python test_source_iOS.py

# Generate Android Excel output
python scraping_android.py

# Generate iOS Excel output
python scraping_iOS.py
```

---

# Notes

- Some public sources may rate-limit requests
- Certain websites may change their HTML structure over time
- Historical version coverage varies by source
- Release notes availability depends on source quality
- Some sources may become temporarily unavailable

---

# Final Output

After running the scraping scripts, the repository generates:

```bash
android_app_version_history_v3.xlsx
ios_app_version_history_v3.xlsx
```

These Excel files contain the structured historical version datasets for all supported applications.

---
