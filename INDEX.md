# Amazon Business Intelligence - Project Index

## Overview

This document provides a quick reference to all components of the data warehouse layer, workflow orchestration system, and CLI interface.

## Files

### Data Layer

**`data/__init__.py`** (1 line)
- Exports: `DataWarehouse`
- Purpose: Module initialization

**`data/warehouse.py`** (143 lines, 6.5 KB)
- Class: `DataWarehouse`
- Purpose: Three-tier data warehouse management
- Storage Tiers:
  1. **Raw**: Original API responses
  2. **Processed**: Cleaned, structured data
  3. **Summaries**: Token-optimized LLM summaries
  4. **Snapshots**: Historical trending data

| Method | Purpose | Example |
|--------|---------|---------|
| `save_raw()` | Store raw API data | `warehouse.save_raw("brand", "ASIN", "listing", data)` |
| `load_raw()` | Retrieve raw data | `warehouse.load_raw("brand", "ASIN", "listing")` |
| `save_processed()` | Store processed data | `warehouse.save_processed("ppc", "analysis", data)` |
| `load_processed()` | Retrieve processed data | `warehouse.load_processed("ppc", "analysis")` |
| `load_latest_processed()` | Get most recent | `warehouse.load_latest_processed("ppc", "analysis")` |
| `save_summary()` | Store LLM summary | `warehouse.save_summary("ppc_summary", text)` |
| `load_summary()` | Retrieve summary | `warehouse.load_summary("ppc_summary")` |
| `load_all_summaries()` | Get all for date | `warehouse.load_all_summaries(date="20260302")` |
| `save_snapshot()` | Store snapshot | `warehouse.save_snapshot("daily", data)` |
| `load_snapshots()` | Get recent snapshots | `warehouse.load_snapshots("daily", limit=30)` |
| `list_dates()` | Enumerate data dates | `warehouse.list_dates("processed")` |

**`data/summary_generator.py`** (135 lines, 5.1 KB)
- Purpose: Token-optimized summary generation for LLM consumption
- Target: ≤2000 tokens (~8000 characters per summary)

| Function | Purpose | Use Case |
|----------|---------|----------|
| `generate_ppc_summary()` | PPC metrics & recommendations | Daily PPC analysis |
| `generate_competitor_summary()` | Competitor landscape | Market research |
| `generate_review_summary()` | Review intelligence | Product feedback |
| `generate_daily_snapshot_summary()` | Compact daily metrics | Trending analysis |

### Orchestration Layer

**`workflows/__init__.py`** (1 line)
- Exports: `WorkflowOrchestrator`
- Purpose: Module initialization

**`workflows/orchestrator.py`** (133 lines, 5.2 KB)
- Class: `WorkflowOrchestrator`
- Purpose: Workflow execution engine with YAML definitions

| Method | Purpose | Example |
|--------|---------|---------|
| `load_workflow()` | Load YAML workflow | `orch.load_workflow("daily_ppc_analysis")` |
| `list_workflows()` | List all workflows | `orch.list_workflows()` |
| `run_workflow()` | Execute workflow | `orch.run_workflow("daily_ppc_analysis")` |

Features:
- YAML-based workflow definitions
- Step-by-step execution tracking
- Dry-run mode for safe testing
- JSON execution logging
- Cron schedule support
- Post-action hooks (email, Slack, etc.)

### CLI Layer

**`cli/__init__.py`** (0 lines)
- Purpose: Module initialization

**`cli/main.py`** (154 lines, 4.8 KB)
- Function: `main()` - Command-line entry point
- Purpose: User interface for all operations

| Command | Purpose | Example |
|---------|---------|---------|
| `test-api` | Test API connections | `python cli/main.py test-api` |
| `pull-data` | Pull ASIN data | `python cli/main.py pull-data ASIN123 --days 31` |
| `list-workflows` | List workflows | `python cli/main.py list-workflows` |
| `run-workflow` | Execute workflow | `python cli/main.py run-workflow daily_analysis --dry-run` |
| `list-skills` | Discover skills | `python cli/main.py list-skills` |

### Testing Layer

**`tests/__init__.py`** (0 lines)
- Purpose: Module initialization

**`tests/conftest.py`** (13 lines, 329 bytes)
- Purpose: Pytest configuration and fixtures

| Fixture | Purpose | Usage |
|---------|---------|-------|
| `project_root` | Project root path | `def test_something(project_root):` |
| `data_warehouse` | Temporary warehouse | `def test_warehouse(data_warehouse):` |

### Documentation

**`STRUCTURE.md`**
- Comprehensive architecture documentation
- Component descriptions
- Integration points
- Best practices

**`QUICKSTART.md`**
- Quick start guide with code examples
- Common patterns
- Troubleshooting guide

**`INDEX.md`** (this file)
- Project overview
- Quick reference
- File locations

## Data Flow

```
1. API Collection
   └─> API responses (raw data)

2. Raw Storage
   └─> warehouse.save_raw()
   └─> raw/{brand}/{asin}/{type}_{date}.json

3. Processing (Skills)
   └─> Load raw data
   └─> Transform and analyze
   └─> warehouse.save_processed()

4. Processed Storage
   └─> processed/{category}/{name}_{date}.json

5. Summary Generation
   └─> generate_*_summary()
   └─> warehouse.save_summary()

6. Summary Storage
   └─> summaries/{name}_{date}.txt

7. LLM Analysis
   └─> Load summaries
   └─> Feed to language models
   └─> Generate insights
```

## Storage Locations

| Type | Pattern | Example |
|------|---------|---------|
| Raw | `raw/{brand}/{asin}/{type}_{date}.json` | `raw/zoviro/B0ABCDEF1/ppc_report_2026-03-02.json` |
| Processed | `processed/{category}/{name}_{date}.json` | `processed/ppc/campaign_analysis_2026-03-02.json` |
| Summaries | `summaries/{name}_{date}.txt` | `summaries/ppc_performance_B0ABCDEF1_20260302.txt` |
| Snapshots | `snapshots/snapshot_{type}_{date}.json` | `snapshots/snapshot_daily_2026-03-02.json` |
| Logs | `workflows/execution_logs/{id}_{ts}.json` | `workflows/execution_logs/daily_ppc_20260302_091530.json` |

Date Formats:
- **Raw/Processed/Snapshots**: `YYYY-MM-DD` (2026-03-02)
- **Summaries**: `YYYYMMDD` (20260302)
- **Logs**: `YYYYMMDD_HHMMSS` (20260302_091530)

## Integration Points

### With API Layer
- CLI `pull-data` command fetches from SP API and Ads API
- Results stored in `raw/` tier via DataWarehouse
- Automatic date-stamping for organization

### With Skills Framework
- Skills read from `raw/` and `processed/` directories
- Process and transform data
- Save results to `processed/` tier
- Can trigger summary generation

### With LLM Analysis
- Load summaries via DataWarehouse
- Token-optimized format (≤2000 tokens)
- Feed to language models for insights
- Use for decision making and recommendations

### With Workflow System
- Orchestrate multi-step processes
- Chain skills together
- Log execution for audit trail
- Support scheduled automation

## Quick Commands

```bash
# Test setup
python cli/main.py test-api

# Pull product data
python cli/main.py pull-data B0ABCDEF1 --competitors B0BCDEFGH,B0CDEFGHI

# List workflows
python cli/main.py list-workflows

# Try workflow (dry run)
python cli/main.py run-workflow daily_ppc_analysis --dry-run

# Execute workflow
python cli/main.py run-workflow daily_ppc_analysis

# List skills
python cli/main.py list-skills

# Run tests
pytest tests/
pytest -v tests/test_warehouse.py
pytest --cov=data tests/
```

## Python Quick Reference

```python
# Import main classes
from data.warehouse import DataWarehouse
from data.summary_generator import generate_ppc_summary
from workflows.orchestrator import WorkflowOrchestrator

# Initialize warehouse
warehouse = DataWarehouse("./data")

# Save and load data
warehouse.save_raw("brand", "ASIN", "type", data, date="2026-03-02")
warehouse.save_processed("category", "name", data, date="2026-03-02")
warehouse.save_summary("name", text, date="20260302")
warehouse.save_snapshot("type", data, date="2026-03-02")

# Load data
raw = warehouse.load_raw("brand", "ASIN", "type", date="2026-03-02")
processed = warehouse.load_processed("category", "name", date="2026-03-02")
summaries = warehouse.load_all_summaries(date="20260302")
snapshots = warehouse.load_snapshots("type", limit=30)

# Generate summaries
summary = generate_ppc_summary(ppc_data, "Product", "ASIN")
warehouse.save_summary("ppc_summary", summary)

# Execute workflows
orch = WorkflowOrchestrator("./config", "./data", "./reports")
result = orch.run_workflow("workflow_id", dry_run=True)
workflows = orch.list_workflows()
```

## File Locations

All files located in:
```
/sessions/optimistic-friendly-johnson/mnt/Amazon Workflows/amazon-business-intelligence/
```

Key directories:
- `data/` - Data warehouse layer
- `workflows/` - Workflow orchestration
- `cli/` - Command-line interface
- `tests/` - Test fixtures and configuration
- Documentation: `STRUCTURE.md`, `QUICKSTART.md`, `INDEX.md`

## Next Steps

1. **Setup**: Review `QUICKSTART.md` for examples
2. **Integrate**: Connect with existing API layer
3. **Test**: Run pytest fixtures to verify
4. **Deploy**: Use CLI for automated operations
5. **Monitor**: Check execution logs in `workflows/execution_logs/`

## Support

For detailed information:
- Architecture: See `STRUCTURE.md`
- Examples: See `QUICKSTART.md`
- API Reference: See docstrings in source files
- Testing: See `tests/conftest.py`
