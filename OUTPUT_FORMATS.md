```# CommitTrader Output Formats

## Overview

After running CommitTrader analysis, your results are available in **multiple formats** optimized for different purposes.

---

## 📊 Output Formats Explained

### 1. **Interactive Website** (Primary Format)
**📁 Location:** `docs/` folder

**What you get:**
- `index.html` - Professional landing page with key findings
- `report.html` - Full interactive report with Plotly charts
- `methodology.html` - Detailed methodology explanation
- `downloads.html` - Data download page
- `data/` - All raw data in CSV/JSON

**Features:**
- ✨ Interactive charts (zoom, pan, hover for details)
- 📱 Mobile responsive
- 🎨 Professional design
- 🔗 Shareable via GitHub Pages

**Best for:**
- Publishing online
- Portfolio/resume
- Sharing with recruiters
- Academic presentations
- Social media

**How to view:**
```bash
# Open in browser
open docs/index.html

# Or serve locally
python -m http.server 8000 --directory docs
# Visit: http://localhost:8000
```

**How to publish:**
```bash
# Push to GitHub
git add docs/
git commit -m "Add analysis results"
git push

# Enable GitHub Pages in repo settings
# Your site: https://username.github.io/commitTrader/
```

---

### 2. **Standalone HTML Report**
**📁 Location:** `data/processed/reports/report_YYYYMMDD_HHMMSS.html`

**What you get:**
- Single HTML file
- Includes all charts and styles
- Self-contained (no external dependencies)

**Features:**
- 📧 Email-friendly (single file)
- 💾 Works offline
- 🎯 Complete analysis in one place

**Best for:**
- Email attachments
- Google Drive/Dropbox sharing
- Backup/archive
- Quick sharing

**How to use:**
```bash
# Just open the file
open data/processed/reports/report_*.html

# Or email it, upload to cloud, etc.
```

---

### 3. **CSV Data Files**
**📁 Location:** `data/processed/snapshots/full_analysis_TIMESTAMP/`

**Files:**
- `event_study_results.csv` - Individual event analysis
  - Columns: ticker, event_date, event_type, ar_day_0, CAR_-5_5, etc.
  - One row per event analyzed

- `aggregated_results.csv` - Summary by event type
  - Columns: event_type, mean_ar, median_ar, std, count, etc.
  - One row per event type

**Best for:**
- Loading into Excel/Google Sheets
- Further analysis in R/Python
- Academic collaboration
- Verification/replication

**How to use:**
```python
import pandas as pd

# Load results
results = pd.read_csv('data/processed/snapshots/.../event_study_results.csv')

# Analyze further
print(results.describe())
results[results['CAR_-5_5'] > 0.05]  # Events with >5% CAR
```

---

### 4. **JSON Metadata**
**📁 Location:** `data/processed/snapshots/full_analysis_TIMESTAMP/`

**Files:**
- `summary.json` - High-level findings
- `statistical_tests.json` - Test results
- `metadata.json` - Analysis parameters

**Structure:**
```json
{
  "analysis_date": "2024-11-15T...",
  "total_events": 1234,
  "valid_event_studies": 1150,
  "overall_statistics": {
    "mean_ar_day_0": 0.0042,
    "mean_car_5_5": 0.0089,
    "pct_positive_ar": 58.3
  },
  "statistical_significance": {
    "t_test": {
      "p_value": 0.0234,
      "significant": true
    }
  }
}
```

**Best for:**
- Programmatic access
- API integrations
- Quick lookups
- README badges

---

### 5. **Raw Data Cache**
**📁 Location:** `data/raw/`

**Contents:**
- `github/` - Cached GitHub data (releases, commits)
- `stocks/` - Cached stock price data
- Format: JSON and CSV

**Purpose:**
- Speed up re-runs
- Avoid hitting API limits
- Reproducibility

**Note:** Can be deleted to force fresh data collection

---

## 🎯 Quick Decision Guide

**I want to...**

### Share on social media
→ Use **Website** (`docs/`)
- Publish to GitHub Pages
- Share the link: `https://username.github.io/commitTrader/`

### Send to a professor/colleague
→ Use **Standalone HTML Report**
- Email: `data/processed/reports/report_*.html`

### Include in a paper
→ Use **CSV Data + Website**
- Reference website for interactive exploration
- Include CSVs as supplementary material

### Add to portfolio
→ Use **Website**
- Add GitHub Pages link to resume
- Screenshot key charts

### Do more analysis
→ Use **CSV Files**
- Load into your preferred tool
- Raw event-level data available

### Quick overview
→ Use **Terminal Output**
- The summary printed after analysis
- Or `summary.json` for structured data

---

## 📸 What They Look Like

### Website (index.html)
```
┌─────────────────────────────────────────┐
│  📊 CommitTrader Research               │
│  Analyzing GitHub Activity & Stocks     │
│                                         │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │
│  │ 1.2k│ │  50 │ │0.42%│ │0.89%│      │
│  │Event│ │ Co. │ │Mean │ │ CAR │      │
│  └─────┘ └─────┘ └─────┘ └─────┘      │
│                                         │
│  [View Full Report] [Methodology]       │
└─────────────────────────────────────────┘
```

### Full Report (report.html)
```
┌─────────────────────────────────────────┐
│  Executive Summary                      │
│  ┌─────────────────────────────────┐   │
│  │ 📊 Interactive CAR Chart        │   │
│  │     [Hover shows details]       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Statistical Tests                      │
│  ┌─────────────────────────────────┐   │
│  │ Test     | P-Value | Sig.       │   │
│  │ t-test   | 0.0234  | **         │   │
│  │ sign     | 0.0156  | **         │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### CSV Files
```
ticker,event_date,event_type,ar_day_0,CAR_-5_5
MSFT,2023-01-15,release,0.0123,0.0234
GOOGL,2023-01-20,release,-0.0056,0.0012
...
```

---

## 🔄 Regenerate Reports

If you want to recreate reports from existing data:

```bash
# Re-run with cached data
python main.py --mode full --skip-collection

# Or specify a specific events file
python main.py --mode analyze --events-file data/raw/events/all_events_*.csv

# Skip report generation (data only)
python main.py --mode full --no-reports
```

---

## 💾 File Sizes

Typical output sizes (for 1000 events):

- Website (`docs/`): ~500 KB
- HTML Report: ~400 KB
- Event Study Results CSV: ~200 KB
- Aggregated Results CSV: ~5 KB
- JSON files: ~50 KB total
- Charts: Embedded in HTML (vector graphics)

**Total:** ~1-2 MB for complete analysis

---

## 🎨 Customization

### Change website style
Edit in `config.yaml`:
```yaml
visualization:
  style: "seaborn-v0_8-darkgrid"  # or plotly_white, etc.
  figure_size: [12, 8]
```

### Custom title/branding
Pass to analysis:
```python
from src.reporting.website_generator import WebsiteGenerator

gen = WebsiteGenerator()
gen.generate_website(
    ...,
    project_title="My Research Project",
    author="Your Name",
    description="Custom description"
)
```

---

## 📤 Export Options

### For Presentations
1. Open `docs/report.html`
2. Right-click charts → "Save image as PNG"
3. Insert into PowerPoint/Keynote

### For Papers
1. Use CSV data in your analysis
2. Reference GitHub Pages site in paper
3. Include in supplementary materials

### For Social Media
1. Screenshot key findings from website
2. Share GitHub Pages link
3. Tweet thread with highlights

---

## ✅ Checklist: Ready to Share?

Before sharing your results:

- [ ] Open `docs/index.html` - does it load properly?
- [ ] Check key statistics - do they make sense?
- [ ] Review methodology page - accurate?
- [ ] Test data downloads - files accessible?
- [ ] Proofread text on website
- [ ] Add your name/affiliation
- [ ] Test on mobile device
- [ ] Push to GitHub
- [ ] Enable GitHub Pages
- [ ] Test live site link

---

## 🎓 Academic Standards

For academic use:

**Include in paper:**
- Reference to methodology
- Key statistics table
- Link to GitHub Pages for full results

**Supplementary materials:**
- `event_study_results.csv`
- `aggregated_results.csv`
- `statistical_tests.json`
- Link to code repository

**Data repository:**
- Upload to Zenodo or figshare
- Get DOI for citation
- Link from paper

---

## Questions?

- Website not generating? Check that plotly is installed: `pip install plotly`
- Charts not showing? Make sure JavaScript is enabled in browser
- GitHub Pages not working? Check repo settings → Pages
- Need help? Check [SHARING_GUIDE.md](./SHARING_GUIDE.md)

---

**Summary:** CommitTrader gives you publication-ready results in multiple formats. The interactive website is perfect for online sharing, while CSV/JSON files enable further analysis. Choose the format that best fits your audience! 🚀
