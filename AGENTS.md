# AGENTS.md

## Purpose

This repository contains public, runnable OptAgent examples.

## Rules

- Keep examples self-contained and public.
- Add or update a README for each example area.
- Include dependency installation and run commands for each new example.
- Keep test data small and reproducible.
- Do not commit private business data, credentials, internal-only paths, or local cache files.
- Run the relevant pytest tests before claiming an example works.

## Relationship To optagent

The private `optagent` repository owns the core package, internal architecture,
implementation records, and core tests. This repository owns runnable examples,
example-specific tests, and example experiment scripts.
