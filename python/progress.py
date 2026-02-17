"""Progress bar and visual feedback utilities for pipeline execution."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class PipelineProgressBar:
    """
    Manages progress bars for pipeline execution.

    Shows:
    - Overall pipeline progress (modules completed)
    - Current module being executed
    - Time estimates
    """

    def __init__(self, total_modules: int, show_progress: bool = True):
        """
        Initialize progress bar manager.

        Args:
            total_modules: Total number of modules to execute
            show_progress: Whether to show progress bars (disable for logs/CI)
        """
        self.total_modules = total_modules
        self.show_progress = show_progress and TQDM_AVAILABLE and sys.stderr.isatty()
        self.main_bar = None
        self.current_module = None
        self.completed = 0

    def start(self, description: str = "Pipeline Progress"):
        """Start the main progress bar."""
        if self.show_progress:
            self.main_bar = tqdm(
                total=self.total_modules,
                desc=description,
                unit="module",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
                position=0,
                leave=True,
            )

    def update_module(self, module_id: str, module_name: str, status: str = "running"):
        """
        Update progress with current module information.

        Args:
            module_id: Module identifier (e.g., "03")
            module_name: Module name (e.g., "alpha_diversity")
            status: Current status ("running", "completed", "failed")
        """
        if self.show_progress and self.main_bar:
            status_icon = {
                "running": "⚙️",
                "completed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(status, "▶️")

            self.main_bar.set_postfix_str(f"{status_icon} {module_id}: {module_name}")

    def complete_module(self, success: bool = True):
        """Mark current module as complete and update progress."""
        if self.show_progress and self.main_bar:
            self.completed += 1
            self.main_bar.update(1)

    def finish(self, success: bool = True):
        """Finish and close the progress bar."""
        if self.show_progress and self.main_bar:
            if success:
                self.main_bar.set_postfix_str("✅ Complete")
            else:
                self.main_bar.set_postfix_str("⚠️ Completed with errors")
            self.main_bar.close()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.finish(success=(exc_type is None))
        return False  # Don't suppress exceptions


@contextmanager
def module_progress(module_id: str, module_name: str, show: bool = True) -> Iterator[None]:
    """
    Context manager for showing progress during module execution.

    Example:
        with module_progress("03", "alpha_diversity"):
            # Module execution here
            pass
    """
    if show and TQDM_AVAILABLE and sys.stderr.isatty():
        with tqdm(
            total=100,
            desc=f"Module {module_id}: {module_name}",
            unit="%",
            bar_format='{desc}: {percentage:3.0f}%|{bar}| [{elapsed}]',
            position=1,
            leave=False,
        ) as pbar:
            # Simulate indeterminate progress
            pbar.update(10)  # Start
            yield
            pbar.update(90)  # Complete
    else:
        yield


class SimpleProgress:
    """Fallback progress indicator when tqdm is not available."""

    def __init__(self, total: int):
        self.total = total
        self.current = 0

    def update(self, module_id: str, module_name: str):
        """Print simple text progress."""
        self.current += 1
        percent = (self.current / self.total) * 100
        print(f"[{self.current}/{self.total} - {percent:.0f}%] Module {module_id}: {module_name}",
              file=sys.stderr, flush=True)

    def finish(self):
        """Print completion message."""
        print(f"✅ Pipeline complete: {self.current}/{self.total} modules", file=sys.stderr)


def create_progress_bar(total_modules: int, show_progress: bool = True, use_simple: bool = False):
    """
    Factory function to create appropriate progress bar.

    Args:
        total_modules: Total number of modules
        show_progress: Whether to show progress
        use_simple: Force simple text progress (no tqdm)

    Returns:
        Progress bar instance (PipelineProgressBar or SimpleProgress)
    """
    if not show_progress:
        return None

    if use_simple or not TQDM_AVAILABLE:
        return SimpleProgress(total_modules)

    return PipelineProgressBar(total_modules, show_progress=True)
