#!/usr/bin/env python3
"""Test git tools against real repository to verify parsers work with actual git output.

This is Priority 1a of the Phase 27.5 Deep Audit.
Tests git_status, git_diff, and git_log parsers against THIS repository.
"""

import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from punie.agent.typed_tools import (
    parse_git_status_output,
    parse_git_diff_output,
    parse_git_log_output,
)


def test_git_status():
    """Test git_status parser against real git status output."""
    print("=" * 80)
    print("TEST 1: git_status parser")
    print("=" * 80)

    # Run real git status
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    print(f"\n📝 Raw git output ({len(result.stdout)} chars):")
    print(result.stdout[:500])  # First 500 chars
    if len(result.stdout) > 500:
        print(f"... ({len(result.stdout) - 500} more chars)")

    # Parse it
    parsed = parse_git_status_output(result.stdout)

    print("\n✅ Parser result:")
    print(f"  success: {parsed.success}")
    print(f"  file_count: {parsed.file_count}")
    print(f"  clean: {parsed.clean}")

    # Calculate counts manually
    staged_count = sum(1 for f in parsed.files if f.staged)
    untracked_count = sum(1 for f in parsed.files if f.status == "untracked")
    print(f"  staged_count: {staged_count}")
    print(f"  unstaged_count: {parsed.file_count - staged_count - untracked_count}")
    print(f"  untracked_count: {untracked_count}")

    print("\n📁 Sample files (first 10):")
    for i, file in enumerate(parsed.files[:10]):
        print(f"  {i+1}. {file.file}")
        print(f"     status={file.status}, staged={file.staged}")

    if len(parsed.files) > 10:
        print(f"  ... and {len(parsed.files) - 10} more files")

    # Check for known bugs
    print("\n🔍 Bug checks:")
    dual_status_files = [f for f in parsed.files if len(f.status) == 2 and f.status[0] != ' ' and f.status[1] != ' ']
    if dual_status_files:
        print(f"  ⚠️  Found {len(dual_status_files)} dual-status files (MM, AM, etc.):")
        for f in dual_status_files[:3]:
            print(f"     {f.file}: status={f.status}, staged={f.staged}")
        print("  Check: Does 'staged' correctly reflect BOTH index and worktree changes?")
    else:
        print("  ✅ No dual-status files found (or they're handled correctly)")

    return parsed


def test_git_diff():
    """Test git_diff parser against real git diff output."""
    print("\n" + "=" * 80)
    print("TEST 2: git_diff parser")
    print("=" * 80)

    # Run real git diff
    result = subprocess.run(
        ["git", "diff", "--stat"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    print(f"\n📝 Raw git output ({len(result.stdout)} chars):")
    print(result.stdout[:500])
    if len(result.stdout) > 500:
        print(f"... ({len(result.stdout) - 500} more chars)")

    # Parse it
    parsed = parse_git_diff_output(result.stdout)

    print("\n✅ Parser result:")
    print(f"  success: {parsed.success}")
    print(f"  file_count: {parsed.file_count}")
    print(f"  additions: {parsed.additions}")
    print(f"  deletions: {parsed.deletions}")

    print("\n📁 Sample files (first 10):")
    for i, file in enumerate(parsed.files[:10]):
        print(f"  {i+1}. {file.file}")
        print(f"     +{file.additions} -{file.deletions}")

    if len(parsed.files) > 10:
        print(f"  ... and {len(parsed.files) - 10} more files")

    # Check for known bugs
    print("\n🔍 Bug checks:")
    print("  Testing with binary file and deleted file scenarios...")

    # Test binary file parsing
    binary_output = "Binary files a/test.png and b/test.png differ\n 1 file changed, 0 insertions(+), 0 deletions(-)"
    try:
        binary_parsed = parse_git_diff_output(binary_output)
        print(f"  Binary file test: success={binary_parsed.success}, files={binary_parsed.file_count}")
        if binary_parsed.file_count == 0:
            print("  ⚠️  Binary files are NOT parsed (no +++ line)")
        else:
            print(f"  ✅ Binary files handled: {binary_parsed.files[0].file}")
    except Exception as e:
        print(f"  ❌ Binary file parsing crashed: {e}")

    # Test deleted file parsing
    deleted_output = " deleted.txt | 10 ----------\n 1 file changed, 0 insertions(+), 10 deletions(-)"
    try:
        deleted_parsed = parse_git_diff_output(deleted_output)
        print(f"  Deleted file test: success={deleted_parsed.success}, files={deleted_parsed.file_count}")
        if deleted_parsed.file_count > 0:
            print(f"  ✅ Deleted files handled: {deleted_parsed.files[0].file}")
    except Exception as e:
        print(f"  ❌ Deleted file parsing crashed: {e}")

    return parsed


def test_git_log():
    """Test git_log parser against real git log output."""
    print("\n" + "=" * 80)
    print("TEST 3: git_log parser (CRITICAL BUG TEST)")
    print("=" * 80)

    # Run CURRENT toolset command (git log --oneline)
    print("\n📝 Current toolset command: git log --oneline -n5")
    result_oneline = subprocess.run(
        ["git", "log", "--oneline", "-n5"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    print(f"Raw output ({len(result_oneline.stdout)} chars):")
    print(result_oneline.stdout)

    parsed_oneline = parse_git_log_output(result_oneline.stdout)

    print("\n✅ Parser result:")
    print(f"  success: {parsed_oneline.success}")
    print(f"  commit_count: {parsed_oneline.commit_count}")

    print("\n📝 Sample commits (first 3):")
    for i, commit in enumerate(parsed_oneline.commits[:3]):
        print(f"  {i+1}. {commit.hash}: {commit.message}")
        print(f"     author={commit.author}, date={commit.date}")

    # THE CRITICAL BUG CHECK
    print("\n🔍 CRITICAL BUG CHECK:")
    all_authors_none = all(c.author is None for c in parsed_oneline.commits)
    all_dates_none = all(c.date is None for c in parsed_oneline.commits)

    if all_authors_none and all_dates_none:
        print("  ❌ BUG CONFIRMED: All commits have author=None and date=None")
        print("  Reason: git log --oneline doesn't include author/date")
        print("  Impact: Stubs and training data claim these fields exist, but they're always None")
    else:
        print("  ✅ Authors/dates are populated correctly")

    # Test proposed fix
    print("\n📝 Proposed fix: git log --format='%h|%an|%ad|%s' -n5")
    result_format = subprocess.run(
        ["git", "log", "--format=%h|%an|%ad|%s", "-n5"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    print(f"Raw output with format ({len(result_format.stdout)} chars):")
    print(result_format.stdout)

    print("\n💡 Recommendation:")
    if all_authors_none:
        print("  1. Change toolset.py line to use --format='%h|%an|%ad|%s'")
        print("  2. Update parse_git_log_output to split on '|'")
        print("  OR")
        print("  3. Remove author/date from GitCommit model, stubs, and training data (honest approach)")

    return parsed_oneline


def main():
    """Run all git tool tests."""
    print("🔍 Phase 27.5 Deep Audit - Priority 1a: Real Git Tools Test")
    print("Testing git tools against THIS repository\n")

    try:
        status_result = test_git_status()
        diff_result = test_git_diff()
        log_result = test_git_log()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ git_status: Parsed {status_result.file_count} files")
        print(f"✅ git_diff: Parsed {diff_result.file_count} files")
        print(f"✅ git_log: Parsed {log_result.commit_count} commits")

        # Overall verdict
        has_bugs = any(c.author is None for c in log_result.commits)

        if has_bugs:
            print("\n⚠️  VERDICT: Parsers work but have known bugs (see details above)")
            print("   Recommend: Fix bugs before claiming these tools are 'working'")
        else:
            print("\n✅ VERDICT: All parsers work correctly against real git output!")

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
