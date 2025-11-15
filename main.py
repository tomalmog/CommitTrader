#!/usr/bin/env python3
"""
CommitTrader - Main Entry Point

Quantitative research platform analyzing GitHub activity and stock price relationships.
"""

import os
import argparse
import logging
from datetime import datetime, timedelta

from src.analysis.pipeline import AnalysisPipeline
from src.visualization.plots import ResultsVisualizer
from src.data.storage import DataStorage
from src.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for CommitTrader."""
    parser = argparse.ArgumentParser(
        description='CommitTrader: Analyze GitHub activity impact on stock prices'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'collect', 'analyze', 'visualize'],
        default='full',
        help='Analysis mode: full (default), collect, analyze, or visualize'
    )

    parser.add_argument(
        '--tickers',
        type=str,
        nargs='+',
        help='List of stock tickers to analyze (e.g., MSFT GOOGL)'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for analysis (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for analysis (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--max-events',
        type=int,
        help='Maximum number of events to analyze (for testing)'
    )

    parser.add_argument(
        '--github-token',
        type=str,
        help='GitHub personal access token (or set GITHUB_TOKEN env var)'
    )

    parser.add_argument(
        '--skip-collection',
        action='store_true',
        help='Skip data collection and use cached data'
    )

    parser.add_argument(
        '--events-file',
        type=str,
        help='Path to events CSV file (if --skip-collection)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to custom config file'
    )

    parser.add_argument(
        '--no-reports',
        action='store_true',
        help='Skip HTML report and website generation'
    )

    args = parser.parse_args()

    # Load configuration
    config = get_config(args.config)

    # Parse dates
    start_date = None
    end_date = None

    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        # Default: 3 years ago
        start_date = datetime.now() - timedelta(days=365 * 3)

    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    # Get GitHub token
    github_token = args.github_token or os.environ.get('GITHUB_TOKEN')

    if not github_token:
        logger.warning(
            "No GitHub token provided. API rate limit will be 60 requests/hour. "
            "Set GITHUB_TOKEN environment variable or use --github-token for 5000/hour."
        )

    # Initialize pipeline
    pipeline = AnalysisPipeline(github_token=github_token)

    # Run analysis based on mode
    if args.mode == 'full':
        logger.info("Running full analysis pipeline")
        summary = pipeline.run_full_analysis(
            tickers=args.tickers,
            start_date=start_date,
            end_date=end_date,
            max_events=args.max_events,
            skip_collection=args.skip_collection,
            events_file=args.events_file,
            generate_reports=not args.no_reports
        )

        # Print summary
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY")
        print("="*80)
        print(f"Total Events: {summary.get('total_events', 0):,}")
        print(f"Valid Event Studies: {summary.get('valid_event_studies', 0):,}")
        print(f"Companies Analyzed: {summary.get('total_companies', 0)}")
        print(f"\nMean AR (Day 0): {summary.get('overall_statistics', {}).get('mean_ar_day_0', 0)*100:.4f}%")
        print(f"Mean CAR (-5,5): {summary.get('overall_statistics', {}).get('mean_car_5_5', 0)*100:.4f}%")
        print(f"% Positive AR: {summary.get('overall_statistics', {}).get('pct_positive_ar', 0):.2f}%")
        print("\nStatistical Significance:")
        for test_name, result in summary.get('statistical_significance', {}).items():
            sig = result.get('significance_level', 'ns')
            p_val = result.get('p_value', 'N/A')
            print(f"  {test_name}: {sig} (p={p_val:.4f})" if isinstance(p_val, float) else f"  {test_name}: {sig}")
        print("="*80)

        if not args.no_reports:
            print("\n📊 REPORTS GENERATED:")
            print("  • HTML Report: data/processed/reports/report_*.html")
            print("  • Website: docs/index.html")
            print("\n🌐 TO VIEW:")
            print("  1. Open docs/index.html in your browser")
            print("  2. Or run: python -m http.server 8000 --directory docs")
            print("     Then visit: http://localhost:8000")
            print("\n📤 TO PUBLISH ON GITHUB PAGES:")
            print("  1. Push the 'docs' folder to GitHub")
            print("  2. Go to repo Settings > Pages")
            print("  3. Set source to 'docs' folder")
            print("  4. Your site will be live at: https://<username>.github.io/<repo>/")
            print("="*80)

    elif args.mode == 'collect':
        logger.info("Running data collection only")
        events = pipeline.collect_all_data(
            tickers=args.tickers,
            start_date=start_date,
            end_date=end_date
        )
        print(f"\nCollected {len(events):,} events")

    elif args.mode == 'analyze':
        logger.info("Running analysis on cached data")
        if not args.events_file and not args.skip_collection:
            logger.error("Must specify --events-file or --skip-collection for analyze mode")
            return

        summary = pipeline.run_full_analysis(
            tickers=args.tickers,
            start_date=start_date,
            end_date=end_date,
            max_events=args.max_events,
            skip_collection=True,
            events_file=args.events_file
        )

    elif args.mode == 'visualize':
        logger.info("Generating visualizations from latest results")
        storage = DataStorage()
        visualizer = ResultsVisualizer()

        # Load latest results
        latest_results_file = storage.get_latest_analysis('event_studies')
        if not latest_results_file:
            logger.error("No analysis results found. Run analysis first.")
            return

        results = storage.load_event_study_results('full_analysis')

        # Create visualizations
        if results is not None and not results.empty:
            fig_car = visualizer.plot_car_distribution(results)
            storage.save_figure(fig_car, 'car_distribution', 'latest')

            fig_ar = visualizer.plot_ar_by_event_type(results)
            storage.save_figure(fig_ar, 'ar_by_type', 'latest')

            print("\nVisualizations saved to data/processed/figures/")

    logger.info("CommitTrader completed successfully!")


if __name__ == '__main__':
    main()
