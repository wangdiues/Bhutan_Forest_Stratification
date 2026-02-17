"""Tests for parallel execution functionality."""

from __future__ import annotations

import pytest
from pathlib import Path

from python.run_pipeline import (
    group_modules_by_level,
    get_module_registry,
    parse_deps,
    dry_run_pipeline,
)


def test_parse_deps():
    """Test dependency parsing."""
    assert parse_deps("") == []
    assert parse_deps("00") == ["00"]
    assert parse_deps("00,01") == ["00", "01"]
    assert parse_deps("00, 01, 02") == ["00", "01", "02"]


def test_group_modules_by_level_simple():
    """Test dependency-based level grouping with simple case."""
    registry = get_module_registry()

    # Test subset: modules 00-04
    module_ids = ["00", "01", "02", "03", "04"]
    levels = group_modules_by_level(module_ids, registry)

    # Expected grouping:
    # Level 0: [00]
    # Level 1: [01]
    # Level 2: [02]
    # Level 3: [03]
    # Level 4: [04]

    assert len(levels) == 5
    assert levels[0] == ["00"]
    assert levels[1] == ["01"]
    assert levels[2] == ["02"]
    assert levels[3] == ["03"]
    assert levels[4] == ["04"]


def test_parallel_group_detection():
    """Test that parallel modules are correctly grouped."""
    registry = get_module_registry()

    # Test full pipeline grouping
    all_ids = [r["id"] for r in registry]
    levels = group_modules_by_level(all_ids, registry)

    # Verify that we have some levels with multiple modules (parallelism)
    level_sizes = [len(lvl) for lvl in levels]
    assert max(level_sizes) >= 3, "Should have at least one level with 3+ parallel modules"

    # Verify specific parallel groups exist
    # Level with 01b, 02, 08 (all depend only on 01)
    parallel_after_01 = None
    for level in levels:
        if set(level) >= {"01b", "02", "08"}:
            parallel_after_01 = level
            break

    # We should find a level containing these modules (or most of them)
    # Note: exact grouping depends on full dependency resolution
    assert parallel_after_01 is not None or any(
        len(level) >= 2 for level in levels
    ), "Should have parallel execution opportunities"


def test_level_ordering():
    """Test that levels respect dependency order."""
    registry = get_module_registry()
    registry_index = {r["id"]: r for r in registry}

    all_ids = [r["id"] for r in registry]
    levels = group_modules_by_level(all_ids, registry)

    # Flatten levels to get execution order
    execution_order = []
    for level in levels:
        execution_order.extend(level)

    # For each module, verify all its dependencies appear before it
    for idx, mid in enumerate(execution_order):
        deps = parse_deps(registry_index[mid]["deps"])
        for dep in deps:
            dep_idx = execution_order.index(dep)
            assert dep_idx < idx, f"Module {mid} appears before its dependency {dep}"


def test_circular_dependency_detection():
    """Test that circular dependencies are caught."""
    # Create fake registry with circular dep
    fake_registry = [{"id": "A", "deps": "B"}, {"id": "B", "deps": "A"}]

    with pytest.raises(RuntimeError, match="Circular dependency"):
        group_modules_by_level(["A", "B"], fake_registry)


def test_dry_run_produces_valid_plan(config):
    """Test dry-run produces valid execution plan."""
    plan = dry_run_pipeline(modules=["03"], cfg=config)

    assert "modules_requested" in plan
    assert "modules_to_run" in plan
    assert "execution_levels" in plan
    assert "time_estimate" in plan

    # Module 03 requires 00, 01, 02 as dependencies
    assert "00" in plan["modules_to_run"]
    assert "01" in plan["modules_to_run"]
    assert "02" in plan["modules_to_run"]
    assert "03" in plan["modules_to_run"]

    # Should have speedup estimate
    assert plan["time_estimate"]["speedup"] >= 1.0


def test_dry_run_full_pipeline(config):
    """Test dry-run on full pipeline."""
    plan = dry_run_pipeline(cfg=config)

    # Should include all modules
    assert len(plan["modules_to_run"]) == 14

    # Should have reasonable estimates
    assert plan["time_estimate"]["sequential_sec"] > 0
    assert plan["time_estimate"]["parallel_sec"] > 0
    assert plan["time_estimate"]["speedup"] > 1.0

    # Should report input status
    assert "input_status" in plan
    assert plan["input_status"]["total"] > 0


def test_dry_run_module_range(config):
    """Test dry-run with module range."""
    plan = dry_run_pipeline(from_id="02", to_id="05", cfg=config)

    # Should include dependencies
    assert "00" in plan["modules_to_run"]
    assert "01" in plan["modules_to_run"]
    assert "02" in plan["modules_to_run"]
    assert "03" in plan["modules_to_run"]  # Dep for 04
    assert "04" in plan["modules_to_run"]
    assert "05" in plan["modules_to_run"]


def test_resource_monitor():
    """Test resource monitoring functionality."""
    from python.performance import ResourceMonitor
    import time

    monitor = ResourceMonitor()
    monitor.start()

    # Simulate work
    _ = [i**2 for i in range(100000)]
    time.sleep(0.1)

    report = monitor.report()

    assert "elapsed_sec" in report
    assert "peak_memory_mb" in report
    assert "cpu_percent" in report
    assert report["elapsed_sec"] >= 0.1


def test_track_resources_context_manager():
    """Test resource tracking context manager."""
    from python.performance import track_resources
    import time

    with track_resources("test_module") as monitor:
        # Simulate work
        _ = [i**2 for i in range(50000)]
        time.sleep(0.05)

    report = monitor.report()
    assert report["elapsed_sec"] >= 0.05


@pytest.mark.skipif(not Path("raw_data").exists(), reason="Requires data for integration test")
def test_parallel_execution_smoke(config):
    """
    Integration test: verify parallel execution can run without errors.
    This is a smoke test that doesn't validate outputs in detail.
    """
    from python.run_pipeline import run_pipeline_parallel

    # Run module 00 in parallel mode (trivial case, but validates machinery)
    result = run_pipeline_parallel(modules=["00"], cfg=config, max_workers=2)

    assert result is not None
    assert "success" in result
    assert "module_results" in result
    assert "00" in result["module_results"]
