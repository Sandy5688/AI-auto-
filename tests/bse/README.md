# Create a test runner script run the below command as whole in terminal to initiate testing:

python -c "
import subprocess
import sys

tests = [
    'python -m pytest test_enhanced_bse.py -v',
    'python test_bse_manual.py',
    'python test_bse_performance.py',
    'python test_api_integration.py'
]

print('🧪 Running Complete BSE Test Suite')
print('='*50)

for i, test in enumerate(tests, 1):
    print(f'\n--- Test {i}/{len(tests)} ---')
    result = subprocess.run(test.split(), capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print('STDERR:', result.stderr)

print('\n✅ All tests completed!')
"
