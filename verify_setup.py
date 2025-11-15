#!/usr/bin/env python3
"""
Setup verification script
Run this to check if your environment is configured correctly
"""

import sys
import os

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 10:
        print("  ✓ Python version is compatible (3.10+)")
        return True
    else:
        print("  ✗ Python version should be 3.10 or higher")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['flask', 'requests', 'dotenv', 'pyngrok']
    missing = []
    
    for package in required_packages:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"  ✓ {package} is installed")
        except ImportError:
            print(f"  ✗ {package} is NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("✓ All dependencies are installed")
        return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("✗ .env file not found")
        print("  Run: cp .env.example .env")
        print("  Then edit .env and add your credentials")
        return False
    
    print("✓ .env file exists")
    
    # Load and check variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'WHATSAPP_PHONE_NUMBER_ID': 'WhatsApp Phone Number ID',
        'WHATSAPP_ACCESS_TOKEN': 'WhatsApp Access Token',
        'WEBHOOK_VERIFY_TOKEN': 'Webhook Verify Token'
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value != f'your_{var.lower()}_here' and 'your_' not in value:
            print(f"  ✓ {description} is set")
        else:
            print(f"  ✗ {description} is NOT set or still has placeholder value")
            all_set = False
    
    return all_set

def check_files():
    """Check if all required files exist"""
    required_files = [
        'app.py',
        'config.py',
        'whatsapp_client.py',
        'timer_manager.py',
        'start_ngrok.py',
        'requirements.txt',
        '.env.example'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} is missing")
            all_exist = False
    
    if all_exist:
        print("✓ All required files are present")
    return all_exist

def main():
    """Run all checks"""
    print("=" * 70)
    print("WhatsApp Bot Setup Verification")
    print("=" * 70)
    print()
    
    checks = []
    
    print("1. Checking Python version...")
    checks.append(check_python_version())
    print()
    
    print("2. Checking required files...")
    checks.append(check_files())
    print()
    
    print("3. Checking dependencies...")
    checks.append(check_dependencies())
    print()
    
    print("4. Checking environment configuration...")
    checks.append(check_env_file())
    print()
    
    print("=" * 70)
    if all(checks):
        print("✅ All checks passed! You're ready to run the bot.")
        print()
        print("Next steps:")
        print("  1. Start ngrok: python start_ngrok.py")
        print("  2. Configure webhook in Meta Dashboard")
        print("  3. Run bot: python app.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("For detailed setup instructions, see SETUP_GUIDE.md")
    print("=" * 70)

if __name__ == '__main__':
    main()

