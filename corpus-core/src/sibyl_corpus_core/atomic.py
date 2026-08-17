"""Small atomic-publication helpers for deterministic local build artifacts."""

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def staging_directory(output_dir: Path) -> Iterator[Path]:
    """Yields a clean sibling staging directory and atomically publishes on success.

    The caller writes a complete directory tree to the yielded path. Any failure removes
    staging and leaves the previous published directory untouched. On success the previous
    output is replaced by the completed staging directory.
    """
    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = output_dir.with_name(f".{output_dir.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        yield staging
        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging.rename(output_dir)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
