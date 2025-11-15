"""Stock price data collection and processing."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import json

import pandas as pd
import numpy as np
import yfinance as yf
from tqdm import tqdm

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockCollector:
    """Collects and processes stock price data."""

    def __init__(self):
        """Initialize stock collector."""
        self.config = get_config()
        self.cache_dir = self.config.raw_data_dir / "stocks"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_stock_data(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get stock price data for a ticker.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data collection
            end_date: End date for data collection
            use_cache: Whether to use cached data

        Returns:
            DataFrame with OHLCV data and adjusted close
        """
        # Set default dates
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365 * 3)
        if end_date is None:
            end_date = datetime.now()

        # Check cache
        cache_file = self.cache_dir / f"{ticker}.csv"
        if use_cache and cache_file.exists():
            logger.info(f"Loading {ticker} from cache")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)

            # Check if cached data covers requested range
            if df.index.min() <= pd.Timestamp(start_date) and df.index.max() >= pd.Timestamp(end_date):
                return df.loc[start_date:end_date]
            else:
                logger.info(f"Cached data for {ticker} doesn't cover full range, fetching new data")

        # Fetch from yfinance
        logger.info(f"Fetching stock data for {ticker}")
        try:
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start=start_date, end=end_date, auto_adjust=False)

            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # Rename columns to lowercase
            df.columns = df.columns.str.lower()

            # Cache the data
            if use_cache:
                df.to_csv(cache_file)
                logger.info(f"Cached {ticker} data to {cache_file}")

            return df

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    def get_market_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get market index data (e.g., S&P 500).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with market index data
        """
        market_ticker = self.config.market_index
        return self.get_stock_data(market_ticker, start_date, end_date)

    def calculate_returns(
        self,
        price_data: pd.DataFrame,
        price_column: str = 'close'
    ) -> pd.Series:
        """
        Calculate daily returns from price data.

        Args:
            price_data: DataFrame with price data
            price_column: Column name for price

        Returns:
            Series with daily returns
        """
        if price_data.empty:
            return pd.Series()

        returns = price_data[price_column].pct_change()
        return returns

    def get_trading_days(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DatetimeIndex:
        """
        Get trading days between two dates using market data.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DatetimeIndex with trading days
        """
        market_data = self.get_market_data(start_date, end_date)
        return market_data.index

    def align_event_to_trading_day(
        self,
        event_date: datetime,
        trading_days: pd.DatetimeIndex,
        direction: str = 'forward'
    ) -> Optional[datetime]:
        """
        Align an event date to the nearest trading day.

        Args:
            event_date: Event date to align
            trading_days: Index of trading days
            direction: 'forward' to find next trading day, 'backward' for previous

        Returns:
            Aligned trading day or None if not found
        """
        event_date = pd.Timestamp(event_date).normalize()

        if event_date in trading_days:
            return event_date

        if direction == 'forward':
            future_days = trading_days[trading_days > event_date]
            if len(future_days) > 0:
                return future_days[0]
        else:  # backward
            past_days = trading_days[trading_days < event_date]
            if len(past_days) > 0:
                return past_days[-1]

        return None

    def get_event_window_data(
        self,
        ticker: str,
        event_date: datetime,
        pre_days: int = 5,
        post_days: int = 5,
        estimation_start: int = -130,
        estimation_end: int = -31
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get stock data for event window and estimation period.

        Args:
            ticker: Stock ticker
            event_date: Event date
            pre_days: Days before event in event window
            post_days: Days after event in event window
            estimation_start: Start of estimation window (days before event)
            estimation_end: End of estimation window (days before event)

        Returns:
            Tuple of (event_window_data, estimation_window_data)
        """
        # Calculate date ranges (add buffer for trading days)
        buffer_days = 50
        data_start = event_date + timedelta(days=estimation_start - buffer_days)
        data_end = event_date + timedelta(days=post_days + buffer_days)

        # Fetch stock data
        stock_data = self.get_stock_data(ticker, data_start, data_end)

        if stock_data.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Get trading days
        trading_days = stock_data.index

        # Align event date to trading day
        event_trading_day = self.align_event_to_trading_day(event_date, trading_days, 'forward')

        if event_trading_day is None:
            logger.warning(f"Could not align event date {event_date} to trading day")
            return pd.DataFrame(), pd.DataFrame()

        # Find event index
        try:
            event_idx = trading_days.get_loc(event_trading_day)
        except KeyError:
            logger.warning(f"Event date {event_trading_day} not found in trading days")
            return pd.DataFrame(), pd.DataFrame()

        # Extract event window
        event_start_idx = max(0, event_idx - pre_days)
        event_end_idx = min(len(trading_days) - 1, event_idx + post_days)
        event_window = stock_data.iloc[event_start_idx:event_end_idx + 1]

        # Extract estimation window
        est_start_idx = max(0, event_idx + estimation_start)
        est_end_idx = max(0, event_idx + estimation_end)

        if est_end_idx > est_start_idx:
            estimation_window = stock_data.iloc[est_start_idx:est_end_idx + 1]
        else:
            estimation_window = pd.DataFrame()

        return event_window, estimation_window

    def get_multiple_tickers(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        price_column: str = 'close'
    ) -> pd.DataFrame:
        """
        Get price data for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            price_column: Which price column to extract

        Returns:
            DataFrame with tickers as columns and dates as index
        """
        all_data = {}

        for ticker in tqdm(tickers, desc="Fetching stock data"):
            data = self.get_stock_data(ticker, start_date, end_date)
            if not data.empty and price_column in data.columns:
                all_data[ticker] = data[price_column]

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        return df

    def validate_data_quality(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        min_trading_days: int = 100
    ) -> Dict[str, any]:
        """
        Validate stock data quality for analysis.

        Args:
            ticker: Stock ticker
            start_date: Start date
            end_date: End date
            min_trading_days: Minimum required trading days

        Returns:
            Dictionary with validation results
        """
        data = self.get_stock_data(ticker, start_date, end_date)

        if data.empty:
            return {
                'valid': False,
                'reason': 'No data available',
                'trading_days': 0,
                'missing_days': 0,
                'extreme_returns': 0
            }

        # Calculate metrics
        returns = self.calculate_returns(data, 'close')
        trading_days = len(data)

        # Check for missing data (compare to market trading days)
        market_data = self.get_market_data(start_date, end_date)
        expected_days = len(market_data)
        missing_days = expected_days - trading_days

        # Check for extreme returns (potential data errors)
        extreme_returns = (returns.abs() > 0.5).sum()  # >50% daily return

        # Validation
        valid = (
            trading_days >= min_trading_days and
            missing_days < 0.1 * expected_days and  # Less than 10% missing
            extreme_returns < 5  # Less than 5 extreme returns
        )

        return {
            'valid': valid,
            'trading_days': trading_days,
            'expected_days': expected_days,
            'missing_days': missing_days,
            'extreme_returns': extreme_returns,
            'reason': 'Valid' if valid else 'Insufficient or poor quality data'
        }

    def get_company_info(self, ticker: str) -> Dict[str, any]:
        """
        Get company information for a ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Dictionary with company information
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            return {
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'country': info.get('country', 'Unknown'),
            }
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return {
                'ticker': ticker,
                'name': ticker,
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': 0,
                'country': 'Unknown',
            }
