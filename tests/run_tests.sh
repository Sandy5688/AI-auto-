#!/bin/bash

echo "🧪 Running all tests..."

echo "📊 Running BSE tests..."
python -m pytest tests/test_bse.py -v

echo "🔐 Running AGK tests..."
python -m pytest tests/test_agk.py -v

echo "🔑 Running token handling tests..."
python -m pytest tests/test_token_handling.py -v

echo "✅ All tests completed!"
