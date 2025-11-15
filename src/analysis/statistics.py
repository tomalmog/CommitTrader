"""Statistical testing for event study results."""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
from scipy import stats

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StatisticalTests:
    """Statistical significance testing for event studies."""

    def __init__(self):
        """Initialize statistical test framework."""
        self.config = get_config()
        self.significance_levels = self.config.get(
            'event_study.significance_levels',
            [0.01, 0.05, 0.10]
        )

    def t_test_abnormal_return(
        self,
        abnormal_returns: pd.Series,
        null_hypothesis: float = 0.0
    ) -> Dict:
        """
        Perform t-test on abnormal returns.

        H0: Mean abnormal return = null_hypothesis (typically 0)
        H1: Mean abnormal return ≠ null_hypothesis

        Args:
            abnormal_returns: Series of abnormal returns
            null_hypothesis: Null hypothesis value

        Returns:
            Dictionary with test results
        """
        # Remove NaN values
        ar = abnormal_returns.dropna()

        if len(ar) == 0:
            return {
                'test': 't-test',
                'valid': False,
                'reason': 'No valid observations'
            }

        # Calculate t-statistic
        mean_ar = ar.mean()
        std_ar = ar.std()
        n = len(ar)

        if std_ar == 0 or n < 2:
            return {
                'test': 't-test',
                'valid': False,
                'reason': 'Insufficient variance or observations'
            }

        t_stat = (mean_ar - null_hypothesis) / (std_ar / np.sqrt(n))
        df = n - 1

        # Two-tailed p-value
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))

        # Determine significance
        significance = self._get_significance_level(p_value)

        return {
            'test': 't-test',
            'valid': True,
            'mean': mean_ar,
            'std': std_ar,
            'n': n,
            't_statistic': t_stat,
            'degrees_of_freedom': df,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'significance_level': significance,
        }

    def sign_test(
        self,
        abnormal_returns: pd.Series
    ) -> Dict:
        """
        Perform sign test (non-parametric).

        H0: Median abnormal return = 0
        H1: Median abnormal return ≠ 0

        Args:
            abnormal_returns: Series of abnormal returns

        Returns:
            Dictionary with test results
        """
        ar = abnormal_returns.dropna()

        if len(ar) == 0:
            return {
                'test': 'sign-test',
                'valid': False,
                'reason': 'No valid observations'
            }

        # Count positive and negative returns
        n_positive = (ar > 0).sum()
        n_negative = (ar < 0).sum()
        n_total = n_positive + n_negative

        if n_total == 0:
            return {
                'test': 'sign-test',
                'valid': False,
                'reason': 'All returns are zero'
            }

        # Under H0, probability of positive return is 0.5
        # Use binomial test
        p_value = 2 * min(
            stats.binom.cdf(n_positive, n_total, 0.5),
            1 - stats.binom.cdf(n_positive - 1, n_total, 0.5)
        )

        significance = self._get_significance_level(p_value)

        return {
            'test': 'sign-test',
            'valid': True,
            'n_positive': n_positive,
            'n_negative': n_negative,
            'n_total': n_total,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'significance_level': significance,
        }

    def wilcoxon_signed_rank_test(
        self,
        abnormal_returns: pd.Series
    ) -> Dict:
        """
        Perform Wilcoxon signed-rank test (non-parametric).

        H0: Median abnormal return = 0
        H1: Median abnormal return ≠ 0

        Args:
            abnormal_returns: Series of abnormal returns

        Returns:
            Dictionary with test results
        """
        ar = abnormal_returns.dropna()

        if len(ar) < 3:
            return {
                'test': 'wilcoxon',
                'valid': False,
                'reason': 'Insufficient observations (need at least 3)'
            }

        try:
            # Perform Wilcoxon signed-rank test
            statistic, p_value = stats.wilcoxon(ar, alternative='two-sided')

            significance = self._get_significance_level(p_value)

            return {
                'test': 'wilcoxon',
                'valid': True,
                'statistic': statistic,
                'p_value': p_value,
                'median': ar.median(),
                'n': len(ar),
                'significant': p_value < 0.05,
                'significance_level': significance,
            }
        except Exception as e:
            return {
                'test': 'wilcoxon',
                'valid': False,
                'reason': str(e)
            }

    def cross_sectional_test(
        self,
        event_results: pd.DataFrame,
        ar_column: str = 'ar_day_0'
    ) -> Dict:
        """
        Perform cross-sectional t-test across multiple events.

        Args:
            event_results: DataFrame with event study results
            ar_column: Column name for abnormal returns to test

        Returns:
            Dictionary with test results
        """
        if event_results.empty or ar_column not in event_results.columns:
            return {
                'test': 'cross-sectional',
                'valid': False,
                'reason': 'No data or column not found'
            }

        # Filter valid events
        valid_events = event_results[event_results['valid'] == True].copy()

        if len(valid_events) < 2:
            return {
                'test': 'cross-sectional',
                'valid': False,
                'reason': 'Insufficient valid events'
            }

        # Perform t-test on cross-section of ARs
        return self.t_test_abnormal_return(valid_events[ar_column])

    def car_significance_test(
        self,
        cumulative_abnormal_returns: pd.Series,
        variance_estimates: Optional[pd.Series] = None
    ) -> Dict:
        """
        Test significance of cumulative abnormal returns (CAR).

        Args:
            cumulative_abnormal_returns: CAR values across events
            variance_estimates: Optional variance estimates for each CAR

        Returns:
            Dictionary with test results
        """
        cars = cumulative_abnormal_returns.dropna()

        if len(cars) == 0:
            return {
                'test': 'CAR-test',
                'valid': False,
                'reason': 'No valid CAR values'
            }

        # Simple t-test on CARs
        if variance_estimates is None:
            return self.t_test_abnormal_return(cars)

        # Weighted t-test if variances provided
        var_est = variance_estimates.dropna()

        # Align CAR and variance
        aligned = pd.DataFrame({
            'car': cars,
            'var': var_est
        }).dropna()

        if len(aligned) < 2:
            return {
                'test': 'CAR-test',
                'valid': False,
                'reason': 'Insufficient observations with variance estimates'
            }

        # Weighted mean CAR
        weights = 1 / aligned['var']
        weighted_mean_car = (aligned['car'] * weights).sum() / weights.sum()

        # Variance of weighted mean
        var_weighted_mean = 1 / weights.sum()
        std_weighted_mean = np.sqrt(var_weighted_mean)

        # t-statistic
        t_stat = weighted_mean_car / std_weighted_mean
        df = len(aligned) - 1
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))

        significance = self._get_significance_level(p_value)

        return {
            'test': 'CAR-test (weighted)',
            'valid': True,
            'mean_car': weighted_mean_car,
            'std_car': std_weighted_mean,
            'n': len(aligned),
            't_statistic': t_stat,
            'degrees_of_freedom': df,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'significance_level': significance,
        }

    def compare_event_types(
        self,
        event_results: pd.DataFrame,
        type_column: str = 'event_type',
        ar_column: str = 'ar_day_0'
    ) -> Dict:
        """
        Compare abnormal returns across different event types.

        Performs ANOVA to test if mean AR differs across event types.

        Args:
            event_results: DataFrame with event study results
            type_column: Column name for event type
            ar_column: Column name for abnormal returns

        Returns:
            Dictionary with comparison results
        """
        # Filter valid events
        valid_events = event_results[event_results['valid'] == True].copy()

        if valid_events.empty:
            return {
                'test': 'ANOVA',
                'valid': False,
                'reason': 'No valid events'
            }

        # Get event types
        event_types = valid_events[type_column].unique()

        if len(event_types) < 2:
            return {
                'test': 'ANOVA',
                'valid': False,
                'reason': 'Need at least 2 event types'
            }

        # Prepare groups
        groups = [
            valid_events[valid_events[type_column] == et][ar_column].dropna()
            for et in event_types
        ]

        # Filter out empty groups
        groups = [g for g in groups if len(g) > 0]

        if len(groups) < 2:
            return {
                'test': 'ANOVA',
                'valid': False,
                'reason': 'Insufficient data in groups'
            }

        # Perform one-way ANOVA
        try:
            f_stat, p_value = stats.f_oneway(*groups)

            # Calculate means for each group
            group_means = {
                et: valid_events[valid_events[type_column] == et][ar_column].mean()
                for et in event_types
            }

            significance = self._get_significance_level(p_value)

            return {
                'test': 'ANOVA',
                'valid': True,
                'f_statistic': f_stat,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'significance_level': significance,
                'num_groups': len(groups),
                'group_means': group_means,
            }
        except Exception as e:
            return {
                'test': 'ANOVA',
                'valid': False,
                'reason': str(e)
            }

    def perform_all_tests(
        self,
        event_results: pd.DataFrame,
        ar_column: str = 'ar_day_0'
    ) -> Dict[str, Dict]:
        """
        Perform comprehensive statistical testing.

        Args:
            event_results: DataFrame with event study results
            ar_column: Column name for abnormal returns to test

        Returns:
            Dictionary with all test results
        """
        # Filter valid events
        valid_events = event_results[event_results['valid'] == True].copy()

        if valid_events.empty:
            logger.warning("No valid events for statistical testing")
            return {}

        ar_values = valid_events[ar_column].dropna()

        results = {}

        # Parametric tests
        results['t_test'] = self.t_test_abnormal_return(ar_values)

        # Non-parametric tests
        results['sign_test'] = self.sign_test(ar_values)
        results['wilcoxon_test'] = self.wilcoxon_signed_rank_test(ar_values)

        # Cross-sectional test
        results['cross_sectional'] = self.cross_sectional_test(event_results, ar_column)

        # Compare event types if available
        if 'event_type' in event_results.columns:
            results['anova'] = self.compare_event_types(event_results, 'event_type', ar_column)

        # Test different CAR windows
        for car_col in ['CAR_0_0', 'CAR_0_1', 'CAR_-1_1', 'CAR_0_5', 'CAR_-5_5']:
            if car_col in valid_events.columns:
                car_values = valid_events[car_col].dropna()
                if len(car_values) > 0:
                    results[f'{car_col}_test'] = self.t_test_abnormal_return(car_values)

        return results

    def _get_significance_level(self, p_value: float) -> str:
        """
        Get significance level label based on p-value.

        Args:
            p_value: P-value from statistical test

        Returns:
            Significance level string (e.g., '***', '**', '*', 'ns')
        """
        if p_value < 0.01:
            return '***'  # Highly significant
        elif p_value < 0.05:
            return '**'   # Significant
        elif p_value < 0.10:
            return '*'    # Marginally significant
        else:
            return 'ns'   # Not significant

    def create_summary_table(
        self,
        test_results: Dict[str, Dict]
    ) -> pd.DataFrame:
        """
        Create summary table of statistical test results.

        Args:
            test_results: Dictionary with test results

        Returns:
            DataFrame with formatted summary
        """
        rows = []

        for test_name, result in test_results.items():
            if not result.get('valid', False):
                continue

            row = {
                'Test': test_name,
                'Statistic': result.get('t_statistic') or result.get('f_statistic') or result.get('statistic', np.nan),
                'P-Value': result.get('p_value', np.nan),
                'Significant': result.get('significance_level', 'ns'),
                'N': result.get('n', np.nan),
            }

            # Add test-specific info
            if 'mean' in result:
                row['Mean AR'] = result['mean']
            if 'mean_car' in result:
                row['Mean CAR'] = result['mean_car']

            rows.append(row)

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)
