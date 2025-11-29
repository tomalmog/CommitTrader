"""Generate static website for GitHub Pages or web hosting."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import shutil
import json

import pandas as pd

from ..config import get_config
from .html_generator import HTMLReportGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebsiteGenerator:
    """Generates static website for research results."""

    def __init__(self):
        """Initialize website generator."""
        self.config = get_config()
        self.html_gen = HTMLReportGenerator()

    def generate_website(
        self,
        events: pd.DataFrame,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        statistical_tests: Dict,
        summary: Dict,
        output_dir: Optional[Path] = None,
        project_title: str = "CommitTrader Research",
        author: str = "Research Team",
        description: str = "Analyzing GitHub activity and stock price relationships"
    ) -> Path:
        """
        Generate complete static website.

        Args:
            events: Events data
            results: Event study results
            aggregated: Aggregated results
            statistical_tests: Statistical tests
            summary: Summary dictionary
            output_dir: Output directory
            project_title: Website title
            author: Author name
            description: Project description

        Returns:
            Path to website directory
        """
        if output_dir is None:
            output_dir = self.config.project_root / "docs"

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating website in {output_dir}")

        # Generate main report page
        report_path = self.html_gen.generate_html_report(
            events, results, aggregated, statistical_tests, summary,
            output_path=output_dir / "report.html",
            title=f"{project_title} - Full Report"
        )

        # Generate index page
        self._generate_index_page(
            output_dir, summary, project_title, author, description
        )

        # Generate data downloads page
        self._generate_downloads_page(
            output_dir, results, aggregated, summary
        )

        # Generate methodology page
        self._generate_methodology_page(output_dir, project_title)

        # Copy data files
        data_dir = output_dir / "data"
        data_dir.mkdir(exist_ok=True)

        # Export results as CSV
        results.to_csv(data_dir / "event_study_results.csv", index=False)
        aggregated.to_csv(data_dir / "aggregated_results.csv", index=False)

        with open(data_dir / "summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        # Generate README for GitHub Pages
        self._generate_github_readme(output_dir, project_title, description)

        logger.info(f"Website generated successfully at {output_dir}")
        logger.info(f"To publish on GitHub Pages:")
        logger.info(f"  1. Push the 'docs' folder to GitHub")
        logger.info(f"  2. Enable GitHub Pages in repo settings (source: docs folder)")
        logger.info(f"  3. Your site will be at: https://<username>.github.io/<repo>/")

        return output_dir

    def _generate_index_page(
        self,
        output_dir: Path,
        summary: Dict,
        title: str,
        author: str,
        description: str
    ):
        """Generate website index page."""
        stats = summary.get('overall_statistics', {})

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
        }}

        .hero {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 80px 20px;
            text-align: center;
        }}

        .hero h1 {{
            font-size: 3em;
            margin-bottom: 20px;
        }}

        .hero p {{
            font-size: 1.3em;
            opacity: 0.95;
            max-width: 800px;
            margin: 0 auto;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 60px 40px;
        }}

        .nav {{
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .nav-content {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px 40px;
            display: flex;
            gap: 35px;
            font-size: 0.95em;
            justify-content: center;
        }}

        .nav a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.3s;
        }}

        .nav a:hover {{
            color: #764ba2;
        }}

        .results-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin: 40px 0;
        }}

        .result-card {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s;
        }}

        .result-card:hover {{
            transform: translateY(-5px);
        }}

        .result-card .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .result-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}

        .section {{
            margin: 60px 0;
        }}

        .section h2 {{
            font-size: 2em;
            margin-bottom: 20px;
            color: #667eea;
        }}

        .findings {{
            background: #f0f4ff;
            padding: 30px;
            border-radius: 12px;
            border-left: 5px solid #667eea;
        }}

        .findings h3 {{
            color: #667eea;
            margin-bottom: 15px;
        }}

        .findings ul {{
            list-style: none;
            padding-left: 0;
        }}

        .findings li {{
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
        }}

        .findings li:before {{
            content: "📊";
            position: absolute;
            left: 0;
        }}

        .cta-buttons {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 40px 0;
            flex-wrap: wrap;
        }}

        .btn {{
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s;
            display: inline-block;
        }}

        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .btn-primary:hover {{
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}

        .btn-secondary {{
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }}

        .btn-secondary:hover {{
            background: #667eea;
            color: white;
        }}

        .footer {{
            background: #2d3748;
            color: white;
            padding: 40px 20px;
            text-align: center;
            margin-top: 80px;
        }}

        .footer p {{
            opacity: 0.8;
        }}

        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 2em; }}
            .hero p {{ font-size: 1.1em; }}
            .nav-content {{ flex-direction: column; gap: 10px; }}
        }}
    </style>
</head>
<body>
    <nav class="nav">
        <div class="nav-content">
            <a href="index.html">Home</a>
            <a href="report.html">Full Report</a>
            <a href="methodology.html">Methodology</a>
            <a href="downloads.html">Downloads</a>
        </div>
    </nav>

    <div class="hero">
        <h1>{title}</h1>
        <p>{description}</p>
        <p style="margin-top: 20px; font-size: 0.9em;">By {author}</p>
    </div>

    <div class="container">
        <div class="section">
            <h2>Key Results</h2>
            <div class="results-grid">
                <div class="result-card">
                    <div class="label">Events Analyzed</div>
                    <div class="value">{summary.get('total_events', 0):,}</div>
                </div>
                <div class="result-card">
                    <div class="label">Companies</div>
                    <div class="value">{summary.get('total_companies', 0)}</div>
                </div>
                <div class="result-card">
                    <div class="label">Mean AR (Day 0)</div>
                    <div class="value">{stats.get('mean_ar_day_0', 0)*100:.3f}%</div>
                </div>
                <div class="result-card">
                    <div class="label">Mean CAR (-5,+5)</div>
                    <div class="value">{stats.get('mean_car_5_5', 0)*100:.3f}%</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Key Findings</h2>
            <div class="findings">
                <h3>Research Question</h3>
                <p>Does public GitHub activity from open-source repositories associated with publicly traded companies have measurable impact on stock prices?</p>

                <h3 style="margin-top: 25px;">Main Results</h3>
                <ul>
                    <li><strong>Average abnormal return on event day:</strong> {stats.get('mean_ar_day_0', 0)*100:.4f}%</li>
                    <li><strong>Average cumulative abnormal return (-5 to +5 days):</strong> {stats.get('mean_car_5_5', 0)*100:.4f}%</li>
                    <li><strong>Percentage of events with positive returns:</strong> {stats.get('pct_positive_ar', 0):.1f}%</li>
                    <li><strong>Total events with valid data:</strong> {summary.get('valid_event_studies', 0):,} out of {summary.get('total_events', 0):,}</li>
                </ul>

                <h3 style="margin-top: 25px;">Interpretation</h3>
                <p>
                    {'The results suggest a statistically significant relationship between GitHub activity and stock prices.'
                     if abs(stats.get('mean_ar_day_0', 0)) > 0.001
                     else 'The results show limited evidence of a relationship between GitHub activity and stock prices.'}
                    See the full report for detailed statistical analysis and event type breakdowns.
                </p>
            </div>
        </div>

        <div class="cta-buttons">
            <a href="report.html" class="btn btn-primary">View Full Report</a>
            <a href="methodology.html" class="btn btn-secondary">Methodology</a>
            <a href="downloads.html" class="btn btn-secondary">Download Data</a>
        </div>

        <div class="section">
            <h2>About This Research</h2>
            <p style="font-size: 1.1em; line-height: 1.8;">
                This study uses event-study methodology to analyze the relationship between GitHub activity
                (releases, commits, and other repository events) and stock price movements for publicly traded
                technology companies. The analysis examines {summary.get('total_events', 0):,} events across
                {summary.get('total_companies', 0)} companies using rigorous statistical testing.
            </p>
        </div>
    </div>

    <div class="footer">
        <p><strong>CommitTrader Research Platform</strong></p>
        <p>Generated: {datetime.now().strftime('%B %d, %Y')}</p>
        <p style="margin-top: 15px; font-size: 0.9em;">
            This research is for educational purposes only and should not be used as investment advice.
        </p>
    </div>
</body>
</html>
"""

        with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
            f.write(html)

    def _generate_methodology_page(self, output_dir: Path, title: str):
        """Generate methodology page."""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Methodology - {title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.8;
            color: #333;
            margin: 0;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin: 0;
        }}

        .container {{
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
        }}

        h2 {{
            color: #667eea;
            margin-top: 40px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}

        .method-box {{
            background: #f0f4ff;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}

        code {{
            background: #e5e7eb;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}

        ol, ul {{
            margin: 15px 0;
            padding-left: 30px;
        }}

        li {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Research Methodology</h1>
    </div>

    <div class="container">
        <h2>Event Study Framework</h2>
        <p>
            This research employs standard event study methodology from financial econometrics to
            measure the impact of GitHub events on stock returns.
        </p>

        <div class="method-box">
            <h3>1. Event Identification</h3>
            <p>Three types of GitHub events are analyzed:</p>
            <ul>
                <li><strong>Releases:</strong> Tagged version releases (excluding pre-releases)</li>
                <li><strong>Commit Spikes:</strong> Unusual increases in commit activity (2+ standard deviations)</li>
                <li><strong>Milestones:</strong> Major version releases, first commits, repository creation</li>
            </ul>
        </div>

        <div class="method-box">
            <h3>2. Expected Returns Calculation</h3>
            <p>We use the <strong>market model</strong> to estimate expected returns:</p>
            <p><code>R_it = α_i + β_i × R_mt + ε_it</code></p>
            <p>Where:</p>
            <ul>
                <li><code>R_it</code> = Stock return for company i at time t</li>
                <li><code>R_mt</code> = Market return (S&P 500)</li>
                <li><code>α_i, β_i</code> = OLS regression parameters</li>
            </ul>
            <p>Parameters are estimated using 100 trading days (-130 to -31 days before event).</p>
        </div>

        <div class="method-box">
            <h3>3. Abnormal Returns</h3>
            <p><code>AR_it = R_it - E(R_it)</code></p>
            <p>Where <code>E(R_it)</code> is the expected return from the market model.</p>
        </div>

        <div class="method-box">
            <h3>4. Cumulative Abnormal Returns</h3>
            <p><code>CAR_i(t1, t2) = Σ AR_it</code> for t = t1 to t2</p>
            <p>We calculate CAR for multiple windows:</p>
            <ul>
                <li>Day 0: Event day only</li>
                <li>Days 0 to +1: Event day plus next day</li>
                <li>Days -1 to +1: Three-day window</li>
                <li>Days -5 to +5: Full event window</li>
            </ul>
        </div>

        <h2>Statistical Testing</h2>

        <div class="method-box">
            <h3>Parametric Tests</h3>
            <ul>
                <li><strong>t-test:</strong> Tests if mean abnormal return differs from zero</li>
                <li><strong>ANOVA:</strong> Compares abnormal returns across event types</li>
            </ul>
        </div>

        <div class="method-box">
            <h3>Non-Parametric Tests</h3>
            <ul>
                <li><strong>Sign Test:</strong> Tests if median AR equals zero (no distributional assumptions)</li>
                <li><strong>Wilcoxon Signed-Rank:</strong> Robust alternative to t-test</li>
            </ul>
        </div>

        <h2>Data Sources</h2>
        <ul>
            <li><strong>GitHub Data:</strong> GitHub REST API v3</li>
            <li><strong>Stock Prices:</strong> Yahoo Finance (via yfinance library)</li>
            <li><strong>Market Index:</strong> S&P 500 (^GSPC)</li>
        </ul>

        <h2>Limitations</h2>
        <ul>
            <li><strong>Confounding Events:</strong> Other news may occur simultaneously with GitHub events</li>
            <li><strong>Selection Bias:</strong> Analysis limited to companies with public GitHub presence</li>
            <li><strong>Data Quality:</strong> Depends on accuracy of GitHub API and stock data</li>
            <li><strong>Market Efficiency:</strong> Markets may quickly incorporate public information</li>
        </ul>

        <h2>Software</h2>
        <p>
            Analysis conducted using <strong>CommitTrader</strong>, an open-source quantitative research platform.
            Key libraries: pandas, numpy, scipy, statsmodels, yfinance, PyGithub.
        </p>
    </div>
</body>
</html>
"""

        with open(output_dir / "methodology.html", 'w', encoding='utf-8') as f:
            f.write(html)

    def _generate_downloads_page(
        self,
        output_dir: Path,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        summary: Dict
    ):
        """Generate data downloads page."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Downloads - CommitTrader Research</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }

        .container {
            max-width: 1000px;
            margin: 40px auto;
            padding: 0 20px;
        }

        .download-card {
            background: white;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            padding: 25px;
            margin: 20px 0;
            transition: all 0.3s;
        }

        .download-card:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
        }

        .download-card h3 {
            color: #667eea;
            margin-top: 0;
        }

        .btn-download {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s;
        }

        .btn-download:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Download Research Data</h1>
        <p>All data and results available for download</p>
    </div>

    <div class="container">
        <div class="download-card">
            <h3>📊 Event Study Results</h3>
            <p>
                Complete event study results including abnormal returns and cumulative abnormal
                returns for all events. Includes metadata about each event.
            </p>
            <p><strong>Format:</strong> CSV | <strong>Rows:</strong> """ + f"""{len(results):,}""" + """</p>
            <a href="data/event_study_results.csv" class="btn-download">Download CSV</a>
        </div>

        <div class="download-card">
            <h3>📈 Aggregated Results</h3>
            <p>
                Aggregated statistics by event type, including mean, median, and standard deviation
                of abnormal returns.
            </p>
            <p><strong>Format:</strong> CSV | <strong>Rows:</strong> """ + f"""{len(aggregated)}""" + """</p>
            <a href="data/aggregated_results.csv" class="btn-download">Download CSV</a>
        </div>

        <div class="download-card">
            <h3>📋 Summary Statistics</h3>
            <p>
                High-level summary of the analysis including total events, companies analyzed,
                and overall statistics.
            </p>
            <p><strong>Format:</strong> JSON</p>
            <a href="data/summary.json" class="btn-download">Download JSON</a>
        </div>

        <div class="download-card">
            <h3>📄 Full Report (HTML)</h3>
            <p>
                Complete interactive report with all visualizations and statistical tests.
                Can be viewed offline.
            </p>
            <a href="report.html" class="btn-download">View Report</a>
        </div>

        <div style="margin-top: 50px; padding: 20px; background: #f0f4ff; border-radius: 8px;">
            <h3 style="margin-top: 0;">Citation</h3>
            <p>If you use this data in your research, please cite:</p>
            <pre style="background: white; padding: 15px; border-radius: 5px; overflow-x: auto;">
@misc{committrader,
  title={CommitTrader: Analyzing GitHub Activity and Stock Price Relationships},
  author={Your Name},
  year={""" + f"""{datetime.now().year}""" + """},
  url={https://github.com/yourusername/commitTrader}
}</pre>
        </div>
    </div>
</body>
</html>
"""

        with open(output_dir / "downloads.html", 'w', encoding='utf-8') as f:
            f.write(html)

    def _generate_github_readme(self, output_dir: Path, title: str, description: str):
        """Generate README for GitHub Pages."""
        readme = f"""# {title}

{description}

## View the Research

🔗 **[View Full Report](./report.html)**

## Quick Links

- [Home](./index.html)
- [Full Report](./report.html)
- [Methodology](./methodology.html)
- [Download Data](./downloads.html)

## About

This website presents research on the relationship between GitHub activity and stock prices
for publicly traded companies using event study methodology.

Generated with [CommitTrader](https://github.com/yourusername/commitTrader)

## Data

All research data is available in the [Downloads](./downloads.html) section.

---

*Last updated: {datetime.now().strftime('%B %d, %Y')}*
"""

        with open(output_dir / "README.md", 'w') as f:
            f.write(readme)
