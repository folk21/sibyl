"""Public source-ingestion API.

This is the feature boundary for everything from external catalogs/artifacts to the prepared
canonical source set consumed by automatic build and LLM curation:

    discover -> review -> acquire/import -> normalize/cache -> prepare -> optional register

Callers should use this module instead of importing ``sources._internal`` or concrete adapters.
"""

from ._internal.acquisition import acquire_selection, fetch_registry_source, import_registry_source
from ._internal.discovery import discover_to_file
from ._internal.preparation import prepare_registry_sources, prepare_selection_sources
from ._internal.registration import register_selection
from ._internal.reports import AcquisitionReport
from ._internal.selection import load_selection, write_selection
from .models import SelectionManifest, SelectionWork

__all__ = [
    "AcquisitionReport",
    "SelectionManifest",
    "SelectionWork",
    "acquire_selection",
    "discover_to_file",
    "fetch_registry_source",
    "import_registry_source",
    "load_selection",
    "prepare_registry_sources",
    "prepare_selection_sources",
    "register_selection",
    "write_selection",
]
