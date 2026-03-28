#!/usr/bin/env python3
"""
Quick setup wizard for AgriProfit - Run this to check prerequisites and guide setup
Usage: python setup_check.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, check_only=False):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check_only:
            return result.returncode == 0
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def check_prerequisite(name, command, version_flag="--version"):
    """Check if a prerequisite is installed"""
    print(f"\n✓ Checking {name}...", end=" ")
    cmd = f"{command} {version_flag}" if version_flag else command
    success, output = run_command(cmd)
    
    if success:
        print(f"✅ Found\n  {output}")
        return True
    else:
        print(f"❌ Not found")
        return False

def check_directory_structure():
    """Verify expected directories exist"""
    print("\n" + "="*50)
    print("CHECKING DIRECTORY STRUCTURE")
    print("="*50)
    
    dirs = {
        "backend": "Backend API (FastAPI)",
        "frontend": "Web Application (Next.js)",
        "mobile": "Mobile App (React Native/Expo)",
        "database": "Database schemas",
        "docs": "Documentation",
    }
    
    all_good = True
    for dir_name, description in dirs.items():
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            print(f"✅ {dir_name:15} - {description}")
        else:
            print(f"❌ {dir_name:15} - MISSING")
            all_good = False
    
    return all_good

def check_env_files():
    """Check if .env files exist"""
    print("\n" + "="*50)
    print("CHECKING ENVIRONMENT FILES")
    print("="*50)
    
    env_files = {
        "backend/.env": "Backend configuration",
        "frontend/.env.local": "Frontend configuration",
        "mobile/.env": "Mobile configuration",
    }
    
    all_good = True
    for env_file, description in env_files.items():
        path = Path(env_file)
        if path.exists():
            print(f"✅ {env_file:25} - exists")
        else:
            example = Path(f"{env_file.rsplit('.', 1)[0]}.example")
            if example.exists():
                print(f"⚠️  {env_file:25} - missing (create from .example)")
                all_good = False
            else:
                print(f"❌ {env_file:25} - NOT FOUND")
                all_good = False
    
    return all_good

def main():
    print("\n" + "="*50)
    print("AGRIPROFIT SETUP CHECKER")
    print("="*50)
    
    # Check prerequisites
    print("\nCHECKING PREREQUISITES")
    print("="*50)
    
    checks = [
        ("Python", "python", "--version"),
        ("Node.js", "node", "--version"),
        ("npm", "npm", "--version"),
        ("Git", "git", "--version"),
        ("PostgreSQL", "psql", "--version"),
    ]
    
    passed = 0
    failed = 0
    
    for name, cmd, flag in checks:
        if check_prerequisite(name, cmd, flag):
            passed += 1
        else:
            print(f"   ⚠️  Install: {name}")
            failed += 1
    
    # Check directory structure
    if check_directory_structure():
        print("\n✅ Repository structure is correct")
    else:
        print("\n❌ Some directories are missing")
        return 1
    
    # Check environment files
    if check_env_files():
        print("\n✅ All environment files are configured")
    else:
        print("\n⚠️  Some .env files need to be created")
    
    # Summary
    print("\n" + "="*50)
    print("SETUP SUMMARY")
    print("="*50)
    
    if failed == 0:
        print("\n✅ All prerequisites installed!")
        print("\nNext steps:")
        print("1. Configure .env files (if not done)")
        print("2. Create database: psql -U postgres")
        print("3. Run: cd backend && venv/Scripts/activate && alembic upgrade head")
        print("4. Run: cd frontend && npm install")
        print("5. Start backend: uvicorn app.main:app --reload")
        print("6. Start frontend: npm run dev")
        print("\n📚 Read SETUP_FRIEND_PC.md for detailed instructions")
        return 0
    else:
        print(f"\n❌ {failed} prerequisites missing:")
        print("\nInstall missing software, then run this script again.")
        print("\n📚 See SETUP_FRIEND_PC.md for installation instructions")
        return 1

if __name__ == "__main__":
    sys.exit(main())
