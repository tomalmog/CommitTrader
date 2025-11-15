"""Visualization tools for analysis results."""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats as scipy_stats

from ..config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultsVisualizer:
    """Creates visualizations for event study results."""

    def __init__(self):
        """Initialize visualizer."""
        self.config = get_config()

        # Set style
        plt.style.use(self.config.get('visualization.style', 'seaborn-v0_8-darkgrid'))
        self.figsize = tuple(self.config.get('visualization.figure_size', [12, 8]))
        self.dpi = self.config.get('visualization.dpi', 300)

        # Color palette
        self.colors = sns.color_palette("Set2")

    def plot_car_distribution(
        self,
        results: pd.DataFrame,
        car_column: str = 'CAR_-5_5',
        by_event_type: bool = True
    ) -> plt.Figure:
        """
        Plot distribution of cumulative abnormal returns.

        Args:
            results: DataFrame with event study results
            car_column: CAR column to plot
            by_event_type: Whether to separate by event type

        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(1, 2, figsize=self.figsize)

        valid_results = results[results['valid'] == True].copy()

        if valid_results.empty or car_column not in valid_results.columns:
            logger.warning(f"No valid data for {car_column}")
            return fig

        # Histogram
        if by_event_type and 'event_type' in valid_results.columns:
            for event_type in valid_results['event_type'].unique():
                data = valid_results[valid_results['event_type'] == event_type][car_column].dropna()
                axes[0].hist(data, alpha=0.6, label=event_type, bins=30)
            axes[0].legend()
        else:
            axes[0].hist(valid_results[car_column].dropna(), bins=30, alpha=0.7, color=self.colors[0])

        axes[0].axvline(x=0, color='red', linestyle='--', linewidth=2, label='Zero CAR')
        axes[0].set_xlabel(f'{car_column} (%)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title(f'Distribution of {car_column}')

        # Box plot
        if by_event_type and 'event_type' in valid_results.columns:
            event_types = valid_results['event_type'].unique()
            data_by_type = [
                valid_results[valid_results['event_type'] == et][car_column].dropna()
                for et in event_types
            ]
            axes[1].boxplot(data_by_type, labels=event_types, patch_artist=True)
        else:
            axes[1].boxplot([valid_results[car_column].dropna()], labels=['All Events'], patch_artist=True)

        axes[1].axhline(y=0, color='red', linestyle='--', linewidth=2)
        axes[1].set_ylabel(f'{car_column} (%)')
        axes[1].set_title(f'{car_column} by Event Type')
        axes[1].tick_params(axis='x', rotation=45)

        plt.tight_layout()
        return fig

    def plot_average_car_over_time(
        self,
        results: pd.DataFrame,
        by_event_type: bool = True
    ) -> plt.Figure:
        """
        Plot average CAR over event time window.

        Args:
            results: DataFrame with event study results
            by_event_type: Whether to separate by event type

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        valid_results = results[results['valid'] == True].copy()

        if valid_results.empty:
            return fig

        # Extract CAR columns
        car_columns = [col for col in valid_results.columns if col.startswith('CAR_')]

        if not car_columns:
            logger.warning("No CAR columns found")
            return fig

        # Parse window information
        car_data = []
        for col in car_columns:
            # Parse window (e.g., CAR_-5_5 -> (-5, 5))
            try:
                parts = col.replace('CAR_', '').split('_')
                if len(parts) == 2:
                    end_day = int(parts[1])
                    mean_car = valid_results[col].mean()
                    car_data.append({'day': end_day, 'mean_car': mean_car})
            except:
                continue

        if not car_data:
            return fig

        car_df = pd.DataFrame(car_data).sort_values('day')

        ax.plot(car_df['day'], car_df['mean_car'] * 100, marker='o', linewidth=2, markersize=8)
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1)
        ax.axvline(x=0, color='gray', linestyle=':', linewidth=1, label='Event Day')

        ax.set_xlabel('Days Relative to Event')
        ax.set_ylabel('Average CAR (%)')
        ax.set_title('Average Cumulative Abnormal Returns Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_ar_by_event_type(
        self,
        results: pd.DataFrame,
        ar_column: str = 'ar_day_0'
    ) -> plt.Figure:
        """
        Plot abnormal returns by event type.

        Args:
            results: DataFrame with event study results
            ar_column: AR column to plot

        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(1, 2, figsize=self.figsize)

        valid_results = results[results['valid'] == True].copy()

        if valid_results.empty or 'event_type' not in valid_results.columns:
            return fig

        # Calculate means by event type
        means = valid_results.groupby('event_type')[ar_column].agg(['mean', 'sem']).reset_index()
        means['mean'] *= 100  # Convert to percentage
        means['sem'] *= 100

        # Bar plot with error bars
        x_pos = range(len(means))
        axes[0].bar(x_pos, means['mean'], yerr=means['sem'], capsize=5, alpha=0.7, color=self.colors)
        axes[0].set_xticks(x_pos)
        axes[0].set_xticklabels(means['event_type'], rotation=45, ha='right')
        axes[0].axhline(y=0, color='red', linestyle='--', linewidth=1)
        axes[0].set_ylabel('Mean AR (%)')
        axes[0].set_title(f'Mean {ar_column} by Event Type')
        axes[0].grid(True, alpha=0.3, axis='y')

        # Violin plot
        event_types = valid_results['event_type'].unique()
        data_by_type = [
            valid_results[valid_results['event_type'] == et][ar_column].dropna() * 100
            for et in event_types
        ]

        parts = axes[1].violinplot(data_by_type, positions=range(len(event_types)), showmeans=True)
        axes[1].set_xticks(range(len(event_types)))
        axes[1].set_xticklabels(event_types, rotation=45, ha='right')
        axes[1].axhline(y=0, color='red', linestyle='--', linewidth=1)
        axes[1].set_ylabel('AR (%)')
        axes[1].set_title(f'Distribution of {ar_column} by Event Type')

        plt.tight_layout()
        return fig

    def plot_statistical_significance(
        self,
        statistical_tests: Dict
    ) -> plt.Figure:
        """
        Visualize statistical test results.

        Args:
            statistical_tests: Dictionary with test results

        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Extract p-values
        test_names = []
        p_values = []

        for test_name, result in statistical_tests.items():
            if result.get('valid', False) and 'p_value' in result:
                test_names.append(test_name)
                p_values.append(result['p_value'])

        if not test_names:
            logger.warning("No valid test results to plot")
            return fig

        # Plot p-values
        y_pos = range(len(test_names))
        colors_list = ['green' if p < 0.05 else 'orange' if p < 0.10 else 'red' for p in p_values]

        ax.barh(y_pos, p_values, color=colors_list, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(test_names)
        ax.set_xlabel('P-Value')
        ax.set_title('Statistical Test Results')

        # Add significance lines
        ax.axvline(x=0.01, color='green', linestyle='--', linewidth=1, label='p=0.01')
        ax.axvline(x=0.05, color='orange', linestyle='--', linewidth=1, label='p=0.05')
        ax.axvline(x=0.10, color='red', linestyle='--', linewidth=1, label='p=0.10')

        ax.legend()
        ax.set_xlim(0, max(0.15, max(p_values) * 1.1))

        plt.tight_layout()
        return fig

    def plot_event_timeline(
        self,
        events: pd.DataFrame,
        results: pd.DataFrame
    ) -> plt.Figure:
        """
        Plot timeline of events and their abnormal returns.

        Args:
            events: DataFrame with event data
            results: DataFrame with event study results

        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Merge events with results
        merged = events.merge(
            results[['ticker', 'event_date', 'ar_day_0', 'CAR_-5_5']],
            left_on=['ticker', 'date'],
            right_on=['ticker', 'event_date'],
            how='inner'
        )

        if merged.empty:
            return fig

        # Plot 1: Event counts over time
        event_counts = merged.groupby([pd.Grouper(key='date', freq='M'), 'event_type']).size().unstack(fill_value=0)

        event_counts.plot(kind='bar', stacked=True, ax=axes[0], alpha=0.7)
        axes[0].set_ylabel('Number of Events')
        axes[0].set_title('Event Frequency Over Time')
        axes[0].legend(title='Event Type')
        axes[0].tick_params(axis='x', rotation=45)

        # Plot 2: Average AR over time
        ar_by_month = merged.groupby(pd.Grouper(key='date', freq='M'))['ar_day_0'].mean() * 100

        axes[1].plot(ar_by_month.index, ar_by_month.values, marker='o', linewidth=2)
        axes[1].axhline(y=0, color='red', linestyle='--', linewidth=1)
        axes[1].set_xlabel('Date')
        axes[1].set_ylabel('Average AR Day 0 (%)')
        axes[1].set_title('Average Abnormal Returns Over Time')
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_top_events(
        self,
        results: pd.DataFrame,
        n: int = 20,
        metric: str = 'CAR_-5_5'
    ) -> plt.Figure:
        """
        Plot top events by abnormal returns.

        Args:
            results: DataFrame with event study results
            n: Number of top events to show
            metric: Metric to rank by

        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 8))

        valid_results = results[results['valid'] == True].copy()

        if valid_results.empty or metric not in valid_results.columns:
            return fig

        # Top positive
        top_positive = valid_results.nlargest(n, metric)
        top_positive['label'] = top_positive['ticker'] + '\n' + top_positive['event_date'].astype(str).str[:10]

        axes[0].barh(range(len(top_positive)), top_positive[metric] * 100, color='green', alpha=0.7)
        axes[0].set_yticks(range(len(top_positive)))
        axes[0].set_yticklabels(top_positive['label'], fontsize=8)
        axes[0].set_xlabel(f'{metric} (%)')
        axes[0].set_title(f'Top {n} Events (Positive {metric})')
        axes[0].invert_yaxis()

        # Top negative
        top_negative = valid_results.nsmallest(n, metric)
        top_negative['label'] = top_negative['ticker'] + '\n' + top_negative['event_date'].astype(str).str[:10]

        axes[1].barh(range(len(top_negative)), top_negative[metric] * 100, color='red', alpha=0.7)
        axes[1].set_yticks(range(len(top_negative)))
        axes[1].set_yticklabels(top_negative['label'], fontsize=8)
        axes[1].set_xlabel(f'{metric} (%)')
        axes[1].set_title(f'Top {n} Events (Negative {metric})')
        axes[1].invert_yaxis()

        plt.tight_layout()
        return fig

    def create_summary_dashboard(
        self,
        events: pd.DataFrame,
        results: pd.DataFrame,
        aggregated: pd.DataFrame,
        statistical_tests: Dict
    ) -> plt.Figure:
        """
        Create comprehensive summary dashboard.

        Args:
            events: Event data
            results: Event study results
            aggregated: Aggregated results
            statistical_tests: Statistical test results

        Returns:
            Matplotlib figure
        """
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        valid_results = results[results['valid'] == True].copy()

        # 1. Overall CAR distribution
        ax1 = fig.add_subplot(gs[0, :2])
        if 'CAR_-5_5' in valid_results.columns:
            ax1.hist(valid_results['CAR_-5_5'] * 100, bins=50, alpha=0.7, color=self.colors[0])
            ax1.axvline(x=0, color='red', linestyle='--', linewidth=2)
            ax1.set_xlabel('CAR (-5, 5) (%)')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Distribution of Cumulative Abnormal Returns')

        # 2. Key statistics
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.axis('off')
        stats_text = f"""
        Key Statistics:

        Total Events: {len(events):,}
        Valid Studies: {len(valid_results):,}
        Companies: {events['ticker'].nunique()}

        Mean AR (Day 0): {valid_results['ar_day_0'].mean()*100:.3f}%
        Median AR (Day 0): {valid_results['ar_day_0'].median()*100:.3f}%

        Mean CAR (-5,5): {valid_results['CAR_-5_5'].mean()*100:.3f}%
        % Positive: {(valid_results['ar_day_0']>0).mean()*100:.1f}%
        """
        ax2.text(0.1, 0.9, stats_text, transform=ax2.transAxes,
                fontsize=10, verticalalignment='top', family='monospace')

        # 3. AR by event type
        ax3 = fig.add_subplot(gs[1, :2])
        if 'event_type' in valid_results.columns:
            means = valid_results.groupby('event_type')['ar_day_0'].mean() * 100
            means.plot(kind='bar', ax=ax3, color=self.colors, alpha=0.7)
            ax3.axhline(y=0, color='red', linestyle='--', linewidth=1)
            ax3.set_ylabel('Mean AR Day 0 (%)')
            ax3.set_title('Average Abnormal Returns by Event Type')
            ax3.tick_params(axis='x', rotation=45)

        # 4. Statistical significance
        ax4 = fig.add_subplot(gs[1, 2])
        sig_count = sum(1 for t in statistical_tests.values()
                       if t.get('valid') and t.get('significant'))
        total_tests = sum(1 for t in statistical_tests.values() if t.get('valid'))

        if total_tests > 0:
            labels = ['Significant', 'Not Significant']
            sizes = [sig_count, total_tests - sig_count]
            colors_pie = ['green', 'red']
            ax4.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
            ax4.set_title(f'Statistical Significance\n({total_tests} tests)')

        # 5. Event timeline
        ax5 = fig.add_subplot(gs[2, :])
        if 'date' in events.columns:
            event_counts = events.groupby(pd.Grouper(key='date', freq='M')).size()
            ax5.plot(event_counts.index, event_counts.values, marker='o', linewidth=2)
            ax5.set_xlabel('Date')
            ax5.set_ylabel('Number of Events')
            ax5.set_title('Event Frequency Over Time')
            ax5.tick_params(axis='x', rotation=45)
            ax5.grid(True, alpha=0.3)

        plt.suptitle('CommitTrader Analysis Dashboard', fontsize=16, fontweight='bold', y=0.995)

        return fig
