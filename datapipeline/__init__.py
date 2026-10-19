"""UniGuide Uganda data-processing pipeline.

Read-only on the original `data/` directory: every stage receives copies and
writes derived datasets into `data/processed/<timestamp>/`.

Run with:  python -m datapipeline.pipeline
"""
