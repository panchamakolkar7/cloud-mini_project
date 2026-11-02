import unittest
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_all_tests():
    print("=" * 65)
    print("        QuotaCloud SaaS Automated Test Suite")
    print("=" * 65)
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(Path(__file__).parent), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 65)
    if result.wasSuccessful():
        print(f" ALL TESTS PASSED! ({result.testsRun} test cases verified successfully)")
        print("=" * 65)
        return 0
    else:
        print(f" TESTS FAILED: Failures: {len(result.failures)}, Errors: {len(result.errors)}")
        print("=" * 65)
        return 1

if __name__ == '__main__':
    sys.exit(run_all_tests())
