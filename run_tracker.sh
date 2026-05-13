#!/bin/bash
export BRIGHT_DATA_KEY=7fe773b11b190ba758a122c288438d14deef5356a694ef707a3c847de5af3b5c
export HEADLESS=true
exec python /mnt/c/Users/mario/.gemini/antigravity/tools/execution/keyword_rank_tracker.py "$@"
