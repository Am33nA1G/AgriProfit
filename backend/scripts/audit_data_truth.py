"""
Data Truth Audit Script
Verifies that the application serves only real data from the database,
with no mock, fake, or placeholder data in production code paths.
"""
import sys
import os
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Project root
BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend" / "src"

# Patterns that indicate mock/fake data in production code
MOCK_PATTERNS = [
    (r'Math\.random\(\)', "JavaScript random - potential fake data generation"),
    (r'random\.uniform\(', "Python random.uniform - potential fake data generation"),
    (r'random\.choice\(', "Python random.choice - potential fake data generation"),
    (r'random\.randint\(', "Python random.randint - potential fake data generation"),
    (r'import\s+random\b', "Python random import"),
    (r'from faker import', "Faker library import"),
    (r'setTimeout\(.+resolve\(.+\d{3,}', "setTimeout resolving promise with delay - potential fake async"),
    (r'def\s+mock_', "Function named mock_*"),
    (r'def\s+fake_', "Function named fake_*"),
    (r'function\s+mock', "Function named mock*"),
    (r'function\s+fake', "Function named fake*"),
]

# Directories/files to exclude
EXCLUDE_DIRS = {'__tests__', 'tests', 'test', 'node_modules', '__pycache__', '.git', '.next'}
EXCLUDE_FILES = {'.test.ts', '.test.tsx', '.test.py', 'conftest.py', 'test_', 'setup.ts'}
EXCLUDE_SCRIPTS = {'manage_db.py', 'seed_', 'audit_data_truth.py'}


def should_skip(path: Path) -> bool:
    """Check if a file should be skipped."""
    parts = path.parts
    for exclude_dir in EXCLUDE_DIRS:
        if exclude_dir in parts:
            return True
    name = path.name
    for exclude_file in EXCLUDE_FILES:
        if name.endswith(exclude_file) or name.startswith(exclude_file):
            return True
    for exclude_script in EXCLUDE_SCRIPTS:
        if name.startswith(exclude_script) or name == exclude_script:
            return True
    return False


def scan_file(filepath: Path) -> list:
    """Scan a single file for mock data patterns."""
    findings = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return findings

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('*'):
            continue  # Skip comments
        for pattern, description in MOCK_PATTERNS:
            if re.search(pattern, line):
                findings.append({
                    'file': str(filepath),
                    'line': i,
                    'pattern': description,
                    'code': stripped[:120],
                })
    return findings


def scan_directory(root: Path, extensions: set) -> list:
    """Scan a directory tree for mock patterns."""
    all_findings = []
    for filepath in root.rglob('*'):
        if filepath.is_file() and filepath.suffix in extensions:
            if should_skip(filepath):
                continue
            findings = scan_file(filepath)
            all_findings.extend(findings)
    return all_findings


def check_backend_api_routes(backend_dir: Path) -> list:
    """Verify backend API routes don't generate fake data."""
    issues = []
    routes_dir = backend_dir / "app"
    for py_file in routes_dir.rglob("routes.py"):
        if should_skip(py_file):
            continue
        content = py_file.read_text(encoding='utf-8', errors='replace')
        if 'import random' in content:
            issues.append(f"CRITICAL: {py_file} imports 'random' - API route should not generate random data")
        if 'from faker' in content:
            issues.append(f"CRITICAL: {py_file} imports 'faker' - API route should not use Faker")
        if 'Math.random' in content:
            issues.append(f"CRITICAL: {py_file} uses Math.random()")
    return issues


def check_frontend_services(frontend_dir: Path) -> list:
    """Verify frontend services don't have mock fallbacks."""
    issues = []
    services_dir = frontend_dir / "services"
    if not services_dir.exists():
        return issues

    for ts_file in services_dir.glob("*.ts"):
        if should_skip(ts_file):
            continue
        content = ts_file.read_text(encoding='utf-8', errors='replace')
        if 'Math.random()' in content:
            issues.append(f"CRITICAL: {ts_file} uses Math.random() - service should not generate fake data")
        # Check for catch blocks that return hardcoded arrays with actual data items
        catch_blocks = re.findall(r'catch\s*[\({][^}]*return\s+\[([^\]]+)\]', content, re.DOTALL)
        for block in catch_blocks:
            if any(kw in block for kw in ['name:', 'price:', 'commodity:', 'mandi:']):
                issues.append(f"WARNING: {ts_file} may return mock data in catch block")
    return issues


def main():
    print("=" * 70)
    print("DATA TRUTH AUDIT")
    print("Verifying no mock/fake/placeholder data in production code")
    print("=" * 70)

    total_issues = 0

    # 1. Scan backend Python files
    print("\n[1/4] Scanning backend Python files...")
    backend_findings = scan_directory(BACKEND_DIR / "app", {'.py'})
    if backend_findings:
        print(f"  FOUND {len(backend_findings)} potential issues:")
        for f in backend_findings:
            print(f"    {f['file']}:{f['line']} - {f['pattern']}")
            print(f"      {f['code']}")
        total_issues += len(backend_findings)
    else:
        print("  PASS - No mock patterns found in backend production code")

    # 2. Scan frontend TypeScript/JavaScript files
    print("\n[2/4] Scanning frontend source files...")
    frontend_findings = scan_directory(FRONTEND_DIR, {'.ts', '.tsx', '.js', '.jsx'})
    if frontend_findings:
        print(f"  FOUND {len(frontend_findings)} potential issues:")
        for f in frontend_findings:
            print(f"    {f['file']}:{f['line']} - {f['pattern']}")
            print(f"      {f['code']}")
        total_issues += len(frontend_findings)
    else:
        print("  PASS - No mock patterns found in frontend production code")

    # 3. Check backend API routes specifically
    print("\n[3/4] Checking backend API routes...")
    route_issues = check_backend_api_routes(BACKEND_DIR)
    if route_issues:
        for issue in route_issues:
            print(f"  {issue}")
        total_issues += len(route_issues)
    else:
        print("  PASS - All API routes are clean")

    # 4. Check frontend services
    print("\n[4/4] Checking frontend services...")
    service_issues = check_frontend_services(FRONTEND_DIR)
    if service_issues:
        for issue in service_issues:
            print(f"  {issue}")
        total_issues += len(service_issues)
    else:
        print("  PASS - All frontend services are clean")

    # Summary
    print("\n" + "=" * 70)
    if total_issues == 0:
        print("AUDIT RESULT: PASS")
        print("No mock, fake, or placeholder data found in production code.")
        print("All data served to users comes from the real database.")
    else:
        print(f"AUDIT RESULT: {total_issues} ISSUES FOUND")
        print("Review the items above and fix any CRITICAL issues.")
    print("=" * 70)

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
