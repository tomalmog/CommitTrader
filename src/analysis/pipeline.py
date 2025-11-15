"""Main analysis pipeline for CommitTrader."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from ..config import get_config
from ..data.github_collector import GitHubCollector
from ..data.stock_collector import StockCollector
from ..data.company_mapper import CompanyMapper
from ..data.storage import DataStorage
from .event_study import EventStudy
from .statistics import StatisticalTests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Main pipeline for running complete analysis."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize analysis pipeline.

        Args:
            github_token: GitHub personal access token
        """
        self.config = get_config()
        self.github_collector = GitHubCollector(github_token)
        self.stock_collector = StockCollector()
        self.company_mapper = CompanyMapper()
        self.storage = DataStorage()
        self.event_study = EventStudy()
        self.statistics = StatisticalTests()

    def collect_all_data(
        self,
        tickers: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Collect GitHub events for all companies.

        Args:
            tickers: List of tickers to analyze (None = all mapped companies)
            start_date: Start date for collection
            end_date: End date for collection

        Returns:
            DataFrame with all events
        """
        # Get tickers to analyze
        if tickers is None:
            tickers = self.company_mapper.get_all_tickers()

        logger.info(f"Collecting data for {len(tickers)} companies")

        all_events = []

        for ticker in tqdm(tickers, desc="Collecting GitHub data"):
            # Get repositories for this ticker
            repos = self.company_mapper.get_repos_for_ticker(ticker)

            if not repos:
                logger.warning(f"No repositories mapped for {ticker}")
                continue

            # Collect events from each repository
            for repo in repos:
                try:
                    events = self.github_collector.collect_all_events(
                        repo, start_date, end_date
                    )

                    # Process releases
                    if 'releases' in events and not events['releases'].empty:
                        releases = events['releases'].copy()
                        releases['ticker'] = ticker
                        releases['event_type'] = 'release'
                        releases['date'] = releases['published_at']
                        all_events.append(releases[['ticker', 'repo', 'date', 'event_type', 'tag_name', 'name']])

                    # Process commit spikes
                    if 'commit_spikes' in events and not events['commit_spikes'].empty:
                        spikes = events['commit_spikes'].copy()
                        spikes['ticker'] = ticker
                        spikes['event_type'] = 'commit_spike'
                        all_events.append(spikes[['ticker', 'repo', 'date', 'event_type', 'num_commits', 'z_score']])

                except Exception as e:
                    logger.error(f"Error collecting events for {repo}: {e}")
                    continue

        if not all_events:
            logger.warning("No events collected")
            return pd.DataFrame()

        # Combine all events
        events_df = pd.concat(all_events, ignore_index=True)
        events_df['date'] = pd.to_datetime(events_df['date'])

        logger.info(f"Collected {len(events_df)} total events")

        # Save events
        self.storage.save_events(events_df, 'all_events')

        return events_df

    def validate_event_data(
        self,
        events: pd.DataFrame,
        min_events_per_ticker: int = 5
    ) -> pd.DataFrame:
        """
        Validate and filter event data.

        Args:
            events: DataFrame with events
            min_events_per_ticker: Minimum events required per ticker

        Returns:
            Filtered DataFrame
        """
        logger.info("Validating event data")

        # Count events per ticker
        event_counts = events.groupby('ticker').size()
        valid_tickers = event_counts[event_counts >= min_events_per_ticker].index

        logger.info(f"Found {len(valid_tickers)} tickers with at least {min_events_per_ticker} events")

        # Filter events
        filtered = events[events['ticker'].isin(valid_tickers)].copy()

        # Remove events too close together (if configured)
        if self.config.get('events.releases.enabled'):
            min_days = self.config.get('events.releases.min_days_between', 1)
            if min_days > 0:
                filtered = filtered.sort_values(['ticker', 'date'])
                filtered['days_since_last'] = filtered.groupby('ticker')['date'].diff().dt.days
                filtered = filtered[(filtered['days_since_last'].isna()) |
                                  (filtered['days_since_last'] >= min_days)]

        logger.info(f"After validation: {len(filtered)} events")

        return filtered

    def run_event_studies(
        self,
        events: pd.DataFrame,
        max_events: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Run event studies for all events.

        Args:
            events: DataFrame with events
            max_events: Maximum number of events to analyze (for testing)

        Returns:
            DataFrame with event study results
        """
        logger.info(f"Running event studies for {len(events)} events")

        # Limit events if specified (useful for testing)
        if max_events and len(events) > max_events:
            logger.info(f"Limiting to {max_events} events for analysis")
            events = events.sample(n=max_events, random_state=42)

        results = []

        for idx, event in tqdm(events.iterrows(), total=len(events), desc="Analyzing events"):
            try:
                result = self.event_study.analyze_event(
                    ticker=event['ticker'],
                    event_date=event['date'],
                    event_type=event['event_type'],
                    event_metadata={
                        'repo': event.get('repo'),
                        'tag_name': event.get('tag_name'),
                        'num_commits': event.get('num_commits'),
                        'z_score': event.get('z_score'),
                    }
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Error analyzing event {idx}: {e}")
                continue

        results_df = pd.DataFrame(results)
        logger.info(f"Completed {len(results_df)} event studies")

        # Save results
        self.storage.save_event_study_results(results_df, 'full_analysis')

        return results_df

    def aggregate_and_analyze(
        self,
        results: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Aggregate results and perform statistical analysis.

        Args:
            results: DataFrame with event study results

        Returns:
            Tuple of (aggregated results, statistical test results)
        """
        logger.info("Aggregating results and running statistical tests")

        # Aggregate by event type
        aggregated_by_type = self.event_study.aggregate_results(
            results, group_by='event_type'
        )

        # Aggregate by ticker
        aggregated_by_ticker = self.event_study.aggregate_results(
            results, group_by='ticker'
        )

        # Run statistical tests
        statistical_tests = self.statistics.perform_all_tests(results)

        # Create summary tables
        test_summary = self.statistics.create_summary_table(statistical_tests)

        # Save aggregated results
        if not aggregated_by_type.empty:
            self.storage.save_aggregated_results(
                aggregated_by_type, 'full_analysis', 'event_type'
            )

        if not aggregated_by_ticker.empty:
            self.storage.save_aggregated_results(
                aggregated_by_ticker, 'full_analysis', 'ticker'
            )

        # Save statistical tests
        self.storage.save_statistical_tests(statistical_tests, 'full_analysis')

        return aggregated_by_type, statistical_tests

    def generate_summary(
        self,
        events: pd.DataFrame,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        statistical_tests: Dict
    ) -> Dict:
        """
        Generate summary report of analysis.

        Args:
            events: DataFrame with events
            results: Event study results
            aggregated: Aggregated results
            statistical_tests: Statistical test results

        Returns:
            Summary dictionary
        """
        valid_results = results[results['valid'] == True]

        summary = {
            'analysis_date': datetime.now().isoformat(),
            'total_events': len(events),
            'total_companies': events['ticker'].nunique(),
            'total_repositories': events['repo'].nunique() if 'repo' in events.columns else 0,
            'valid_event_studies': len(valid_results),
            'event_types': events['event_type'].value_counts().to_dict(),
            'overall_statistics': {
                'mean_ar_day_0': valid_results['ar_day_0'].mean() if 'ar_day_0' in valid_results.columns else None,
                'median_ar_day_0': valid_results['ar_day_0'].median() if 'ar_day_0' in valid_results.columns else None,
                'mean_car_5_5': valid_results['CAR_-5_5'].mean() if 'CAR_-5_5' in valid_results.columns else None,
                'pct_positive_ar': (valid_results['ar_day_0'] > 0).mean() * 100 if 'ar_day_0' in valid_results.columns else None,
            },
            'statistical_significance': {
                test_name: {
                    'significant': test_result.get('significant', False),
                    'p_value': test_result.get('p_value'),
                    'significance_level': test_result.get('significance_level')
                }
                for test_name, test_result in statistical_tests.items()
                if test_result.get('valid', False)
            },
            'by_event_type': aggregated.to_dict('records') if not aggregated.empty else [],
        }

        # Save summary
        self.storage.save_summary_report(summary, 'full_analysis')

        return summary

    def run_full_analysis(
        self,
        tickers: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_events: Optional[int] = None,
        skip_collection: bool = False,
        events_file: Optional[str] = None,
        generate_reports: bool = True
    ) -> Dict:
        """
        Run complete analysis pipeline.

        Args:
            tickers: List of tickers to analyze
            start_date: Start date for analysis
            end_date: End date for analysis
            max_events: Maximum events to analyze (for testing)
            skip_collection: Skip data collection and use cached data
            events_file: Path to events CSV file (if skip_collection=True)
            generate_reports: Generate HTML reports and website

        Returns:
            Summary dictionary
        """
        logger.info("="*80)
        logger.info("Starting CommitTrader Analysis Pipeline")
        logger.info("="*80)

        # Step 1: Collect data
        if skip_collection and events_file:
            logger.info(f"Loading events from {events_file}")
            events = pd.read_csv(events_file, parse_dates=['date'])
        elif skip_collection:
            logger.info("Loading cached events")
            events = self.storage.load_events('all_events')
            if events is None:
                raise ValueError("No cached events found. Run collection first.")
        else:
            events = self.collect_all_data(tickers, start_date, end_date)

        if events.empty:
            logger.error("No events to analyze")
            return {}

        # Step 2: Validate data
        events = self.validate_event_data(
            events,
            min_events_per_ticker=self.config.get('analysis.min_events_per_company', 5)
        )

        # Step 3: Run event studies
        results = self.run_event_studies(events, max_events)

        if results.empty:
            logger.error("No valid event study results")
            return {}

        # Step 4: Aggregate and analyze
        aggregated, statistical_tests = self.aggregate_and_analyze(results)

        # Step 5: Generate summary
        summary = self.generate_summary(events, results, aggregated, statistical_tests)

        # Step 6: Create snapshot
        snapshot_dir = self.storage.create_analysis_snapshot(
            'full_analysis',
            results,
            aggregated,
            statistical_tests,
            summary
        )

        # Step 7: Generate reports (if requested)
        if generate_reports:
            logger.info("Generating HTML reports...")
            self.generate_html_reports(events, results, aggregated, statistical_tests, summary)

        logger.info("="*80)
        logger.info("Analysis Complete!")
        logger.info(f"Results saved to: {snapshot_dir}")
        logger.info("="*80)

        return summary

    def generate_html_reports(
        self,
        events: pd.DataFrame,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        statistical_tests: Dict,
        summary: Dict
    ):
        """Generate HTML reports and website."""
        try:
            from ..reporting.html_generator import HTMLReportGenerator
            from ..reporting.website_generator import WebsiteGenerator

            # Generate standalone HTML report
            html_gen = HTMLReportGenerator()
            report_path = html_gen.generate_html_report(
                events, results, aggregated, statistical_tests, summary
            )
            logger.info(f"HTML report generated: {report_path}")

            # Generate website
            website_gen = WebsiteGenerator()
            website_dir = website_gen.generate_website(
                events, results, aggregated, statistical_tests, summary
            )
            logger.info(f"Website generated: {website_dir}")
            logger.info(f"Open {website_dir}/index.html in your browser")

        except ImportError as e:
            logger.warning(f"Could not generate reports: {e}")
            logger.warning("Make sure plotly is installed: pip install plotly")
