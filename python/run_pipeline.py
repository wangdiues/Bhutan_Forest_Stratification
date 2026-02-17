from __future__ import annotations

import argparse
import importlib.util
import logging
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from config import config
    from utils import log_done, log_section, setup_logging, write_json
    from validation import ValidationError, validate_canonical_outputs, validate_module_result
    from caching import (
        load_cache,
        save_cache,
        should_skip_module,
        update_cache_entry,
        clear_cache as clear_module_cache,
    )
    from performance import profile_module, write_profile_report, identify_bottlenecks, format_profile_summary
except ImportError:
    from python.config import config
    from python.utils import log_done, log_section, setup_logging, write_json
    from python.validation import ValidationError, validate_canonical_outputs, validate_module_result
    from python.caching import (
        load_cache,
        save_cache,
        should_skip_module,
        update_cache_entry,
        clear_cache as clear_module_cache,
    )
    from python.performance import (
        profile_module,
        write_profile_report,
        identify_bottlenecks,
        format_profile_summary,
    )


def get_module_registry() -> list[dict[str, str]]:
    return [
        {"id": "00", "name": "data_inspection", "file": "python/modules/00_data_inspection.py", "deps": ""},
        {"id": "01", "name": "data_cleaning", "file": "python/modules/01_data_cleaning.py", "deps": "00"},
        {"id": "01b", "name": "qc_after_cleaning", "file": "python/modules/01b_qc_after_cleaning.py", "deps": "01"},
        {"id": "02", "name": "env_extraction", "file": "python/modules/02_env_extraction.py", "deps": "01"},
        {"id": "02b", "name": "qc_after_env_extraction", "file": "python/modules/02b_qc_after_env_extraction.py", "deps": "02"},
        {"id": "03", "name": "alpha_diversity", "file": "python/modules/03_alpha_diversity.py", "deps": "02"},
        {"id": "04", "name": "beta_diversity", "file": "python/modules/04_beta_diversity.py", "deps": "03"},
        {"id": "05", "name": "cca_ordination", "file": "python/modules/05_cca_ordination.py", "deps": "02"},
        {"id": "06", "name": "indicator_species", "file": "python/modules/06_indicator_species.py", "deps": "03"},
        {"id": "07", "name": "co_occurrence", "file": "python/modules/07_co_occurrence.py", "deps": "03"},
        {"id": "08", "name": "evi_trends", "file": "python/modules/08_evi_trends.py", "deps": "01"},
        {"id": "09", "name": "sci_index", "file": "python/modules/09_sci_index.py", "deps": "03"},
        {"id": "10", "name": "spatial_mapping", "file": "python/modules/10_spatial_mapping.py", "deps": "03,04,08,09"},
        {"id": "11", "name": "reporting", "file": "python/modules/11_reporting.py", "deps": "03,04,05,06,07,08,09,10"},
    ]


def normalize_module_id(module_id: str) -> str:
    s = str(module_id).strip().lower()
    if s.isdigit():
        return f"{int(s):02d}"
    if len(s) >= 2 and s[:-1].isdigit() and s[-1].isalpha():
        return f"{int(s[:-1]):02d}{s[-1]}"
    return s


def parse_deps(x: str) -> list[str]:
    return [d.strip() for d in x.split(",") if d.strip()] if x else []


def expand_dependencies(module_ids: list[str], registry: list[dict[str, str]]) -> list[str]:
    index = {r["id"]: r for r in registry}
    out: list[str] = []

    def add_with_deps(mid: str) -> None:
        if mid in out:
            return
        if mid not in index:
            raise RuntimeError(f"Unknown module id: {mid}")
        for dep in parse_deps(index[mid]["deps"]):
            add_with_deps(dep)
        out.append(mid)

    for m in module_ids:
        add_with_deps(m)
    return out


def group_modules_by_level(module_ids: list[str], registry: list[dict]) -> list[list[str]]:
    """
    Group modules into execution levels based on dependencies.

    Returns list of lists, where each inner list contains modules
    that can run in parallel (same level in dependency graph).
    """
    index = {r["id"]: r for r in registry}
    levels = []
    completed = set()

    while len(completed) < len(module_ids):
        # Find modules whose dependencies are all completed
        current_level = []
        for mid in module_ids:
            if mid in completed:
                continue
            deps = parse_deps(index[mid]["deps"])
            if all(d in completed for d in deps):
                current_level.append(mid)

        if not current_level:
            raise RuntimeError("Circular dependency detected")

        levels.append(current_level)
        completed.update(current_level)

    return levels


def collect_input_snapshot(cfg: dict) -> dict:
    snap = {}
    for key, path in cfg["paths"]["inputs"].items():
        p = Path(path)
        if p.exists():
            stat = p.stat()
            snap[key] = {"path": str(p), "exists": True, "size_bytes": stat.st_size, "mtime": stat.st_mtime}
        else:
            snap[key] = {"path": str(p), "exists": False, "size_bytes": None, "mtime": None}
    return snap


def _load_module_from_file(file_path: Path):
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module file: {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_module(
    module_id: str,
    cfg: dict,
    logger: logging.Logger | None = None,
    track_perf: bool = True,
    use_cache: bool = True,
    cache: dict | None = None,
    enable_profiling: bool = False,
) -> dict:
    module_id = normalize_module_id(module_id)
    registry = get_module_registry()
    row = next((r for r in registry if r["id"] == module_id), None)
    if row is None:
        raise RuntimeError(f"Unknown module id: {module_id}")

    # Check cache if enabled
    if use_cache and cache is not None:
        can_skip, skip_reason = should_skip_module(module_id, cfg, cache, logger)
        if can_skip:
            # Return cached result
            cached_entry = cache.get(module_id, {})
            if logger:
                logger.info(f"Module {module_id} skipped (cached)")
            return {
                "status": "cached",
                "outputs": cached_entry.get("outputs", []),
                "warnings": [],
                "runtime_sec": 0.0,
                "module_id": row["id"],
                "module_name": row["name"],
                "cache_reason": skip_reason,
            }

    module_file = Path(cfg["root"]) / row["file"]
    if not module_file.exists():
        raise RuntimeError(f"Module file not found: {module_file}")

    # Use logger if available, otherwise fall back to legacy logging
    if logger:
        logger.info(f"Starting module {row['id']}: {row['name']}")
    else:
        log_section(f"module {row['id']} {row['name']}")
    t0 = time.time()

    # Import performance monitoring if requested
    monitor = None
    if track_perf:
        try:
            try:
                from performance import track_resources
            except ImportError:
                from python.performance import track_resources
            # Create a context manager instance for resource tracking
            monitor_ctx = track_resources(module_id, logger=logger)
            monitor = monitor_ctx.__enter__()
        except ImportError:
            monitor = None

    # Enable profiling if requested
    profiler_ctx = None
    if enable_profiling:
        try:
            profiler_ctx = profile_module(module_id)
            profiler = profiler_ctx.__enter__()
        except Exception:
            profiler_ctx = None
            profiler = None
    else:
        profiler = None

    try:
        mod = _load_module_from_file(module_file)
        if not hasattr(mod, "module_run"):
            raise RuntimeError(f"module_run(config) not defined in {module_file}")
        result = mod.module_run(cfg)
        if not isinstance(result, dict):
            raise RuntimeError(f"module_run did not return a dict in {module_file}")

        # Validate result contract and outputs
        try:
            validate_module_result(result, module_id)
            validate_canonical_outputs(cfg, module_id)
            if logger:
                logger.debug(f"Module {module_id} output validation passed")
        except ValidationError as ve:
            if logger:
                logger.warning(f"Validation warning for module {module_id}: {ve}")
            # Add validation warning but don't fail the module
            result.setdefault("warnings", []).append(f"Validation: {ve}")

    except Exception as exc:
        result = {
            "status": "failed",
            "outputs": [],
            "warnings": [f"{type(exc).__name__}: {exc}"],
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }
    finally:
        # Capture resource report if monitoring was enabled
        if monitor:
            try:
                resource_report = monitor.report()
                # We'll add this to result after warnings are normalized
            except Exception:
                resource_report = None
            try:
                monitor_ctx.__exit__(None, None, None)
            except Exception:
                pass
        else:
            resource_report = None

        # Capture profiling report if enabled
        if profiler_ctx:
            try:
                profiler_ctx.__exit__(None, None, None)
                if profiler:
                    profile_stats = profiler.get_stats()
                    profile_dir = Path(cfg["paths"]["cache"]["profile_dir"])
                    profile_file = write_profile_report(module_id, profile_stats, profile_dir)
                    bottlenecks = identify_bottlenecks(profile_stats, threshold_percent=10.0)
                    profile_summary = {
                        "profile_file": str(profile_file),
                        "bottlenecks": bottlenecks,
                        "total_functions": len(profile_stats),
                    }
                    if logger and bottlenecks:
                        logger.info(f"Module {module_id} bottlenecks: {len(bottlenecks)} functions > 10% time")
                else:
                    profile_summary = None
            except Exception as e:
                profile_summary = None
                if logger:
                    logger.debug(f"Profiling error: {e}")
        else:
            profile_summary = None

    warnings = result.get("warnings", [])
    if isinstance(warnings, str):
        warnings = [warnings]
    elif not isinstance(warnings, list):
        warnings = [str(warnings)]
    result["warnings"] = warnings

    runtime_sec = result.get("runtime_sec", time.time() - t0)
    result["runtime_sec"] = runtime_sec
    result["module_id"] = row["id"]
    result["module_name"] = row["name"]

    # Add resource report if available
    if resource_report:
        result["resources"] = resource_report

    # Add profiling summary if available
    if profile_summary:
        result["profiling"] = profile_summary

    # Update cache if module succeeded and caching is enabled
    if use_cache and cache is not None and result.get("status") != "failed":
        try:
            update_cache_entry(module_id, cfg, cache)
            if logger:
                logger.debug(f"Module {module_id} cache updated")
        except Exception as e:
            if logger:
                logger.debug(f"Cache update failed: {e}")

    if result.get("status") != "failed":
        if logger:
            logger.info(f"Module {row['id']} completed in {runtime_sec:.2f} sec")
        else:
            log_done(f"module {row['id']} finished in {runtime_sec:.2f} sec")
    else:
        msg = " | ".join(result.get("warnings", [])) or "Unknown error"
        if logger:
            logger.error(f"Module {row['id']} failed: {msg}")
            if "error" in result and "traceback" in result["error"]:
                logger.debug(f"Traceback:\n{result['error']['traceback']}")
        else:
            print(f"Module failed: {row['id']} - {msg}")

    return result


def run_pipeline(modules: list[str] | None = None, from_id: str | None = None, to_id: str | None = None, cfg: dict | None = None, log_level: str = "INFO", show_progress: bool = True) -> dict:
    """Run pipeline sequentially (original behavior)."""
    cfg = cfg or config
    registry = get_module_registry()
    ids = [r["id"] for r in registry]

    if modules:
        target = [normalize_module_id(m) for m in modules]
    elif from_id is not None or to_id is not None:
        start = normalize_module_id(from_id or ids[0])
        end = normalize_module_id(to_id or ids[-1])
        if start not in ids or end not in ids or ids.index(start) > ids.index(end):
            raise RuntimeError("Invalid from/to module range.")
        target = ids[ids.index(start): ids.index(end) + 1]
    else:
        target = ids

    run_ids = expand_dependencies(target, registry)

    # Initialize logging
    Path(cfg["paths"]["logs"]["run_logs_dir"]).mkdir(parents=True, exist_ok=True)
    logger = setup_logging(cfg, level=log_level)
    logger.info(f"Starting pipeline with modules: {target}")
    logger.info(f"Resolved execution order: {run_ids}")
    logger.debug(f"Configuration root: {cfg['root']}")

    # Initialize progress bar
    try:
        from progress import PipelineProgressBar
        progress = PipelineProgressBar(len(run_ids), show_progress=show_progress)
        progress.start("Pipeline Progress")
    except ImportError:
        progress = None

    results: dict[str, dict] = {}
    registry_index = {r["id"]: r for r in registry}

    for mid in run_ids:
        module_name = registry_index[mid]["name"]
        if progress:
            progress.update_module(mid, module_name, "running")

        results[mid] = run_module(mid, cfg, logger=logger)

        if progress:
            status = "failed" if results[mid].get("status") == "failed" else "completed"
            progress.update_module(mid, module_name, status)
            progress.complete_module(success=(status == "completed"))

        if results[mid].get("status") == "failed":
            logger.error(f"Pipeline stopped due to module {mid} failure")
            break

    if progress:
        progress.finish(success=all(r.get("status") != "failed" for r in results.values()))

    success = all(r.get("status") != "failed" for r in results.values())
    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": cfg["params"]["seed"],
        "modules_requested": target,
        "modules_run": list(results.keys()),
        "success": success,
        "module_results": results,
        "input_snapshot": collect_input_snapshot(cfg),
    }
    manifest_path = cfg["paths"]["logs"]["run_manifest"]
    write_json(manifest_path, manifest)

    if success:
        logger.info(f"Pipeline completed successfully - {len(results)} modules run")
    else:
        logger.warning(f"Pipeline completed with failures - {len(results)} modules attempted")
    logger.info(f"Run manifest written to: {manifest_path}")

    return manifest


def run_pipeline_parallel(
    modules: list[str] | None = None,
    from_id: str | None = None,
    to_id: str | None = None,
    cfg: dict | None = None,
    log_level: str = "INFO",
    max_workers: int | None = None,
    continue_on_error: bool = False,
    show_progress: bool = True,
    use_cache: bool = True,
    enable_profiling: bool = False,
) -> dict:
    """
    Run pipeline with level-based parallel execution.

    Args:
        modules: Specific module IDs to run
        from_id: Start module ID
        to_id: End module ID
        cfg: Configuration dictionary
        log_level: Logging level
        max_workers: Max parallel threads (default: config['params']['cores'])
        continue_on_error: Continue executing independent modules even if some fail

    Returns:
        Manifest dictionary with execution results
    """
    cfg = cfg or config
    registry = get_module_registry()
    ids = [r["id"] for r in registry]

    # Resolve target modules (same logic as sequential)
    if modules:
        target = [normalize_module_id(m) for m in modules]
    elif from_id is not None or to_id is not None:
        start = normalize_module_id(from_id or ids[0])
        end = normalize_module_id(to_id or ids[-1])
        if start not in ids or end not in ids or ids.index(start) > ids.index(end):
            raise RuntimeError("Invalid from/to module range.")
        target = ids[ids.index(start) : ids.index(end) + 1]
    else:
        target = ids

    run_ids = expand_dependencies(target, registry)

    # Initialize logging
    Path(cfg["paths"]["logs"]["run_logs_dir"]).mkdir(parents=True, exist_ok=True)
    logger = setup_logging(cfg, level=log_level)
    logger.info(f"Starting parallel pipeline with modules: {target}")

    # Load cache if enabled
    cache = load_cache(cfg) if use_cache else None
    if cache and logger:
        logger.info(f"Cache loaded with {len(cache)} entries")
    if enable_profiling and logger:
        logger.info("Profiling enabled for all modules")

    # Group modules by execution level
    levels = group_modules_by_level(run_ids, registry)
    logger.info(f"Execution plan: {len(levels)} levels, max parallelism: {max(len(lvl) for lvl in levels)}")

    max_workers = max_workers or cfg["params"]["cores"]
    results: dict[str, dict] = {}
    failed_modules = set()
    registry_index = {r["id"]: r for r in registry}

    # Initialize progress bar
    try:
        from progress import PipelineProgressBar
        progress = PipelineProgressBar(len(run_ids), show_progress=show_progress)
        progress.start("Parallel Pipeline")
    except ImportError:
        progress = None

    # Execute level by level
    for level_idx, level_modules in enumerate(levels):
        logger.info(f"Level {level_idx + 1}/{len(levels)}: {level_modules}")

        # Skip modules that depend on failed modules (if continue_on_error)
        if continue_on_error and failed_modules:
            skipped = []
            for m in level_modules:
                deps = parse_deps(registry_index[m]["deps"])
                if any(d in failed_modules for d in deps):
                    skipped.append(m)

            for mid in skipped:
                results[mid] = {
                    "status": "skipped",
                    "outputs": [],
                    "warnings": [f"Skipped due to failed dependency: {failed_modules}"],
                    "runtime_sec": 0.0,
                }
            level_modules = [m for m in level_modules if m not in skipped]

        if not level_modules:
            continue

        # Run modules in this level in parallel
        if len(level_modules) == 1:
            # No need for threading overhead
            mid = level_modules[0]
            if progress:
                progress.update_module(mid, registry_index[mid]["name"], "running")
            results[mid] = run_module(
                mid, cfg, logger=logger, use_cache=use_cache, cache=cache, enable_profiling=enable_profiling
            )
            if progress:
                status = results[mid].get("status")
                if status == "cached":
                    status = "completed"  # Show cached as completed
                elif status == "failed":
                    status = "failed"
                else:
                    status = "completed"
                progress.update_module(mid, registry_index[mid]["name"], status)
                progress.complete_module(success=(status == "completed"))
        else:
            # Parallel execution using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(max_workers, len(level_modules))) as executor:
                future_to_module = {
                    executor.submit(
                        run_module, mid, cfg, logger, True, use_cache, cache, enable_profiling
                    ): mid
                    for mid in level_modules
                }

                for future in as_completed(future_to_module):
                    mid = future_to_module[future]
                    if progress:
                        progress.update_module(mid, registry_index[mid]["name"], "running")
                    try:
                        results[mid] = future.result()
                        if progress:
                            status = results[mid].get("status")
                            if status == "cached":
                                status = "completed"
                            elif status == "failed":
                                status = "failed"
                            else:
                                status = "completed"
                            progress.update_module(mid, registry_index[mid]["name"], status)
                            progress.complete_module(success=(status == "completed"))
                    except Exception as exc:
                        logger.error(f"Module {mid} raised unexpected exception: {exc}")
                        results[mid] = {
                            "status": "failed",
                            "outputs": [],
                            "warnings": [str(exc)],
                            "runtime_sec": 0.0,
                            "error": {"type": type(exc).__name__, "message": str(exc)},
                        }
                        if progress:
                            progress.update_module(mid, registry_index[mid]["name"], "failed")
                            progress.complete_module(success=False)

        # Check for failures
        level_failures = [m for m in level_modules if results.get(m, {}).get("status") == "failed"]
        if level_failures:
            failed_modules.update(level_failures)
            if not continue_on_error:
                logger.error(f"Level {level_idx + 1} had failures: {level_failures}. Stopping.")
                break

    # Finish progress bar
    if progress:
        progress.finish(success=all(r.get("status") != "failed" for r in results.values()))

    # Save cache if enabled
    if use_cache and cache is not None:
        try:
            save_cache(cache, cfg)
            logger.info(f"Cache saved with {len(cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    # Write manifest
    success = all(r.get("status") != "failed" for r in results.values())
    # Count cached modules
    cached_count = sum(1 for r in results.values() if r.get("status") == "cached")

    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": cfg["params"]["seed"],
        "modules_requested": target,
        "modules_run": list(results.keys()),
        "success": success,
        "execution_mode": "parallel",
        "max_workers": max_workers,
        "continue_on_error": continue_on_error,
        "cache_enabled": use_cache,
        "cached_modules": cached_count,
        "profiling_enabled": enable_profiling,
        "module_results": results,
        "input_snapshot": collect_input_snapshot(cfg),
    }
    manifest_path = cfg["paths"]["logs"]["run_manifest"]
    write_json(manifest_path, manifest)

    if success:
        logger.info(f"Pipeline completed successfully - {len(results)} modules run")
    else:
        logger.warning(f"Pipeline completed with failures - {len(results)} modules attempted")
    logger.info(f"Run manifest written to: {manifest_path}")

    return manifest


def dry_run_pipeline(
    modules: list[str] | None = None,
    from_id: str | None = None,
    to_id: str | None = None,
    cfg: dict | None = None,
) -> dict:
    """
    Preview execution plan without running modules.

    Returns:
        Dictionary with execution plan, input status, and estimates
    """
    cfg = cfg or config
    registry = get_module_registry()
    ids = [r["id"] for r in registry]

    # Resolve target modules (same logic as run_pipeline)
    if modules:
        target = [normalize_module_id(m) for m in modules]
    elif from_id is not None or to_id is not None:
        start = normalize_module_id(from_id or ids[0])
        end = normalize_module_id(to_id or ids[-1])
        if start not in ids or end not in ids or ids.index(start) > ids.index(end):
            raise RuntimeError("Invalid from/to module range.")
        target = ids[ids.index(start) : ids.index(end) + 1]
    else:
        target = ids

    run_ids = expand_dependencies(target, registry)
    levels = group_modules_by_level(run_ids, registry)

    # Check input files
    input_snapshot = collect_input_snapshot(cfg)
    missing_inputs = [k for k, v in input_snapshot.items() if not v["exists"]]

    # Estimate runtime based on module characteristics
    runtime_estimates = {
        "00": 0.1,
        "01": 2.0,
        "01b": 0.5,
        "02": 20.0,
        "02b": 0.5,
        "03": 1.5,
        "04": 3.0,
        "05": 2.0,
        "06": 2.0,
        "07": 2.0,
        "08": 3.0,
        "09": 1.0,
        "10": 5.0,
        "11": 2.0,
    }

    # Calculate sequential and parallel estimates
    sequential_time = sum(runtime_estimates.get(mid, 1.0) for mid in run_ids)
    parallel_time = sum(max(runtime_estimates.get(mid, 1.0) for mid in level) for level in levels)

    plan = {
        "modules_requested": target,
        "modules_to_run": run_ids,
        "execution_levels": levels,
        "level_count": len(levels),
        "max_parallelism": max(len(lvl) for lvl in levels),
        "input_status": {
            "total": len(input_snapshot),
            "available": len(input_snapshot) - len(missing_inputs),
            "missing": missing_inputs,
        },
        "time_estimate": {
            "sequential_sec": sequential_time,
            "parallel_sec": parallel_time,
            "speedup": sequential_time / parallel_time if parallel_time > 0 else 1.0,
        },
    }

    return plan


def print_dry_run_report(plan: dict):
    """Pretty-print dry-run execution plan."""
    print("\n=== PIPELINE DRY RUN ===\n")
    print(f"Modules requested: {plan['modules_requested']}")
    print(f"Modules to execute (with deps): {plan['modules_to_run']}")
    print(f"\nExecution plan: {plan['level_count']} levels")

    for i, level in enumerate(plan["execution_levels"]):
        parallel_note = f" [parallel: {len(level)} modules]" if len(level) > 1 else ""
        print(f"  Level {i + 1}: {level}{parallel_note}")

    print(f"\nInput files:")
    print(f"  Available: {plan['input_status']['available']}/{plan['input_status']['total']}")
    if plan["input_status"]["missing"]:
        print(f"  Missing: {plan['input_status']['missing']}")

    print(f"\nEstimated runtime:")
    print(f"  Sequential: {plan['time_estimate']['sequential_sec']:.1f}s")
    print(f"  Parallel: {plan['time_estimate']['parallel_sec']:.1f}s")
    print(f"  Speedup: {plan['time_estimate']['speedup']:.2f}x")
    print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Bhutan forest stratification pipeline")
    parser.add_argument("--modules", nargs="*", help="Specific module IDs to run, e.g., 01 02 03")
    parser.add_argument("--from", dest="from_id", help="Start module ID")
    parser.add_argument("--to", dest="to_id", help="End module ID")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview execution plan without running")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue executing independent modules even if some fail",
    )
    parser.add_argument(
        "--sequential", action="store_true", help="Force sequential execution (disable parallelism)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum parallel workers (default: auto-detect from CPU cores)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars (useful for logs/CI environments)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching and force full rebuild of all modules",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before running (forces fresh execution)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable detailed performance profiling (function-level timing)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    show_progress = not args.no_progress
    use_cache = not args.no_cache
    enable_profiling = args.profile

    # Clear cache if requested
    if args.clear_cache:
        clear_module_cache(config)
        print("Cache cleared")
        if not (args.modules or args.from_id or args.to_id):
            # If only clearing cache, exit
            import sys
            sys.exit(0)

    if args.dry_run:
        plan = dry_run_pipeline(modules=args.modules, from_id=args.from_id, to_id=args.to_id, cfg=config)
        print_dry_run_report(plan)
    elif args.sequential:
        # Note: Sequential mode doesn't currently support caching/profiling
        # Could be added in future if needed
        run_pipeline(
            modules=args.modules,
            from_id=args.from_id,
            to_id=args.to_id,
            cfg=config,
            log_level=args.log_level,
            show_progress=show_progress,
        )
    else:
        run_pipeline_parallel(
            modules=args.modules,
            from_id=args.from_id,
            to_id=args.to_id,
            cfg=config,
            log_level=args.log_level,
            max_workers=args.max_workers,
            continue_on_error=args.continue_on_error,
            show_progress=show_progress,
            use_cache=use_cache,
            enable_profiling=enable_profiling,
        )
