"""Performance monitoring and progress utilities."""

from __future__ import annotations

import functools
import json
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class ResourceMonitor:
    """Track CPU and memory usage for a process."""

    def __init__(self):
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
        else:
            self.process = None
        self.start_time = None
        self.start_memory = None
        self.peak_memory = 0

    def start(self):
        """Begin monitoring."""
        self.start_time = time.time()
        if self.process:
            self.start_memory = self.process.memory_info().rss
            self.peak_memory = self.start_memory
        else:
            self.start_memory = 0
            self.peak_memory = 0

    def update(self):
        """Update peak memory."""
        if self.process:
            current_memory = self.process.memory_info().rss
            self.peak_memory = max(self.peak_memory, current_memory)

    def report(self) -> dict[str, Any]:
        """Get resource usage report."""
        self.update()
        elapsed = time.time() - self.start_time if self.start_time else 0
        memory_delta = self.peak_memory - self.start_memory if self.start_memory else 0

        cpu_percent = 0.0
        if self.process:
            try:
                cpu_percent = self.process.cpu_percent(interval=0.1)
            except Exception:
                cpu_percent = 0.0

        return {
            "elapsed_sec": round(elapsed, 2),
            "peak_memory_mb": round(self.peak_memory / (1024 * 1024), 2),
            "memory_delta_mb": round(memory_delta / (1024 * 1024), 2),
            "cpu_percent": round(cpu_percent, 1),
        }


@contextmanager
def track_resources(module_id: str, logger=None) -> Iterator[ResourceMonitor]:
    """Context manager for tracking module resource usage."""
    monitor = ResourceMonitor()
    monitor.start()

    try:
        yield monitor
    finally:
        report = monitor.report()
        if logger:
            logger.debug(
                f"Module {module_id} resources: "
                f"time={report['elapsed_sec']:.1f}s, "
                f"peak_mem={report['peak_memory_mb']:.1f}MB, "
                f"cpu={report['cpu_percent']:.1f}%"
            )


def progress_bar(iterable, desc: str = "", total: int = None, disable: bool = False):
    """Wrapper for tqdm progress bar with fallback."""
    if TQDM_AVAILABLE and not disable:
        return tqdm(iterable, desc=desc, total=total)
    return iterable


# ============================================================================
# Performance Profiling
# ============================================================================


class FunctionProfiler:
    """Profile function execution times within modules."""

    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.active = False

    def start(self):
        """Enable profiling."""
        self.active = True
        self.timings.clear()
        self.call_counts.clear()

    def stop(self):
        """Disable profiling."""
        self.active = False

    def record(self, function_name: str, elapsed_sec: float):
        """Record a function execution time."""
        if self.active:
            self.timings[function_name].append(elapsed_sec)
            self.call_counts[function_name] += 1

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get profiling statistics."""
        stats = {}
        for func_name, times in self.timings.items():
            total_time = sum(times)
            stats[func_name] = {
                "calls": self.call_counts[func_name],
                "total_sec": round(total_time, 4),
                "mean_sec": round(total_time / len(times), 4),
                "min_sec": round(min(times), 4),
                "max_sec": round(max(times), 4),
            }
        return stats


# Global profiler instance (used by decorator)
_global_profiler = FunctionProfiler()


def profile_function(func: Callable) -> Callable:
    """
    Decorator to profile function execution time.

    Usage:
        @profile_function
        def my_function():
            ...

    Function times are recorded in the global profiler when active.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - t0
            func_name = f"{func.__module__}.{func.__qualname__}"
            _global_profiler.record(func_name, elapsed)

    return wrapper


@contextmanager
def profile_module(module_id: str) -> Iterator[FunctionProfiler]:
    """
    Context manager for profiling a module.

    Usage:
        with profile_module("03") as profiler:
            # Run module code
            pass
        stats = profiler.get_stats()
    """
    profiler = _global_profiler
    profiler.start()

    try:
        yield profiler
    finally:
        profiler.stop()


def write_profile_report(module_id: str, stats: Dict[str, Dict[str, Any]], output_dir: Path) -> Path:
    """
    Write profiling report to disk.

    Args:
        module_id: Module identifier
        stats: Profiling statistics from profiler.get_stats()
        output_dir: Directory to write report

    Returns:
        Path to written report file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_file = output_dir / f"profile_{module_id}.json"

    # Sort by total time descending
    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1]["total_sec"], reverse=True))

    report = {
        "module_id": module_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "function_stats": sorted_stats,
        "summary": {
            "total_functions": len(stats),
            "total_time_sec": round(sum(s["total_sec"] for s in stats.values()), 2),
            "total_calls": sum(s["calls"] for s in stats.values()),
        },
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    return report_file


def identify_bottlenecks(
    stats: Dict[str, Dict[str, Any]], threshold_percent: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Identify performance bottlenecks from profiling data.

    Args:
        stats: Profiling statistics
        threshold_percent: Functions taking more than this % of total time are bottlenecks

    Returns:
        List of bottleneck entries with details
    """
    if not stats:
        return []

    total_time = sum(s["total_sec"] for s in stats.values())
    if total_time == 0:
        return []

    bottlenecks = []
    for func_name, func_stats in stats.items():
        percent = (func_stats["total_sec"] / total_time) * 100
        if percent >= threshold_percent:
            bottlenecks.append(
                {
                    "function": func_name,
                    "total_sec": func_stats["total_sec"],
                    "percent": round(percent, 1),
                    "calls": func_stats["calls"],
                    "mean_sec": func_stats["mean_sec"],
                }
            )

    # Sort by percent descending
    bottlenecks.sort(key=lambda x: x["percent"], reverse=True)
    return bottlenecks


def format_profile_summary(stats: Dict[str, Dict[str, Any]], top_n: int = 10) -> str:
    """
    Format profiling statistics as human-readable summary.

    Args:
        stats: Profiling statistics
        top_n: Number of top functions to include

    Returns:
        Formatted summary string
    """
    if not stats:
        return "No profiling data available"

    total_time = sum(s["total_sec"] for s in stats.values())
    total_calls = sum(s["calls"] for s in stats.values())

    lines = [
        "Performance Profile Summary",
        "=" * 60,
        f"Total functions: {len(stats)}",
        f"Total time: {total_time:.2f}s",
        f"Total calls: {total_calls}",
        "",
        f"Top {top_n} functions by time:",
        "-" * 60,
    ]

    # Sort by total time
    sorted_funcs = sorted(stats.items(), key=lambda x: x[1]["total_sec"], reverse=True)

    for i, (func_name, func_stats) in enumerate(sorted_funcs[:top_n], 1):
        percent = (func_stats["total_sec"] / total_time * 100) if total_time > 0 else 0
        # Shorten function name if too long
        display_name = func_name if len(func_name) <= 50 else "..." + func_name[-47:]
        lines.append(
            f"{i:2d}. {display_name:50s} {func_stats['total_sec']:7.2f}s ({percent:5.1f}%) "
            f"[{func_stats['calls']} calls, {func_stats['mean_sec']:.3f}s avg]"
        )

    return "\n".join(lines)
