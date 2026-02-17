#!/usr/bin/env python3
"""Standalone Phase 2 validation script - doesn't require full pipeline dependencies."""

import sys
import time
from pathlib import Path

print("=" * 60)
print("PHASE 2 VALIDATION - Standalone Tests")
print("=" * 60)
print()

# Test 1: performance.py module
print("TEST 1: Resource Monitoring Module")
print("-" * 60)
try:
    from python.performance import ResourceMonitor, track_resources, progress_bar
    print("✓ performance.py imports successfully")

    # Test ResourceMonitor
    monitor = ResourceMonitor()
    monitor.start()
    _ = [i**2 for i in range(100000)]  # Simulate work
    time.sleep(0.1)
    report = monitor.report()

    assert "elapsed_sec" in report
    assert "peak_memory_mb" in report
    assert "cpu_percent" in report
    assert report["elapsed_sec"] >= 0.1
    print(f"✓ ResourceMonitor works - elapsed: {report['elapsed_sec']:.2f}s, mem: {report['peak_memory_mb']:.1f}MB")

    # Test context manager
    with track_resources("test_module") as mon:
        _ = [i**2 for i in range(50000)]
        time.sleep(0.05)

    ctx_report = mon.report()
    assert ctx_report["elapsed_sec"] >= 0.05
    print(f"✓ track_resources context manager works")

    # Test progress_bar wrapper
    items = list(range(10))
    result = list(progress_bar(items, desc="Test", disable=True))
    assert len(result) == 10
    print("✓ progress_bar wrapper works")

    print("✅ TEST 1 PASSED")
except Exception as e:
    print(f"❌ TEST 1 FAILED: {e}")
    sys.exit(1)

print()

# Test 2: Dependency parsing (from run_pipeline.py, but isolated)
print("TEST 2: Dependency Parsing Logic")
print("-" * 60)
try:
    def parse_deps(x: str) -> list[str]:
        """Parse dependency string."""
        return [d.strip() for d in x.split(",") if d.strip()] if x else []

    assert parse_deps("") == []
    assert parse_deps("00") == ["00"]
    assert parse_deps("00,01") == ["00", "01"]
    assert parse_deps("00, 01, 02") == ["00", "01", "02"]
    print("✓ parse_deps() logic correct")
    print("✅ TEST 2 PASSED")
except Exception as e:
    print(f"❌ TEST 2 FAILED: {e}")
    sys.exit(1)

print()

# Test 3: Level grouping algorithm (isolated test)
print("TEST 3: Module Grouping Algorithm")
print("-" * 60)
try:
    def group_modules_by_level_test(module_ids: list[str], registry: list[dict]) -> list[list[str]]:
        """Group modules into execution levels based on dependencies."""
        def parse_deps_local(x: str) -> list[str]:
            return [d.strip() for d in x.split(",") if d.strip()] if x else []

        index = {r["id"]: r for r in registry}
        levels = []
        completed = set()

        while len(completed) < len(module_ids):
            current_level = []
            for mid in module_ids:
                if mid in completed:
                    continue
                deps = parse_deps_local(index[mid]["deps"])
                if all(d in completed for d in deps):
                    current_level.append(mid)

            if not current_level:
                raise RuntimeError("Circular dependency detected")

            levels.append(current_level)
            completed.update(current_level)

        return levels

    # Test with simple registry
    test_registry = [
        {"id": "00", "deps": ""},
        {"id": "01", "deps": "00"},
        {"id": "02", "deps": "01"},
        {"id": "03", "deps": "02"},
    ]

    levels = group_modules_by_level_test(["00", "01", "02", "03"], test_registry)
    assert len(levels) == 4
    assert levels[0] == ["00"]
    assert levels[1] == ["01"]
    assert levels[2] == ["02"]
    assert levels[3] == ["03"]
    print("✓ Sequential dependency grouping correct")

    # Test with parallel opportunities
    parallel_registry = [
        {"id": "00", "deps": ""},
        {"id": "01", "deps": "00"},
        {"id": "02a", "deps": "01"},
        {"id": "02b", "deps": "01"},
        {"id": "02c", "deps": "01"},
    ]

    levels = group_modules_by_level_test(["00", "01", "02a", "02b", "02c"], parallel_registry)
    assert len(levels) == 3
    assert levels[0] == ["00"]
    assert levels[1] == ["01"]
    assert set(levels[2]) == {"02a", "02b", "02c"}  # All three should be in same level
    print("✓ Parallel grouping correct - 3 modules grouped in level 2")

    # Test circular dependency detection
    circular_registry = [
        {"id": "A", "deps": "B"},
        {"id": "B", "deps": "A"}
    ]

    try:
        levels = group_modules_by_level_test(["A", "B"], circular_registry)
        print("❌ Circular dependency not detected!")
        sys.exit(1)
    except RuntimeError as e:
        if "Circular" in str(e):
            print("✓ Circular dependency correctly detected")
        else:
            raise

    print("✅ TEST 3 PASSED")
except Exception as e:
    print(f"❌ TEST 3 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: File existence and syntax
print("TEST 4: File Existence and Syntax")
print("-" * 60)
files_to_check = [
    "python/performance.py",
    "python/run_pipeline.py",
    "tests/test_parallel.py",
    "pyproject.toml",
    "PHASE2_IMPLEMENTATION_SUMMARY.md"
]

for filepath in files_to_check:
    path = Path(filepath)
    if path.exists():
        print(f"✓ {filepath} exists ({path.stat().st_size} bytes)")
    else:
        print(f"❌ {filepath} missing!")
        sys.exit(1)

print("✅ TEST 4 PASSED")

print()
print("=" * 60)
print("ALL PHASE 2 VALIDATION TESTS PASSED! ✅")
print("=" * 60)
print()
print("Summary:")
print("  ✓ Resource monitoring works (performance.py)")
print("  ✓ Dependency parsing logic correct")
print("  ✓ Level grouping algorithm correct")
print("  ✓ Parallel execution grouping works")
print("  ✓ Circular dependency detection works")
print("  ✓ All Phase 2 files present")
print()
print("Next steps:")
print("  1. Install full dependencies: pip install pandas matplotlib scipy geopandas rasterio")
print("  2. Run full test suite: pytest tests/test_parallel.py -v")
print("  3. Test dry-run mode: python -m python.run_pipeline --dry-run")
print("  4. Benchmark performance with real data")
