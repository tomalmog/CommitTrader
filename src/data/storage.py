"""Data storage and persistence for analysis results."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import pickle

import pandas as pd

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataStorage:
    """Manages storage and retrieval of analysis data."""

    def __init__(self):
        """Initialize data storage manager."""
        self.config = get_config()
        self.raw_dir = self.config.raw_data_dir
        self.processed_dir = self.config.processed_data_dir

    def save_events(
        self,
        events: pd.DataFrame,
        event_type: str,
        ticker: Optional[str] = None
    ) -> Path:
        """
        Save GitHub events data.

        Args:
            events: DataFrame with event data
            event_type: Type of events (e.g., 'releases', 'commits')
            ticker: Optional ticker symbol for organization

        Returns:
            Path to saved file
        """
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d')
        if ticker:
            filename = f"{ticker}_{event_type}_{timestamp}.csv"
        else:
            filename = f"all_{event_type}_{timestamp}.csv"

        file_path = self.raw_dir / "events" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to CSV
        events.to_csv(file_path, index=False)
        logger.info(f"Saved {len(events)} {event_type} events to {file_path}")

        return file_path

    def load_events(
        self,
        event_type: str,
        ticker: Optional[str] = None,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Load GitHub events data.

        Args:
            event_type: Type of events
            ticker: Optional ticker symbol
            latest: If True, load most recent file

        Returns:
            DataFrame with events or None if not found
        """
        events_dir = self.raw_dir / "events"
        if not events_dir.exists():
            logger.warning(f"Events directory not found: {events_dir}")
            return None

        # Find matching files
        if ticker:
            pattern = f"{ticker}_{event_type}_*.csv"
        else:
            pattern = f"all_{event_type}_*.csv"

        files = sorted(events_dir.glob(pattern))

        if not files:
            logger.warning(f"No event files found matching: {pattern}")
            return None

        # Load latest or first
        file_to_load = files[-1] if latest else files[0]
        logger.info(f"Loading events from {file_to_load}")

        return pd.read_csv(file_to_load, parse_dates=['date'] if 'date' in pd.read_csv(file_to_load, nrows=0).columns else None)

    def save_event_study_results(
        self,
        results: pd.DataFrame,
        analysis_name: str
    ) -> Path:
        """
        Save event study analysis results.

        Args:
            results: DataFrame with event study results
            analysis_name: Name for this analysis run

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"event_study_{analysis_name}_{timestamp}.csv"

        file_path = self.processed_dir / "event_studies" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        results.to_csv(file_path, index=False)
        logger.info(f"Saved event study results to {file_path}")

        # Also save as JSON for easier inspection
        json_path = file_path.with_suffix('.json')
        results.to_json(json_path, orient='records', indent=2, date_format='iso')

        return file_path

    def load_event_study_results(
        self,
        analysis_name: str,
        latest: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Load event study results.

        Args:
            analysis_name: Name of analysis
            latest: Load most recent results

        Returns:
            DataFrame with results or None if not found
        """
        results_dir = self.processed_dir / "event_studies"
        if not results_dir.exists():
            return None

        pattern = f"event_study_{analysis_name}_*.csv"
        files = sorted(results_dir.glob(pattern))

        if not files:
            logger.warning(f"No results found for analysis: {analysis_name}")
            return None

        file_to_load = files[-1] if latest else files[0]
        logger.info(f"Loading results from {file_to_load}")

        return pd.read_csv(file_to_load)

    def save_aggregated_results(
        self,
        results: pd.DataFrame,
        analysis_name: str,
        group_by: str
    ) -> Path:
        """
        Save aggregated analysis results.

        Args:
            results: DataFrame with aggregated results
            analysis_name: Name for this analysis
            group_by: What the results are grouped by

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"aggregated_{analysis_name}_by_{group_by}_{timestamp}.csv"

        file_path = self.processed_dir / "aggregated" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        results.to_csv(file_path, index=False)
        logger.info(f"Saved aggregated results to {file_path}")

        return file_path

    def save_statistical_tests(
        self,
        test_results: Dict[str, Dict],
        analysis_name: str
    ) -> Path:
        """
        Save statistical test results.

        Args:
            test_results: Dictionary with test results
            analysis_name: Name for this analysis

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"statistical_tests_{analysis_name}_{timestamp}.json"

        file_path = self.processed_dir / "statistics" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert numpy types to native Python types for JSON serialization
        cleaned_results = self._clean_for_json(test_results)

        with open(file_path, 'w') as f:
            json.dump(cleaned_results, f, indent=2)

        logger.info(f"Saved statistical test results to {file_path}")
        return file_path

    def save_summary_report(
        self,
        summary: Dict[str, Any],
        analysis_name: str
    ) -> Path:
        """
        Save analysis summary report.

        Args:
            summary: Dictionary with summary information
            analysis_name: Name for this analysis

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"summary_{analysis_name}_{timestamp}.json"

        file_path = self.processed_dir / "summaries" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        cleaned_summary = self._clean_for_json(summary)

        with open(file_path, 'w') as f:
            json.dump(cleaned_summary, f, indent=2)

        logger.info(f"Saved summary report to {file_path}")
        return file_path

    def save_figure(
        self,
        fig,
        figure_name: str,
        analysis_name: str,
        format: str = 'png'
    ) -> Path:
        """
        Save matplotlib figure.

        Args:
            fig: Matplotlib figure object
            figure_name: Name for the figure
            analysis_name: Name of analysis
            format: Image format (png, pdf, svg)

        Returns:
            Path to saved figure
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{figure_name}_{analysis_name}_{timestamp}.{format}"

        file_path = self.processed_dir / "figures" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        fig.savefig(file_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved figure to {file_path}")

        return file_path

    def get_latest_analysis(
        self,
        analysis_type: str = 'event_studies'
    ) -> Optional[Path]:
        """
        Get path to most recent analysis file.

        Args:
            analysis_type: Type of analysis (event_studies, aggregated, etc.)

        Returns:
            Path to latest file or None
        """
        analysis_dir = self.processed_dir / analysis_type
        if not analysis_dir.exists():
            return None

        files = sorted(analysis_dir.glob('*.csv'))
        return files[-1] if files else None

    def list_analyses(
        self,
        analysis_type: str = 'event_studies'
    ) -> List[Path]:
        """
        List all analysis files of a given type.

        Args:
            analysis_type: Type of analysis

        Returns:
            List of file paths
        """
        analysis_dir = self.processed_dir / analysis_type
        if not analysis_dir.exists():
            return []

        return sorted(analysis_dir.glob('*.csv'))

    def create_analysis_snapshot(
        self,
        analysis_name: str,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        statistical_tests: Dict,
        summary: Dict
    ) -> Path:
        """
        Create complete snapshot of an analysis run.

        Args:
            analysis_name: Name for this analysis
            results: Event study results
            aggregated: Aggregated results
            statistical_tests: Statistical test results
            summary: Summary information

        Returns:
            Path to snapshot directory
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = self.processed_dir / "snapshots" / f"{analysis_name}_{timestamp}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Save all components
        results.to_csv(snapshot_dir / "event_study_results.csv", index=False)
        aggregated.to_csv(snapshot_dir / "aggregated_results.csv", index=False)

        with open(snapshot_dir / "statistical_tests.json", 'w') as f:
            json.dump(self._clean_for_json(statistical_tests), f, indent=2)

        with open(snapshot_dir / "summary.json", 'w') as f:
            json.dump(self._clean_for_json(summary), f, indent=2)

        # Save metadata
        metadata = {
            'analysis_name': analysis_name,
            'timestamp': timestamp,
            'num_events': len(results),
            'num_valid_events': len(results[results['valid'] == True]) if 'valid' in results.columns else 0,
        }

        with open(snapshot_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Created analysis snapshot at {snapshot_dir}")
        return snapshot_dir

    def _clean_for_json(self, obj: Any) -> Any:
        """
        Clean object for JSON serialization (convert numpy types, etc.).

        Args:
            obj: Object to clean

        Returns:
            JSON-serializable object
        """
        import numpy as np

        if isinstance(obj, dict):
            return {key: self._clean_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_json(item) for item in obj]
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif pd.isna(obj):
            return None
        else:
            return obj
