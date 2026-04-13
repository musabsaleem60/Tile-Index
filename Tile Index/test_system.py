"""
Test script to verify all system components work correctly
"""

import sys
import traceback

def test_database():
    """Test database initialization"""
    print("Testing database initialization...")
    try:
        from database.init_db import init_database
        db_path = init_database()
        print(f"✓ Database initialized: {db_path}")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        traceback.print_exc()
        return False

def test_auth():
    """Test authentication service"""
    print("\nTesting authentication service...")
    try:
        from services.auth_service import AuthenticationService
        from repositories.user_repository import UserRepository
        
        # Check default admin
        user = UserRepository.get_by_username('musab')
        if user:
            print(f"✓ Default admin user found: {user.username}")
            # Test login
            try:
                logged_user = AuthenticationService.login('musab', 'musab123')
                print(f"✓ Login successful: {logged_user.username} ({logged_user.role})")
            except Exception as e:
                print(f"✗ Login failed: {e}")
                return False
        else:
            print("✗ Default admin user not found")
            return False
        return True
    except Exception as e:
        print(f"✗ Authentication error: {e}")
        traceback.print_exc()
        return False

def test_imports():
    """Test all module imports"""
    print("\nTesting module imports...")
    modules = [
        'ui.login_window',
        'ui.main_window',
        'ui.inventory_window',
        'ui.invoice_window',
        'ui.user_management_window',
        'ui.report_window',
        'ui.invoice_search_window',
        'services.inventory_service',
        'services.invoice_service',
        'services.report_service',
        'repositories.user_repository',
        'repositories.stock_transaction_repository',
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module}: {e}")
            failed.append(module)
    
    return len(failed) == 0

def test_branches():
    """Test branch repository"""
    print("\nTesting branches...")
    try:
        from repositories.branch_repository import BranchRepository
        branches = BranchRepository.get_all()
        print(f"✓ Found {len(branches)} branches")
        for branch in branches:
            print(f"  - {branch.name} ({branch.code})")
        return len(branches) > 0
    except Exception as e:
        print(f"✗ Branch error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Tile Index System - Component Test")
    print("=" * 60)
    
    results = []
    results.append(("Database", test_database()))
    results.append(("Branches", test_branches()))
    results.append(("Imports", test_imports()))
    results.append(("Authentication", test_auth()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed! System is ready to use.")
        print("\nTo start the application, run: python main.py")
        print("Default login: musab / musab123")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

