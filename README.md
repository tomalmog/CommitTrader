# CommitTrader

A quantitative research platform analyzing the relationship between GitHub activity from open-source repositories and stock prices of publicly traded companies.

## Overview

CommitTrader investigates whether public GitHub activity (commits, releases, repository metrics) from open-source projects associated with publicly traded companies has any measurable impact on their stock prices. The platform uses event-study methodology to measure abnormal returns around different types of GitHub events and evaluates which signals—if any—carry informational value for investors.

## Features

- **Comprehensive Data Collection**
  - Automated GitHub event collection (releases, commits, activity spikes)
  - Stock price data integration via yfinance
  - Configurable company-to-repository mappings
  - Built-in caching to minimize API calls

- **Rigorous Event Study Analysis**
  - Market model, mean-adjusted, and market-adjusted return models
  - Calculation of abnormal returns (AR) and cumulative abnormal returns (CAR)
  - Multiple event windows (-5 to +5 days, custom configurations)
  - Estimation period methodology (130-day windows)

- **Statistical Testing**
  - Parametric tests (t-tests, ANOVA)
  - Non-parametric tests (sign test, Wilcoxon signed-rank)
  - Cross-sectional analysis
  - Significance testing for different CAR windows

- **Visualization & Reporting**
  - Distribution plots for AR and CAR
  - Event type comparisons
  - Timeline analysis
  - Comprehensive summary dashboards
  - Statistical significance visualization

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd commitTrader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional but recommended) Set up GitHub token for higher API rate limits:
```bash
export GITHUB_TOKEN="your_github_token_here"
```

Get a token at: https://github.com/settings/tokens

Without a token: 60 API requests/hour
With a token: 5,000 API requests/hour

## Quick Start

### Basic Usage

Run a complete analysis on default companies:

```bash
python main.py --mode full
```

### Analyze Specific Companies

```bash
python main.py --mode full --tickers MSFT GOOGL META --start-date 2022-01-01
```

### Step-by-Step Workflow

1. **Data Collection Only**:
```bash
python main.py --mode collect --tickers MSFT GOOGL
```

2. **Analysis on Collected Data**:
```bash
python main.py --mode analyze --skip-collection
```

3. **Generate Visualizations**:
```bash
python main.py --mode visualize
```

## Configuration

Edit `config.yaml` to customize:

- Event windows (pre/post event days)
- Estimation windows for expected returns
- Event types to analyze (releases, commits, milestones)
- Statistical significance levels
- Cache settings
- Visualization preferences

### Key Configuration Options

```yaml
event_study:
  event_window:
    pre: 5    # Days before event
    post: 5   # Days after event

  estimation_window:
    start: -130  # Start of estimation period
    end: -31     # End of estimation period

  expected_return_model: "market"  # market, mean_adjusted, or market_adjusted

events:
  releases:
    enabled: true
    prerelease: false
  commits:
    enabled: true
    spike_threshold: 2.0  # Std deviations for spike detection
```

## Company-Repository Mappings

The system uses a CSV file to map stock tickers to GitHub repositories:

`data/mappings/company_repo_mappings.csv`

Format:
```csv
ticker,company_name,repo_full_name,repo_type,sector,primary_repo
MSFT,Microsoft,microsoft/vscode,primary,Technology,TRUE
GOOGL,Alphabet,tensorflow/tensorflow,project,Technology,TRUE
```

Add your own mappings to analyze additional companies.

## Output Structure

```
data/
├── raw/                    # Cached GitHub and stock data
│   ├── github/
│   └── stocks/
├── processed/              # Analysis results
│   ├── event_studies/     # Individual event study results
│   ├── aggregated/        # Aggregated statistics
│   ├── statistics/        # Statistical test results
│   ├── figures/           # Visualizations
│   └── snapshots/         # Complete analysis snapshots
```

## Usage Examples

### Example 1: Analyze Tech Giants

```python
from src.analysis.pipeline import AnalysisPipeline
from datetime import datetime

# Initialize pipeline
pipeline = AnalysisPipeline(github_token="your_token")

# Run analysis
summary = pipeline.run_full_analysis(
    tickers=['MSFT', 'GOOGL', 'META', 'AAPL'],
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2023, 12, 31)
)
```

### Example 2: Analyze Specific Event Type

```python
from src.data.github_collector import GitHubCollector
from src.analysis.event_study import EventStudy

# Collect release events only
collector = GitHubCollector()
releases = collector.collect_releases('microsoft/vscode')

# Analyze each release
event_study = EventStudy()
for _, release in releases.iterrows():
    result = event_study.analyze_event(
        ticker='MSFT',
        event_date=release['published_at'],
        event_type='release'
    )
```

### Example 3: Custom Visualization

```python
from src.visualization.plots import ResultsVisualizer
from src.data.storage import DataStorage

# Load results
storage = DataStorage()
results = storage.load_event_study_results('full_analysis')

# Create custom plots
visualizer = ResultsVisualizer()
fig = visualizer.plot_car_distribution(results, car_column='CAR_0_5')
storage.save_figure(fig, 'custom_car_plot', 'analysis_name')
```

## Methodology

### Event Study Approach

1. **Event Identification**: Collect GitHub events (releases, commit spikes, milestones)

2. **Expected Returns**: Calculate expected returns using:
   - Market Model: E(R_it) = α_i + β_i * R_mt
   - Mean-Adjusted Model: E(R_it) = mean(R_it) over estimation period
   - Market-Adjusted Model: E(R_it) = R_mt

3. **Abnormal Returns**: AR_it = R_it - E(R_it)

4. **Cumulative Abnormal Returns**: CAR = Σ AR_it over event window

5. **Statistical Testing**: Multiple tests to assess significance

### Statistical Tests

- **t-test**: Tests if mean abnormal return differs from zero
- **Sign test**: Non-parametric test for median AR
- **Wilcoxon signed-rank**: Robust test for AR significance
- **Cross-sectional test**: Tests across multiple events
- **ANOVA**: Compares AR across different event types

## Research Questions

This platform helps answer:

1. Do GitHub releases generate measurable stock price reactions?
2. Are commit activity spikes associated with abnormal returns?
3. Which types of GitHub events carry informational value?
4. Does the relationship vary by company size, sector, or repository characteristics?
5. How quickly do markets react to GitHub activity?

## Limitations & Considerations

- **Correlation ≠ Causation**: Observed relationships don't imply trading signals
- **Confounding Events**: Other news/events may occur simultaneously
- **Selection Bias**: Analysis limited to companies with public GitHub presence
- **Data Quality**: Depends on GitHub API and stock data reliability
- **Market Efficiency**: Markets may quickly price in public information

## Contributing

To add new features or companies:

1. Add company mappings to `data/mappings/company_repo_mappings.csv`
2. Extend event types in `src/data/github_collector.py`
3. Add custom statistical tests in `src/analysis/statistics.py`
4. Create new visualizations in `src/visualization/plots.py`

## Project Structure

```
commitTrader/
├── src/
│   ├── analysis/
│   │   ├── event_study.py      # Event study methodology
│   │   ├── statistics.py       # Statistical testing
│   │   └── pipeline.py         # Main analysis pipeline
│   ├── data/
│   │   ├── github_collector.py # GitHub data collection
│   │   ├── stock_collector.py  # Stock price data
│   │   ├── company_mapper.py   # Ticker-repo mapping
│   │   └── storage.py          # Data persistence
│   ├── visualization/
│   │   └── plots.py            # Visualization tools
│   └── config.py               # Configuration management
├── data/                       # Data storage
├── config.yaml                 # Configuration file
├── main.py                     # CLI entry point
└── requirements.txt            # Dependencies
```

## License

MIT License - See LICENSE file for details

## Citation

If you use CommitTrader in academic research, please cite:

```
@software{committrader,
  title={CommitTrader: Analyzing GitHub Activity and Stock Price Relationships},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/commitTrader}
}
```

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check documentation in `/docs` (if available)
- Review example notebooks in `/notebooks`

---

**Disclaimer**: This tool is for research purposes only. It should not be used as the basis for investment decisions. Past performance does not guarantee future results.
