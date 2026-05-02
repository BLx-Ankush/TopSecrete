"""
Simple verification script for Task 2.1 enum definitions.
Reads types.py file and verifies enum definitions without importing.
"""

from pathlib import Path

def verify_enums():
    """Verify enum definitions match design requirements"""
    
    types_file = Path("Alice_code/alice_browser_automation/types.py")
    
    if not types_file.exists():
        print("❌ types.py file not found!")
        return False
    
    content = types_file.read_text()
    
    # Check for TaskType enum
    print("Checking TaskType enum...")
    task_type_checks = [
        'class TaskType(Enum):',
        'WEB_BOOKING = "web_booking"',
        'PROBLEM_SOLVING = "problem_solving"',
        'APP_ACCESS = "app_access"'
    ]
    
    task_type_ok = all(check in content for check in task_type_checks)
    if task_type_ok:
        print("  ✅ TaskType enum: CORRECT")
    else:
        print("  ❌ TaskType enum: MISSING OR INCORRECT")
        for check in task_type_checks:
            if check not in content:
                print(f"     Missing: {check}")
    
    # Check for ActionType enum
    print("\nChecking ActionType enum...")
    action_type_checks = [
        'class ActionType(Enum):',
        'NAVIGATE = "navigate"',
        'CLICK = "click"',
        'TYPE = "type"',
        'WAIT = "wait"',
        'EXTRACT = "extract"',
        'SCROLL = "scroll"',
        'SELECT = "select"',
        'UPLOAD = "upload"',
        'DOWNLOAD = "download"'
    ]
    
    action_type_ok = all(check in content for check in action_type_checks)
    if action_type_ok:
        print("  ✅ ActionType enum: CORRECT")
    else:
        print("  ❌ ActionType enum: MISSING OR INCORRECT")
        for check in action_type_checks:
            if check not in content:
                print(f"     Missing: {check}")
    
    # Check for SessionState enum
    print("\nChecking SessionState enum...")
    session_state_checks = [
        'class SessionState(Enum):',
        'CREATING = "creating"',
        'ACTIVE = "active"',
        'IDLE = "idle"',
        'CRASHED = "crashed"',
        'CLOSING = "closing"'
    ]
    
    session_state_ok = all(check in content for check in session_state_checks)
    if session_state_ok:
        print("  ✅ SessionState enum: CORRECT")
    else:
        print("  ❌ SessionState enum: MISSING OR INCORRECT")
        for check in session_state_checks:
            if check not in content:
                print(f"     Missing: {check}")
    
    print("\n" + "=" * 70)
    if task_type_ok and action_type_ok and session_state_ok:
        print("✅ TASK 2.1 VERIFICATION: ALL ENUMS CORRECT")
        print("=" * 70)
        return True
    else:
        print("❌ TASK 2.1 VERIFICATION: SOME ENUMS HAVE ISSUES")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = verify_enums()
    exit(0 if success else 1)
