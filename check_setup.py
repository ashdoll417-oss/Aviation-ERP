"""
Pre-Flight Check Script
Verifies that all required libraries are installed for the Aviation ERP project.
"""

import sys


def check_imports():
    """Check if all required libraries can be imported."""
    required_packages = {
        "fastapi": "fastapi",
        "supabase": "supabase",
        "dotenv": "python-dotenv",
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✓ {package_name} - Found")
        except ImportError:
            print(f"✗ {package_name} - Not found")
            missing_packages.append(package_name)
    
    print()  # Empty line
    
    if missing_packages:
        print("Missing packages detected!")
        print()
        print("Run the following command to install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        print()
        return False
    else:
        print("Environment Ready")
        return True


if __name__ == "__main__":
    success = check_imports()
    sys.exit(0 if success else 1)

