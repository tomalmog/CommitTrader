# CommitTrader

CommitTrader is a quantitative research project analyzing whether public GitHub activity from open-source repositories associated with publicly traded companies has any measurable relationship with short-term stock price movements.

## Overview

CommitTrader examines how different forms of GitHub activity align with abnormal stock returns around the event date. The project uses event-study methodology to evaluate whether developer-driven signals contain informational value that public markets may respond to.

## Research Focus

CommitTrader investigates:

- **Whether open-source releases correspond with observable stock price reactions**
- **Whether commit spikes or elevated development activity correlate with abnormal returns**
- **Which GitHub event categories show statistically significant effects**
- **How effects vary by company size, sector, or repository relevance**
- **Which event windows (e.g., −1 to +1, −5 to +5) exhibit the strongest signals**

## Methodology

CommitTrader uses a structured event-study framework consisting of:

### **Event Identification**
- Collection of GitHub releases  
- Detection of commit frequency spikes  
- Categorization of repository activity events  

### **Expected Return Models**
- **Market Model**  
- **Mean-Adjusted Model**  
- **Market-Adjusted Model**

### **Abnormal Return (AR) Calculation**
- AR computed as the difference between observed returns and expected returns

### **Cumulative Abnormal Returns (CAR)**
- CAR aggregated over configurable windows such as:
  - **Short windows:** (−1, 0, +1)  
  - **Medium windows:** (−3 to +3)  
  - **Extended windows:** (−5 to +5)

### **Statistical Testing**
- **t-tests**  
- **Sign tests**  
- **Wilcoxon signed-rank tests**  
- **Cross-sectional tests**  
- **ANOVA** for comparing event types  

### **Aggregation and Interpretation**
- Company-level and sector-level comparisons  
- Event-type-specific summaries  
- Identification of consistent patterns or null results

## Data Sources

- **GitHub Activity Data**  
  Public events (releases, commits, spikes) collected from mapped repositories.

- **Market Data**  
  Daily stock prices and index returns used for modeling expected returns.

- **Company–Repository Mapping**  
  A maintained CSV linking tickers to relevant open-source repositories.

## Outputs

CommitTrader produces:

- **Event-level AR and CAR results**
- **Aggregated statistical summaries for each event category**
- **Cross-company and cross-sector comparisons**
- **Significance test outcomes**
- **Visualizations**, including:
  - AR and CAR distributions  
  - Timeline charts  
  - Event-type comparisons  

These outputs support evaluating whether open-source development patterns show measurable alignment with stock market behavior.

## Scope and Limitations
- Public GitHub repositories reflect only part of a company's engineering activity.
- Effects may vary by time period, company, or sector.
- Results should not be interpreted as trading signals.
- The project is intended strictly for research and analysis.

## Purpose

CommitTrader provides a framework for studying how open-source software ecosystems interact with financial markets. It enables structured, empirical evaluation of whether developer activity produces market-relevant signals and offers a foundation for further academic research in quantitative finance, software engineering analytics, and market microstructure.
