"""GitHub data collection for repository events and activity."""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import json

from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.GitRelease import GitRelease
from github.Commit import Commit
import pandas as pd
from tqdm import tqdm

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubCollector:
    """Collects GitHub repository data for analysis."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub collector.

        Args:
            github_token: GitHub personal access token. If None, uses unauthenticated access.
        """
        self.config = get_config()

        # Initialize GitHub client
        if github_token is None:
            github_token = self.config.get_github_token()

        if github_token:
            self.github = Github(github_token)
            logger.info("GitHub API initialized with authentication (5000 requests/hour)")
        else:
            self.github = Github()
            logger.warning("GitHub API initialized without authentication (60 requests/hour)")

        self.cache_dir = self.config.raw_data_dir / "github"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        rate_limit = self.github.get_rate_limit()
        return {
            'core_remaining': rate_limit.core.remaining,
            'core_limit': rate_limit.core.limit,
            'core_reset': rate_limit.core.reset,
            'search_remaining': rate_limit.search.remaining,
            'search_limit': rate_limit.search.limit,
        }

    def _wait_for_rate_limit(self):
        """Wait if rate limit is low."""
        rate_limit = self.github.get_rate_limit()
        if rate_limit.core.remaining < 10:
            sleep_time = (rate_limit.core.reset - datetime.utcnow()).total_seconds() + 10
            if sleep_time > 0:
                logger.warning(f"Rate limit low. Sleeping for {sleep_time:.0f} seconds...")
                time.sleep(sleep_time)

    def get_repository(self, repo_full_name: str) -> Repository:
        """
        Get repository object.

        Args:
            repo_full_name: Repository name in format 'owner/repo'

        Returns:
            GitHub Repository object
        """
        try:
            return self.github.get_repo(repo_full_name)
        except GithubException as e:
            logger.error(f"Error fetching repository {repo_full_name}: {e}")
            raise

    def collect_releases(
        self,
        repo_full_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_prerelease: bool = False
    ) -> pd.DataFrame:
        """
        Collect release events from a repository.

        Args:
            repo_full_name: Repository name in format 'owner/repo'
            start_date: Start date for collection
            end_date: End date for collection
            include_prerelease: Whether to include pre-releases

        Returns:
            DataFrame with release information
        """
        logger.info(f"Collecting releases for {repo_full_name}")

        # Check cache
        cache_file = self.cache_dir / f"{repo_full_name.replace('/', '_')}_releases.json"
        if self.config.get('collection.cache_enabled') and cache_file.exists():
            logger.info(f"Loading releases from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                releases_data = json.load(f)
            df = pd.DataFrame(releases_data)
            if not df.empty:
                df['published_at'] = pd.to_datetime(df['published_at'])
                return self._filter_by_date(df, start_date, end_date)

        self._wait_for_rate_limit()
        repo = self.get_repository(repo_full_name)

        releases = []
        try:
            for release in repo.get_releases():
                # Skip pre-releases if configured
                if release.prerelease and not include_prerelease:
                    continue

                release_data = {
                    'repo': repo_full_name,
                    'tag_name': release.tag_name,
                    'name': release.title or release.tag_name,
                    'published_at': release.published_at,
                    'created_at': release.created_at,
                    'prerelease': release.prerelease,
                    'draft': release.draft,
                    'author': release.author.login if release.author else None,
                    'url': release.html_url,
                }
                releases.append(release_data)

                # Respect rate limits
                if self.config.get('collection.respect_rate_limits'):
                    time.sleep(self.config.get('collection.sleep_between_requests', 0.5))

        except GithubException as e:
            logger.error(f"Error collecting releases for {repo_full_name}: {e}")

        df = pd.DataFrame(releases)

        # Cache results
        if self.config.get('collection.cache_enabled') and not df.empty:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(df.to_dict('records'), f, default=str, indent=2)

        if df.empty:
            return df

        df['published_at'] = pd.to_datetime(df['published_at'])
        return self._filter_by_date(df, start_date, end_date)

    def collect_commits(
        self,
        repo_full_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        branch: str = 'main'
    ) -> pd.DataFrame:
        """
        Collect commit activity from a repository.

        Args:
            repo_full_name: Repository name in format 'owner/repo'
            start_date: Start date for collection
            end_date: End date for collection
            branch: Branch to collect commits from

        Returns:
            DataFrame with commit information
        """
        logger.info(f"Collecting commits for {repo_full_name}")

        # Check cache
        cache_file = self.cache_dir / f"{repo_full_name.replace('/', '_')}_commits.json"
        if self.config.get('collection.cache_enabled') and cache_file.exists():
            logger.info(f"Loading commits from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                commits_data = json.load(f)
            df = pd.DataFrame(commits_data)
            if not df.empty:
                df['commit_date'] = pd.to_datetime(df['commit_date'])
                return self._filter_by_date(df, start_date, end_date, 'commit_date')

        self._wait_for_rate_limit()
        repo = self.get_repository(repo_full_name)

        commits = []
        try:
            # Try main branch first, fallback to master
            try:
                commit_generator = repo.get_commits(sha=branch, since=start_date, until=end_date)
            except GithubException:
                logger.info(f"Branch '{branch}' not found, trying 'master'")
                commit_generator = repo.get_commits(sha='master', since=start_date, until=end_date)

            for commit in tqdm(commit_generator, desc=f"Fetching commits"):
                commit_data = {
                    'repo': repo_full_name,
                    'sha': commit.sha,
                    'commit_date': commit.commit.author.date,
                    'author': commit.commit.author.name,
                    'author_login': commit.author.login if commit.author else None,
                    'message': commit.commit.message.split('\n')[0],  # First line only
                    'additions': commit.stats.additions if commit.stats else 0,
                    'deletions': commit.stats.deletions if commit.stats else 0,
                    'total_changes': commit.stats.total if commit.stats else 0,
                }
                commits.append(commit_data)

                # Respect rate limits
                if self.config.get('collection.respect_rate_limits'):
                    time.sleep(self.config.get('collection.sleep_between_requests', 0.5))

        except GithubException as e:
            logger.error(f"Error collecting commits for {repo_full_name}: {e}")

        df = pd.DataFrame(commits)

        # Cache results
        if self.config.get('collection.cache_enabled') and not df.empty:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(df.to_dict('records'), f, default=str, indent=2)

        if df.empty:
            return df

        df['commit_date'] = pd.to_datetime(df['commit_date'])
        return df

    def aggregate_daily_commits(self, commits_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate commits by day.

        Args:
            commits_df: DataFrame with individual commits

        Returns:
            DataFrame with daily commit aggregates
        """
        if commits_df.empty:
            return pd.DataFrame()

        daily = commits_df.groupby([pd.Grouper(key='commit_date', freq='D'), 'repo']).agg({
            'sha': 'count',
            'additions': 'sum',
            'deletions': 'sum',
            'total_changes': 'sum',
            'author_login': 'nunique'
        }).reset_index()

        daily.columns = ['date', 'repo', 'num_commits', 'total_additions',
                        'total_deletions', 'total_changes', 'unique_authors']

        return daily

    def detect_commit_spikes(
        self,
        daily_commits: pd.DataFrame,
        threshold: float = 2.0
    ) -> pd.DataFrame:
        """
        Detect unusual spikes in commit activity.

        Args:
            daily_commits: DataFrame with daily commit counts
            threshold: Number of standard deviations above mean to flag as spike

        Returns:
            DataFrame with spike events
        """
        if daily_commits.empty:
            return pd.DataFrame()

        # Calculate rolling statistics
        daily_commits = daily_commits.sort_values('date')
        daily_commits['rolling_mean'] = daily_commits['num_commits'].rolling(window=30, min_periods=7).mean()
        daily_commits['rolling_std'] = daily_commits['num_commits'].rolling(window=30, min_periods=7).std()

        # Identify spikes
        daily_commits['z_score'] = (
            (daily_commits['num_commits'] - daily_commits['rolling_mean']) /
            daily_commits['rolling_std']
        )

        spikes = daily_commits[daily_commits['z_score'] > threshold].copy()
        spikes['event_type'] = 'commit_spike'

        return spikes[['date', 'repo', 'num_commits', 'z_score', 'event_type']]

    def get_repository_metadata(self, repo_full_name: str) -> Dict[str, Any]:
        """
        Get repository metadata.

        Args:
            repo_full_name: Repository name in format 'owner/repo'

        Returns:
            Dictionary with repository metadata
        """
        self._wait_for_rate_limit()
        repo = self.get_repository(repo_full_name)

        return {
            'repo': repo_full_name,
            'description': repo.description,
            'created_at': repo.created_at,
            'stars': repo.stargazers_count,
            'forks': repo.forks_count,
            'watchers': repo.watchers_count,
            'open_issues': repo.open_issues_count,
            'language': repo.language,
            'size': repo.size,
            'topics': repo.get_topics(),
            'license': repo.license.name if repo.license else None,
        }

    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        date_col: str = 'published_at'
    ) -> pd.DataFrame:
        """Filter DataFrame by date range."""
        if df.empty:
            return df

        # Make dates timezone-aware if column has timezone info
        if start_date and pd.api.types.is_datetime64_any_dtype(df[date_col]):
            if df[date_col].dt.tz is not None:
                # Column has timezone, make start_date timezone-aware
                if start_date.tzinfo is None:
                    import pytz
                    start_date = pytz.UTC.localize(start_date)
            df = df[df[date_col] >= start_date]

        if end_date and pd.api.types.is_datetime64_any_dtype(df[date_col]):
            if df[date_col].dt.tz is not None:
                # Column has timezone, make end_date timezone-aware
                if end_date.tzinfo is None:
                    import pytz
                    end_date = pytz.UTC.localize(end_date)
            df = df[df[date_col] <= end_date]

        return df

    def collect_all_events(
        self,
        repo_full_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Collect all configured event types for a repository.

        Args:
            repo_full_name: Repository name in format 'owner/repo'
            start_date: Start date for collection
            end_date: End date for collection

        Returns:
            Dictionary with DataFrames for each event type
        """
        events = {}

        # Collect releases
        if self.config.get('events.releases.enabled'):
            releases = self.collect_releases(
                repo_full_name,
                start_date,
                end_date,
                include_prerelease=self.config.get('events.releases.prerelease', False)
            )
            events['releases'] = releases

        # Collect commits
        if self.config.get('events.commits.enabled'):
            commits = self.collect_commits(repo_full_name, start_date, end_date)
            daily_commits = self.aggregate_daily_commits(commits)
            commit_spikes = self.detect_commit_spikes(
                daily_commits,
                threshold=self.config.get('events.commits.spike_threshold', 2.0)
            )
            events['commits'] = commits
            events['daily_commits'] = daily_commits
            events['commit_spikes'] = commit_spikes

        return events
