#!/bin/bash

# CommitTrader Test Run
# Quick test to verify installation and basic functionality

echo "========================================"
echo "CommitTrader - Test Run"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q
echo "✓ Dependencies installed"
echo ""

# Run a quick test analysis
echo "Running test analysis (5 events from Microsoft)..."
echo "This should take 1-2 minutes..."
echo ""

python main.py \
  --mode full \
  --tickers MSFT \
  --max-events 5 \
  --start-date 2023-01-01 \
  --end-date 2023-12-31

echo ""
echo "========================================"
echo "Test Complete!"
echo "========================================"
echo ""
echo "Results saved to: data/processed/snapshots/"
echo ""
echo "Next steps:"
echo "1. Check the summary output above"
echo "2. Review results in data/processed/snapshots/"
echo "3. Try: python main.py --mode full --tickers MSFT GOOGL --max-events 20"
echo "4. Read QUICKSTART.md for more examples"
echo ""
