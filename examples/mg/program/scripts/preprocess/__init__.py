"""Preprocess-stage adapter.

The original MG common preprocess remains the owner of generating model-facing
SQLite tables. This package only validates that those tables are present before
the OptAgent model phase runs.
"""

