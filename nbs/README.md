# Notebook Execution Order

This directory contains numbered notebooks reflecting the logical execution and information flow of the Alma TV system.

## Order & Purpose

1. **`01_config.ipynb`** - Configuration system
   - Load settings from `config.yaml`
   - Environment variable overrides
   - Keyword mappings

2. **`02_library_scanner.ipynb`** - Media library scanning
   - Scan media directories
   - Parse filenames
   - Populate database

3. **`03_library_service.ipynb`** - Library queries
   - List series and episodes
   - Random selection
   - Statistics and caching

4. **`04_scheduler_parser.ipynb`** - Request parsing
   - Natural language → structured requests
   - Keyword mapping
   - Date parsing

5. **`05_scheduler_weights.ipynb`** - Weight calculation
   - Baseline weights
   - Feedback bonuses
   - Time decay
   - "Never again" exclusion

6. **`06_scheduler_lineup.ipynb`** - Lineup generation
   - Weighted episode selection
   - Runtime enforcement
   - Diversity constraints
   - Request fulfillment

7. **`07_scheduler_cli.ipynb`** - CLI usage
   - Command-line interface
   - Natural language requests
   - JSON output

## Other Files

- **`index.ipynb`** - Main entry point / overview
- **`nbdev_notebook_template.ipynb`** - Template for new notebooks
