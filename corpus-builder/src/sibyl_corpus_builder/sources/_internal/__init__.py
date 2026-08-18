"""Private implementation of the source-ingestion feature.

This package contains source-specific orchestration behind ``sources.api``:
selection/registry persistence, adapter dispatch, acquisition, artifact cache,
reports, preparation, and registration. Other features consume only the
prepared canonical-source boundary and must not import these internals."""
