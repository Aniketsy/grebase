# Architecture

## Overview
Grebase is a Python CLI that orchestrates Git rebase workflows and applies safe, rule-based conflict resolutions.

## Core Modules
- cli: command parsing and workflow orchestration
- git_ops: subprocess wrapper around Git
- conflict_parser: parses conflict markers into segments
- conflict_classifier: classifies conflicts by type
- conflict_resolver: applies deterministic rules
- rules: low-level merge heuristics
- lockfile_tools: regenerates lockfiles via package managers

## Data Flow
1. cli validates repo and detects target
2. git_ops starts rebase
3. conflict_detector finds conflicts
4. parser and classifier analyze files
5. resolver applies safe rules
6. git_ops stages files and continues
