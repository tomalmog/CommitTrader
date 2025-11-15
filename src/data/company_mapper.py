"""Company and repository mapping management."""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import json
import csv

import pandas as pd

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompanyMapper:
    """Maps GitHub repositories to publicly traded companies."""

    def __init__(self, mappings_file: Optional[str] = None):
        """
        Initialize company mapper.

        Args:
            mappings_file: Path to mappings file (CSV or JSON)
        """
        self.config = get_config()
        self.mappings_dir = self.config.mappings_dir

        if mappings_file is None:
            mappings_file = self.mappings_dir / "company_repo_mappings.csv"

        self.mappings_file = Path(mappings_file)
        self.mappings = self._load_mappings()

    def _load_mappings(self) -> pd.DataFrame:
        """Load company-repository mappings from file."""
        if not self.mappings_file.exists():
            logger.warning(f"Mappings file not found: {self.mappings_file}")
            logger.info("Creating empty mappings DataFrame")
            return pd.DataFrame(columns=[
                'ticker', 'company_name', 'repo_full_name', 'repo_type',
                'sector', 'primary_repo'
            ])

        # Load based on file type
        if self.mappings_file.suffix == '.csv':
            df = pd.read_csv(self.mappings_file)
        elif self.mappings_file.suffix == '.json':
            df = pd.read_json(self.mappings_file)
        else:
            raise ValueError(f"Unsupported file format: {self.mappings_file.suffix}")

        logger.info(f"Loaded {len(df)} repository mappings for {df['ticker'].nunique()} companies")
        return df

    def save_mappings(self, file_path: Optional[str] = None):
        """
        Save mappings to file.

        Args:
            file_path: Path to save to (defaults to original file)
        """
        if file_path is None:
            file_path = self.mappings_file

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.suffix == '.csv':
            self.mappings.to_csv(file_path, index=False)
        elif file_path.suffix == '.json':
            self.mappings.to_json(file_path, orient='records', indent=2)

        logger.info(f"Saved mappings to {file_path}")

    def add_mapping(
        self,
        ticker: str,
        company_name: str,
        repo_full_name: str,
        repo_type: str = 'primary',
        sector: Optional[str] = None,
        primary_repo: bool = True
    ):
        """
        Add a new company-repository mapping.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            repo_full_name: GitHub repository in format 'owner/repo'
            repo_type: Type of repo (e.g., 'primary', 'subsidiary', 'project')
            sector: Company sector
            primary_repo: Whether this is the primary repo for the company
        """
        new_mapping = pd.DataFrame([{
            'ticker': ticker.upper(),
            'company_name': company_name,
            'repo_full_name': repo_full_name,
            'repo_type': repo_type,
            'sector': sector,
            'primary_repo': primary_repo
        }])

        self.mappings = pd.concat([self.mappings, new_mapping], ignore_index=True)
        logger.info(f"Added mapping: {ticker} -> {repo_full_name}")

    def get_repos_for_ticker(self, ticker: str, primary_only: bool = False) -> List[str]:
        """
        Get repositories for a given ticker.

        Args:
            ticker: Stock ticker symbol
            primary_only: Only return primary repositories

        Returns:
            List of repository full names
        """
        ticker = ticker.upper()
        mask = self.mappings['ticker'] == ticker

        if primary_only:
            mask = mask & self.mappings['primary_repo']

        repos = self.mappings[mask]['repo_full_name'].tolist()
        return repos

    def get_ticker_for_repo(self, repo_full_name: str) -> Optional[str]:
        """
        Get ticker for a given repository.

        Args:
            repo_full_name: GitHub repository in format 'owner/repo'

        Returns:
            Stock ticker or None if not found
        """
        matches = self.mappings[self.mappings['repo_full_name'] == repo_full_name]

        if matches.empty:
            return None

        return matches.iloc[0]['ticker']

    def get_all_tickers(self) -> List[str]:
        """Get list of all tickers in mappings."""
        return self.mappings['ticker'].unique().tolist()

    def get_all_repos(self) -> List[str]:
        """Get list of all repositories in mappings."""
        return self.mappings['repo_full_name'].unique().tolist()

    def get_company_info(self, ticker: str) -> Dict:
        """
        Get company information for a ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Dictionary with company information
        """
        ticker = ticker.upper()
        matches = self.mappings[self.mappings['ticker'] == ticker]

        if matches.empty:
            return {}

        first_match = matches.iloc[0]
        repos = self.get_repos_for_ticker(ticker)

        return {
            'ticker': ticker,
            'company_name': first_match['company_name'],
            'sector': first_match['sector'],
            'num_repos': len(repos),
            'repositories': repos
        }

    def get_mappings_by_sector(self, sector: str) -> pd.DataFrame:
        """
        Get all mappings for a specific sector.

        Args:
            sector: Sector name

        Returns:
            DataFrame with mappings for that sector
        """
        return self.mappings[self.mappings['sector'] == sector]

    def validate_mappings(self) -> Dict[str, any]:
        """
        Validate mapping data quality.

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Check for duplicates
        duplicate_repos = self.mappings[self.mappings.duplicated(subset=['ticker', 'repo_full_name'], keep=False)]
        if not duplicate_repos.empty:
            issues.append(f"Found {len(duplicate_repos)} duplicate ticker-repo pairs")

        # Check for tickers without primary repo
        tickers = self.mappings.groupby('ticker')['primary_repo'].any()
        tickers_without_primary = tickers[~tickers].index.tolist()
        if tickers_without_primary:
            issues.append(f"Tickers without primary repo: {tickers_without_primary}")

        # Check for invalid repo format
        invalid_format = self.mappings[~self.mappings['repo_full_name'].str.contains('/')]
        if not invalid_format.empty:
            issues.append(f"Found {len(invalid_format)} repos with invalid format (missing '/')")

        return {
            'valid': len(issues) == 0,
            'num_companies': self.mappings['ticker'].nunique(),
            'num_repos': len(self.mappings),
            'issues': issues
        }

    def export_for_analysis(self) -> pd.DataFrame:
        """
        Export mappings in format suitable for analysis.

        Returns:
            DataFrame with one row per repo, including company metadata
        """
        return self.mappings[['ticker', 'company_name', 'repo_full_name', 'sector', 'primary_repo']].copy()
