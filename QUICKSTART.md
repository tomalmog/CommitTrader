# CommitTrader - Quick Start Guide

Get started with CommitTrader in 5 minutes!

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Set GitHub token for higher API limits
export GITHUB_TOKEN="your_token_here"
```

Get a GitHub token at: https://github.com/settings/tokens (no special permissions needed)

## Run Your First Analysis

### Option 1: Test Run (Fast)

Analyze a small sample to verify everything works:

```bash
python main.py --mode full --tickers MSFT --max-events 10
```

This will:
- Collect events from Microsoft's repositories
- Analyze 10 events
- Generate results in `data/processed/snapshots/`

### Option 2: Full Analysis

Run a complete analysis on multiple companies:

```bash
python main.py --mode full --tickers MSFT GOOGL META --start-date 2023-01-01
```

### Option 3: All Mapped Companies

Analyze all companies in the mappings file:

```bash
python main.py --mode full
```

**Note**: This will take several hours depending on the number of companies and GitHub API rate limits.

## Understanding the Output

After running the analysis, you'll find:

### Results Directory: `data/processed/snapshots/`

Each analysis creates a snapshot with:
- `event_study_results.csv` - Individual event results
- `aggregated_results.csv` - Statistics by event type
- `statistical_tests.json` - Significance test results
- `summary.json` - High-level summary

### Key Metrics to Look For

**In the terminal output:**
```
Mean AR (Day 0): X.XXXX%      # Average abnormal return on event day
Mean CAR (-5,5): X.XXXX%      # Average cumulative return over 11-day window
% Positive AR: XX.XX%         # Percentage of events with positive returns
```

**Statistical Significance:**
- `***` = highly significant (p < 0.01)
- `**` = significant (p < 0.05)
- `*` = marginally significant (p < 0.10)
- `ns` = not significant

## Interpreting Results

### Positive Results Indicate:
- GitHub events correlate with stock price movements
- Markets react to repository activity
- Specific event types may carry informational value

### Negative/Null Results Indicate:
- No measurable relationship detected
- Markets don't react to these GitHub signals
- Effects may be too small or too noisy to detect

## Common Use Cases

### 1. Compare Event Types

Which has more impact - releases or commit spikes?

```bash
python main.py --mode full --max-events 100
# Check aggregated_results.csv to compare event types
```

### 2. Analyze Specific Time Period

Study a particular market period:

```bash
python main.py --mode full --start-date 2020-03-01 --end-date 2020-06-01
```

### 3. Focus on Tech Companies

Edit `data/mappings/company_repo_mappings.csv` and run:

```bash
python main.py --mode full --tickers MSFT GOOGL META AAPL AMZN
```

## Customization

### Adjust Event Windows

Edit `config.yaml`:

```yaml
event_study:
  event_window:
    pre: 10   # Look 10 days before event
    post: 10  # Look 10 days after event
```

### Change Expected Return Model

```yaml
event_study:
  expected_return_model: "market"  # or "mean_adjusted" or "market_adjusted"
```

### Filter Event Types

```yaml
events:
  releases:
    enabled: true
  commits:
    enabled: false  # Disable commit spike analysis
```

## Working with Jupyter Notebook

```bash
jupyter notebook notebooks/example_analysis.ipynb
```

The notebook provides interactive analysis and custom visualizations.

## Troubleshooting

### "No events collected"
- Check that repositories exist and are public
- Verify date range includes repository activity
- Ensure companies are in mappings file

### "Rate limit exceeded"
- Set GITHUB_TOKEN environment variable
- Reduce number of companies/events
- Wait for rate limit reset

### "No stock data available"
- Verify ticker symbols are correct
- Check date range covers trading days
- Some tickers may not be in yfinance

### "Insufficient data for event study"
- Event occurred too close to start/end of data
- Not enough trading days around event
- Stock was not actively traded during period

## Next Steps

1. **Expand company list**: Add more mappings in `data/mappings/company_repo_mappings.csv`

2. **Try different configurations**: Experiment with `config.yaml` settings

3. **Visualize results**: Use the notebook to create custom plots

4. **Export findings**: Results are saved in CSV/JSON for external analysis

5. **Interpret results**: Consider the research questions in README.md

## Getting Help

- Read the full README.md for detailed documentation
- Check the example notebook for code samples
- Review config.yaml for all configuration options
- Examine the output files to understand data structure

## Example Workflow

```bash
# 1. Quick test
python main.py --mode full --tickers MSFT --max-events 5

# 2. Review results
cat data/processed/snapshots/full_analysis_*/summary.json

# 3. If looks good, run full analysis
python main.py --mode full --tickers MSFT GOOGL META

# 4. Generate additional visualizations
python main.py --mode visualize

# 5. Explore in notebook
jupyter notebook notebooks/example_analysis.ipynb
```

Happy researching!
