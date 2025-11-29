"""Generate interactive HTML reports from analysis results."""

import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """Generates interactive HTML reports with Plotly charts."""

    def __init__(self):
        """Initialize HTML report generator."""
        self.config = get_config()

    def create_interactive_car_plot(self, results: pd.DataFrame) -> str:
        """Create interactive CAR distribution plot."""
        valid_results = results[results['valid'] == True].copy()

        if 'CAR_-5_5' not in valid_results.columns:
            return ""

        # Create histogram with event type colors
        fig = px.histogram(
            valid_results,
            x='CAR_-5_5',
            color='event_type' if 'event_type' in valid_results.columns else None,
            nbins=50,
            title='Distribution of Cumulative Abnormal Returns (-5, +5 days)',
            labels={'CAR_-5_5': 'CAR (-5, +5) (%)', 'count': 'Frequency'},
            barmode='overlay',
            opacity=0.7
        )

        fig.update_xaxes(tickformat='.2%')
        fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Zero CAR")
        fig.update_layout(template='plotly_white', height=500)

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def create_ar_comparison_plot(self, results: pd.DataFrame) -> str:
        """Create interactive AR comparison by event type."""
        valid_results = results[results['valid'] == True].copy()

        if 'event_type' not in valid_results.columns or 'ar_day_0' not in valid_results.columns:
            return ""

        # Calculate statistics by event type
        stats = valid_results.groupby('event_type')['ar_day_0'].agg([
            'mean', 'median', 'std', 'count'
        ]).reset_index()

        stats['sem'] = stats['std'] / np.sqrt(stats['count'])

        fig = go.Figure()

        # Add bars with error bars
        fig.add_trace(go.Bar(
            x=stats['event_type'],
            y=stats['mean'] * 100,
            error_y=dict(type='data', array=stats['sem'] * 100),
            name='Mean AR (Day 0)',
            text=[f"{v:.3f}%" for v in stats['mean'] * 100],
            textposition='outside'
        ))

        fig.update_layout(
            title='Average Abnormal Returns by Event Type',
            xaxis_title='Event Type',
            yaxis_title='Mean AR Day 0 (%)',
            template='plotly_white',
            height=500,
            showlegend=False
        )

        fig.add_hline(y=0, line_dash="dash", line_color="red")

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def create_timeline_plot(self, events: pd.DataFrame, results: pd.DataFrame) -> str:
        """Create interactive timeline of events and returns."""
        merged = events.merge(
            results[['ticker', 'event_date', 'ar_day_0']],
            left_on=['ticker', 'date'],
            right_on=['ticker', 'event_date'],
            how='inner'
        )

        if merged.empty:
            return ""

        # Aggregate by month
        monthly = merged.groupby([
            pd.Grouper(key='date', freq='ME'),
            'event_type'
        ]).agg({
            'ar_day_0': 'mean',
            'ticker': 'count'
        }).reset_index()

        monthly.columns = ['date', 'event_type', 'mean_ar', 'event_count']

        # Create subplot with two y-axes
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Event Frequency Over Time', 'Average Abnormal Returns Over Time'),
            vertical_spacing=0.15
        )

        # Event counts by type
        for event_type in monthly['event_type'].unique():
            data = monthly[monthly['event_type'] == event_type]
            fig.add_trace(
                go.Bar(
                    x=data['date'],
                    y=data['event_count'],
                    name=event_type,
                    legendgroup=event_type
                ),
                row=1, col=1
            )

        # Average AR over time
        ar_monthly = merged.groupby(pd.Grouper(key='date', freq='ME'))['ar_day_0'].mean().reset_index()
        fig.add_trace(
            go.Scatter(
                x=ar_monthly['date'],
                y=ar_monthly['ar_day_0'] * 100,
                mode='lines+markers',
                name='Mean AR',
                line=dict(width=3),
                showlegend=False
            ),
            row=2, col=1
        )

        fig.add_hline(y=0, line_dash="dash", line_color="red", row=2, col=1)

        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Number of Events", row=1, col=1)
        fig.update_yaxes(title_text="Mean AR (%)", row=2, col=1)

        fig.update_layout(template='plotly_white', height=800, barmode='stack')

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def create_top_events_plot(self, results: pd.DataFrame, n: int = 20) -> str:
        """Create interactive plot of top events."""
        valid_results = results[results['valid'] == True].copy()

        if 'CAR_-5_5' not in valid_results.columns:
            return ""

        # Top positive and negative
        top_positive = valid_results.nlargest(n, 'CAR_-5_5')
        top_negative = valid_results.nsmallest(n, 'CAR_-5_5')

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(f'Top {n} Events (Positive CAR)', f'Top {n} Events (Negative CAR)')
        )

        # Positive
        fig.add_trace(
            go.Bar(
                y=[f"{row['ticker']}<br>{pd.to_datetime(row['event_date']).strftime('%Y-%m-%d')}"
                   for _, row in top_positive.iterrows()],
                x=top_positive['CAR_-5_5'] * 100,
                orientation='h',
                marker_color='green',
                name='Positive',
                text=[f"{v:.2f}%" for v in top_positive['CAR_-5_5'] * 100],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=1
        )

        # Negative
        fig.add_trace(
            go.Bar(
                y=[f"{row['ticker']}<br>{pd.to_datetime(row['event_date']).strftime('%Y-%m-%d')}"
                   for _, row in top_negative.iterrows()],
                x=top_negative['CAR_-5_5'] * 100,
                orientation='h',
                marker_color='red',
                name='Negative',
                text=[f"{v:.2f}%" for v in top_negative['CAR_-5_5'] * 100],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=2
        )

        fig.update_xaxes(title_text="CAR (-5,5) %")
        fig.update_layout(template='plotly_white', height=600)

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def generate_html_report(
        self,
        events: pd.DataFrame,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        statistical_tests: Dict,
        summary: Dict,
        output_path: Optional[Path] = None,
        title: str = "CommitTrader Analysis Report"
    ) -> Path:
        """
        Generate complete HTML report.

        Args:
            events: Events data
            results: Event study results
            aggregated: Aggregated results
            statistical_tests: Statistical tests
            summary: Summary dictionary
            output_path: Output file path
            title: Report title

        Returns:
            Path to generated HTML file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.config.processed_data_dir / "reports" / f"report_{timestamp}.html"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate plots
        car_plot = self.create_interactive_car_plot(results)
        ar_plot = self.create_ar_comparison_plot(results)
        timeline_plot = self.create_timeline_plot(events, results)
        top_events_plot = self.create_top_events_plot(results)

        # Generate statistics table
        valid_results = results[results['valid'] == True]
        stats_html = self._generate_stats_table(valid_results, summary)

        # Generate significance table
        sig_html = self._generate_significance_table(statistical_tests)

        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --color-bg: #fafafa;
            --color-text: #1a1a1a;
            --color-text-light: #666;
            --color-border: #e0e0e0;
            --color-accent: #2c2c2c;
            --font-serif: 'Georgia', 'Times New Roman', serif;
            --font-sans: 'Helvetica Neue', Arial, sans-serif;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: var(--font-sans);
            line-height: 1.7;
            color: var(--color-text);
            background: var(--color-bg);
        }}

        .nav {{
            background: white;
            border-bottom: 1px solid var(--color-border);
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
        }}

        .nav a {{
            color: var(--color-text);
            text-decoration: none;
            transition: opacity 0.4s ease;
            opacity: 0.6;
        }}

        .nav a:hover {{
            opacity: 1;
        }}

        .header {{
            background: white;
            border-bottom: 1px solid var(--color-border);
            padding: 60px 50px;
            margin-bottom: 50px;
            text-align: center;
        }}

        .header h1 {{
            font-family: var(--font-serif);
            font-size: 2.8em;
            font-weight: 400;
            color: var(--color-accent);
            margin-bottom: 15px;
            letter-spacing: -0.02em;
        }}

        .header .subtitle {{
            color: var(--color-text-light);
            font-size: 1em;
            margin: 10px 0;
            font-weight: 300;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 0 40px 80px;
        }}

        .section {{
            background: white;
            padding: 50px;
            margin-bottom: 30px;
            border: 1px solid var(--color-border);
            border-top: none;
        }}

        .section:first-of-type {{
            border-top: 1px solid var(--color-border);
        }}

        .section h2 {{
            font-family: var(--font-serif);
            font-size: 1.8em;
            font-weight: 400;
            color: var(--color-accent);
            margin: 0 0 30px 0;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--color-border);
            letter-spacing: -0.01em;
        }}

        .section h3 {{
            font-family: var(--font-serif);
            font-size: 1.3em;
            font-weight: 400;
            color: var(--color-accent);
            margin: 30px 0 15px 0;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1px;
            background: var(--color-border);
            border: 1px solid var(--color-border);
            margin: 30px 0;
        }}

        .stat-card {{
            background: white;
            padding: 35px 25px;
            text-align: center;
            transition: background 0.4s ease;
        }}

        .stat-card:hover {{
            background: #fcfcfc;
        }}

        .stat-card .label {{
            font-size: 0.75em;
            color: var(--color-text-light);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            font-weight: 500;
        }}

        .stat-card .value {{
            font-size: 2em;
            font-weight: 300;
            color: var(--color-accent);
            font-family: var(--font-serif);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            border: 1px solid var(--color-border);
        }}

        th, td {{
            padding: 16px 20px;
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }}

        th {{
            background: #f9f9f9;
            color: var(--color-text);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75em;
            letter-spacing: 1px;
        }}

        tr:hover {{
            background: #fcfcfc;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .significance {{
            display: inline-block;
            padding: 3px 10px;
            font-size: 0.85em;
            font-weight: 400;
            letter-spacing: 0.5px;
        }}

        .sig-high {{
            background: #1a1a1a;
            color: white;
        }}

        .sig-med {{
            background: #666;
            color: white;
        }}

        .sig-low {{
            background: #999;
            color: white;
        }}

        .sig-none {{
            background: #e5e7eb;
            color: #6b7280;
        }}

        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}

        .methodology {{
            background: #f0f4ff;
            padding: 20px;
            border-left: 4px solid #667eea;
            margin: 20px 0;
        }}

        .plot-container {{
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <nav class="nav">
        <div class="nav-content">
            <a href="index.html">Home</a>
            <a href="report.html">Full Report</a>
            <a href="visualizations.html">Visualizations</a>
            <a href="methodology.html">Methodology</a>
            <a href="downloads.html">Downloads</a>
        </div>
    </nav>

    <div class="header">
        <h1>{title}</h1>
        <div class="subtitle">
            Quantitative Analysis of GitHub Activity and Stock Price Relationships
        </div>
        <div class="subtitle">
            Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </div>
    </div>

    <div class="container">
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Events Analyzed</div>
                <div class="value">{summary.get('total_events', 0):,}</div>
            </div>
            <div class="stat-card">
                <div class="label">Valid Event Studies</div>
                <div class="value">{summary.get('valid_event_studies', 0):,}</div>
            </div>
            <div class="stat-card">
                <div class="label">Companies Analyzed</div>
                <div class="value">{summary.get('total_companies', 0)}</div>
            </div>
            <div class="stat-card">
                <div class="label">Repositories Tracked</div>
                <div class="value">{summary.get('total_repositories', 0)}</div>
            </div>
        </div>

        {stats_html}
    </div>

    <div class="section">
        <h2>Key Findings</h2>
        <div class="methodology">
            <h3 style="margin-top: 0;">Research Question</h3>
            <p>
                Does public GitHub activity from open-source repositories associated with
                publicly traded companies have measurable impact on stock prices?
            </p>

            <h3>Main Results</h3>
            <ul>
                <li><strong>Mean Abnormal Return (Day 0):</strong> {summary.get('overall_statistics', {}).get('mean_ar_day_0', 0)*100:.4f}%</li>
                <li><strong>Mean CAR (-5, +5):</strong> {summary.get('overall_statistics', {}).get('mean_car_5_5', 0)*100:.4f}%</li>
                <li><strong>Events with Positive Returns:</strong> {summary.get('overall_statistics', {}).get('pct_positive_ar', 0):.1f}%</li>
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>Statistical Significance</h2>
        {sig_html}
        <p style="margin-top: 20px; font-size: 0.9em; color: #666;">
            <strong>Significance Levels:</strong>
            <span class="significance sig-high">***</span> p < 0.01 (highly significant) |
            <span class="significance sig-med">**</span> p < 0.05 (significant) |
            <span class="significance sig-low">*</span> p < 0.10 (marginally significant) |
            <span class="significance sig-none">ns</span> not significant
        </p>
    </div>

    <div class="section">
        <h2>Cumulative Abnormal Returns Distribution</h2>
        <div class="plot-container">
            {car_plot}
        </div>
    </div>

    <div class="section">
        <h2>Abnormal Returns by Event Type</h2>
        <div class="plot-container">
            {ar_plot}
        </div>
    </div>

    <div class="section">
        <h2>Event Timeline Analysis</h2>
        <div class="plot-container">
            {timeline_plot}
        </div>
    </div>

    <div class="section">
        <h2>Top Events</h2>
        <div class="plot-container">
            {top_events_plot}
        </div>
    </div>

    <div class="section">
        <h2>Methodology</h2>
        <div class="methodology">
            <h3 style="margin-top: 0;">Event Study Approach</h3>
            <ol>
                <li><strong>Event Identification:</strong> GitHub releases, commit spikes, and milestones</li>
                <li><strong>Expected Returns:</strong> Market model with OLS parameter estimation</li>
                <li><strong>Abnormal Returns:</strong> AR = Actual Return - Expected Return</li>
                <li><strong>Statistical Testing:</strong> Multiple parametric and non-parametric tests</li>
                <li><strong>Aggregation:</strong> Cross-sectional analysis across all events</li>
            </ol>

            <h3>Event Windows</h3>
            <ul>
                <li>Event Window: -5 to +5 trading days around event</li>
                <li>Estimation Window: -130 to -31 days before event</li>
                <li>Market Index: S&P 500 (^GSPC)</li>
            </ul>
        </div>
    </div>

    </div>

    <div class="footer">
        <p>
            <strong>CommitTrader</strong> - Quantitative Research Platform<br>
            This report is for research purposes only and should not be used as investment advice.<br>
            Past performance does not guarantee future results.
        </p>
    </div>
</body>
</html>
"""

        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML report generated: {output_path}")
        return output_path

    def _generate_stats_table(self, results: pd.DataFrame, summary: Dict) -> str:
        """Generate HTML table of statistics."""
        stats = summary.get('overall_statistics', {})

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Mean AR (Day 0)</td>
                    <td>{stats.get('mean_ar_day_0', 0)*100:.4f}%</td>
                </tr>
                <tr>
                    <td>Median AR (Day 0)</td>
                    <td>{stats.get('median_ar_day_0', 0)*100:.4f}%</td>
                </tr>
                <tr>
                    <td>Mean CAR (-5, +5)</td>
                    <td>{stats.get('mean_car_5_5', 0)*100:.4f}%</td>
                </tr>
                <tr>
                    <td>% Events with Positive AR</td>
                    <td>{stats.get('pct_positive_ar', 0):.1f}%</td>
                </tr>
                <tr>
                    <td>Standard Deviation</td>
                    <td>{results['ar_day_0'].std()*100:.4f}%</td>
                </tr>
            </tbody>
        </table>
        """

    def _generate_significance_table(self, statistical_tests: Dict) -> str:
        """Generate HTML table of statistical test results."""
        rows = []

        for test_name, result in statistical_tests.items():
            if not result.get('valid', False):
                continue

            p_value = result.get('p_value', np.nan)
            sig_level = result.get('significance_level', 'ns')

            # CSS class for significance
            if sig_level == '***':
                css_class = 'sig-high'
            elif sig_level == '**':
                css_class = 'sig-med'
            elif sig_level == '*':
                css_class = 'sig-low'
            else:
                css_class = 'sig-none'

            if np.isnan(p_value):
                p_value_display = "N/A"
            else:
                p_value_display = f"{p_value:.4f}"

            rows.append(f"""
                <tr>
                    <td>{test_name}</td>
                    <td>{p_value_display}</td>
                    <td><span class="significance {css_class}">{sig_level}</span></td>
                    <td>{result.get('n', 'N/A')}</td>
                </tr>
            """)

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Test</th>
                    <th>P-Value</th>
                    <th>Significance</th>
                    <th>N</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
