"""Event study methodology for analyzing abnormal returns."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm

from ..config import get_config
from ..data.stock_collector import StockCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventStudy:
    """Implements event study methodology for analyzing stock price reactions."""

    def __init__(self):
        """Initialize event study analyzer."""
        self.config = get_config()
        self.stock_collector = StockCollector()

    def calculate_market_model_parameters(
        self,
        stock_returns: pd.Series,
        market_returns: pd.Series
    ) -> Tuple[float, float, float]:
        """
        Estimate market model parameters using OLS regression.

        Market Model: R_it = α_i + β_i * R_mt + ε_it

        Args:
            stock_returns: Stock returns during estimation period
            market_returns: Market returns during estimation period

        Returns:
            Tuple of (alpha, beta, residual_std)
        """
        # Align the series and drop NaN
        df = pd.DataFrame({
            'stock': stock_returns,
            'market': market_returns
        }).dropna()

        if len(df) < 30:  # Minimum observations for reliable estimation
            logger.warning(f"Insufficient data for market model: {len(df)} observations")
            return 0.0, 1.0, np.nan

        # OLS regression
        X = sm.add_constant(df['market'])
        y = df['stock']

        try:
            model = sm.OLS(y, X).fit()
            alpha = model.params['const']
            beta = model.params['market']
            residual_std = np.sqrt(model.mse_resid)

            return alpha, beta, residual_std
        except Exception as e:
            logger.error(f"Error in market model estimation: {e}")
            return 0.0, 1.0, np.nan

    def calculate_expected_returns(
        self,
        event_window_data: pd.DataFrame,
        estimation_window_data: pd.DataFrame,
        market_data: pd.DataFrame,
        model: str = 'market'
    ) -> pd.Series:
        """
        Calculate expected returns for event window.

        Args:
            event_window_data: Stock data for event window
            estimation_window_data: Stock data for estimation window
            market_data: Market index data
            model: Model type ('market', 'mean_adjusted', 'market_adjusted')

        Returns:
            Series with expected returns for event window
        """
        if event_window_data.empty:
            return pd.Series()

        # Calculate returns
        stock_returns_event = event_window_data['close'].pct_change()

        if model == 'mean_adjusted':
            # Expected return = mean return during estimation period
            if estimation_window_data.empty:
                expected_return = 0.0
            else:
                est_returns = estimation_window_data['close'].pct_change()
                expected_return = est_returns.mean()

            expected_returns = pd.Series(expected_return, index=stock_returns_event.index)

        elif model == 'market_adjusted':
            # Expected return = market return
            market_returns = market_data['close'].pct_change()
            expected_returns = market_returns.reindex(stock_returns_event.index)

        elif model == 'market':
            # Expected return from market model
            if estimation_window_data.empty:
                # Fallback to market-adjusted
                market_returns = market_data['close'].pct_change()
                expected_returns = market_returns.reindex(stock_returns_event.index)
            else:
                # Estimate market model parameters
                est_returns = estimation_window_data['close'].pct_change()
                est_market_returns = market_data['close'].pct_change()
                est_market_returns = est_market_returns.reindex(estimation_window_data.index)

                alpha, beta, _ = self.calculate_market_model_parameters(
                    est_returns, est_market_returns
                )

                # Calculate expected returns for event window
                event_market_returns = market_data['close'].pct_change()
                event_market_returns = event_market_returns.reindex(event_window_data.index)

                expected_returns = alpha + beta * event_market_returns

        else:
            raise ValueError(f"Unknown model type: {model}")

        return expected_returns

    def calculate_abnormal_returns(
        self,
        ticker: str,
        event_date: datetime,
        pre_days: Optional[int] = None,
        post_days: Optional[int] = None,
        estimation_start: Optional[int] = None,
        estimation_end: Optional[int] = None,
        model: str = 'market'
    ) -> pd.DataFrame:
        """
        Calculate abnormal returns for an event.

        Args:
            ticker: Stock ticker
            event_date: Event date
            pre_days: Days before event (default from config)
            post_days: Days after event (default from config)
            estimation_start: Estimation window start (default from config)
            estimation_end: Estimation window end (default from config)
            model: Expected return model

        Returns:
            DataFrame with abnormal returns
        """
        # Use config defaults if not specified
        if pre_days is None:
            pre_days = self.config.event_window_pre
        if post_days is None:
            post_days = self.config.event_window_post
        if estimation_start is None:
            estimation_start = self.config.estimation_window_start
        if estimation_end is None:
            estimation_end = self.config.estimation_window_end

        # Get stock data for event and estimation windows
        event_window, estimation_window = self.stock_collector.get_event_window_data(
            ticker, event_date, pre_days, post_days, estimation_start, estimation_end
        )

        if event_window.empty:
            logger.warning(f"No event window data for {ticker} on {event_date}")
            return pd.DataFrame()

        # Get market data
        market_start = event_date + pd.Timedelta(days=estimation_start - 10)
        market_end = event_date + pd.Timedelta(days=post_days + 10)
        market_data = self.stock_collector.get_market_data(market_start, market_end)

        if market_data.empty:
            logger.warning("No market data available")
            return pd.DataFrame()

        # Calculate expected returns
        expected_returns = self.calculate_expected_returns(
            event_window, estimation_window, market_data, model
        )

        # Calculate actual and abnormal returns
        actual_returns = event_window['close'].pct_change()

        # Create results DataFrame
        results = pd.DataFrame({
            'date': event_window.index,
            'actual_return': actual_returns.values,
            'expected_return': expected_returns.values,
        })

        results['abnormal_return'] = results['actual_return'] - results['expected_return']

        # Add event time (days relative to event)
        event_trading_day = self.stock_collector.align_event_to_trading_day(
            event_date, event_window.index, 'forward'
        )

        if event_trading_day is not None:
            event_idx = event_window.index.get_loc(event_trading_day)
            results['event_time'] = range(-event_idx, len(results) - event_idx)
        else:
            results['event_time'] = range(len(results))

        # Add metadata
        results['ticker'] = ticker
        results['event_date'] = event_date

        return results

    def calculate_cumulative_abnormal_returns(
        self,
        abnormal_returns: pd.DataFrame,
        start_day: int = 0,
        end_day: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate cumulative abnormal returns (CAR).

        Args:
            abnormal_returns: DataFrame with abnormal returns
            start_day: Start day of CAR window (relative to event)
            end_day: End day of CAR window (if None, uses end of data)

        Returns:
            DataFrame with CAR values
        """
        if abnormal_returns.empty:
            return pd.DataFrame()

        # Filter to CAR window
        mask = abnormal_returns['event_time'] >= start_day
        if end_day is not None:
            mask = mask & (abnormal_returns['event_time'] <= end_day)

        car_data = abnormal_returns[mask].copy()

        # Calculate CAR
        car_data['CAR'] = car_data['abnormal_return'].cumsum()

        return car_data

    def analyze_event(
        self,
        ticker: str,
        event_date: datetime,
        event_type: str,
        event_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Perform complete event study analysis for a single event.

        Args:
            ticker: Stock ticker
            event_date: Event date
            event_type: Type of event (e.g., 'release', 'commit_spike')
            event_metadata: Additional event information

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing event: {ticker} on {event_date} ({event_type})")

        # Calculate abnormal returns
        ar_df = self.calculate_abnormal_returns(
            ticker,
            event_date,
            model=self.config.get('event_study.expected_return_model', 'market')
        )

        if ar_df.empty:
            return {
                'ticker': ticker,
                'event_date': event_date,
                'event_type': event_type,
                'valid': False,
                'reason': 'Insufficient data'
            }

        # Calculate CAR for different windows
        car_results = {}
        for window_name, (start, end) in [
            ('CAR_0_0', (0, 0)),    # Event day only
            ('CAR_0_1', (0, 1)),    # Event day + 1
            ('CAR_-1_1', (-1, 1)),  # 3-day window
            ('CAR_0_5', (0, 5)),    # Post-event week
            ('CAR_-5_5', (-5, 5)),  # Full event window
        ]:
            car_df = self.calculate_cumulative_abnormal_returns(ar_df, start, end)
            if not car_df.empty:
                car_results[window_name] = car_df['CAR'].iloc[-1]

        # Calculate statistics
        mean_ar = ar_df['abnormal_return'].mean()
        std_ar = ar_df['abnormal_return'].std()
        median_ar = ar_df['abnormal_return'].median()

        # Event day AR (day 0)
        event_day_ar = ar_df[ar_df['event_time'] == 0]['abnormal_return']
        ar_day_0 = event_day_ar.iloc[0] if not event_day_ar.empty else np.nan

        return {
            'ticker': ticker,
            'event_date': event_date,
            'event_type': event_type,
            'valid': True,
            'ar_day_0': ar_day_0,
            'mean_ar': mean_ar,
            'median_ar': median_ar,
            'std_ar': std_ar,
            **car_results,
            'metadata': event_metadata or {},
            'num_observations': len(ar_df)
        }

    def analyze_multiple_events(
        self,
        events: pd.DataFrame,
        ticker_col: str = 'ticker',
        date_col: str = 'date',
        type_col: str = 'event_type'
    ) -> pd.DataFrame:
        """
        Analyze multiple events in batch.

        Args:
            events: DataFrame with event information
            ticker_col: Column name for ticker
            date_col: Column name for event date
            type_col: Column name for event type

        Returns:
            DataFrame with analysis results for all events
        """
        results = []

        for idx, row in events.iterrows():
            try:
                result = self.analyze_event(
                    ticker=row[ticker_col],
                    event_date=pd.to_datetime(row[date_col]),
                    event_type=row[type_col],
                    event_metadata=row.to_dict()
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing event {idx}: {e}")
                continue

        return pd.DataFrame(results)

    def aggregate_results(
        self,
        results: pd.DataFrame,
        group_by: str = 'event_type'
    ) -> pd.DataFrame:
        """
        Aggregate event study results.

        Args:
            results: DataFrame with individual event results
            group_by: Column to group by

        Returns:
            DataFrame with aggregated statistics
        """
        if results.empty:
            return pd.DataFrame()

        # Filter valid results
        valid_results = results[results['valid'] == True].copy()

        if valid_results.empty:
            logger.warning("No valid results to aggregate")
            return pd.DataFrame()

        # Aggregate by group
        agg_funcs = {
            'ar_day_0': ['mean', 'median', 'std', 'count'],
            'mean_ar': 'mean',
            'CAR_0_0': ['mean', 'median', 'std'],
            'CAR_0_1': ['mean', 'median', 'std'],
            'CAR_-1_1': ['mean', 'median', 'std'],
            'CAR_0_5': ['mean', 'median', 'std'],
            'CAR_-5_5': ['mean', 'median', 'std'],
        }

        # Only aggregate columns that exist
        agg_funcs = {k: v for k, v in agg_funcs.items() if k in valid_results.columns}

        aggregated = valid_results.groupby(group_by).agg(agg_funcs)

        # Flatten column names
        aggregated.columns = ['_'.join(col).strip('_') for col in aggregated.columns]

        return aggregated.reset_index()
