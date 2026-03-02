# Amazon Business Intelligence - Data Layer Structure

This document outlines the newly created data warehouse, workflow orchestration, and CLI components.

## Directory Structure

```
amazon-business-intelligence/
├── data/
│   ├── __init__.py                 # Exports DataWarehouse
│   ├── warehouse.py                # Three-tier data warehouse abstraction
│   └── summary_generator.py        # Token-optimized summary generation
│
├── workflows/
│   ├── __init__.py                 # Exports WorkflowOrchestrator
│   └── orchestrator.py             # Workflow execution engine
│
├── cli/
│   ├── __init__.py                 # Empty
│   └── main.py                     # CLI entry point
│
└── tests/
    ├── __init__.py                 # Empty
    └── conftest.py                 # Pytest fixtures
```

## Components

### 1. Data Warehouse (`data/warehouse.py`)

**Purpose:** Manages three-tier data storage with automatic path resolution and date-stamping.

**Features:**
- Raw data storage: `raw/{brand}/{asin}/{data_type}_{date}.json`
- Processed data storage: `processed/{category}/{name}_{date}.json`
- Summary storage: `summaries/{name}_{date}.txt` (token-optimized for LLM consumption)
- Snapshot storage: `snapshots/snapshot_{type}_{date}.json`

**Key Methods:**
- `save_raw()` / `load_raw()` - Store/retrieve raw API data
- `save_processed()` / `load_processed()` - Store/retrieve processed data
- `load_latest_processed()` - Get most recent data matching prefix
- `save_summary()` / `load_summary()` - Store/retrieve text summaries
- `load_all_summaries()` - Load all summaries for a date
- `save_snapshot()` / `load_snapshots()` - Store/retrieve trending snapshots
- `list_dates()` - Enumerate available data dates

**Example Usage:**
```python
from data.warehouse import DataWarehouse

warehouse = DataWarehouse("/path/to/data")
warehouse.save_raw("brand", "ASIN123", "product_listing", {"data": "..."})
data = warehouse.load_raw("brand", "ASIN123", "product_listing")
```

### 2. Summary Generator (`data/summary_generator.py`)

**Purpose:** Creates token-optimized text summaries from processed data for LLM consumption.

**Target:** Each summary ≤2000 tokens (~8000 characters)

**Functions:**
- `generate_ppc_summary()` - PPC performance metrics and recommendations
- `generate_competitor_summary()` - Competitor landscape analysis
- `generate_review_summary()` - Review intelligence and themes
- `generate_daily_snapshot_summary()` - Compact daily metrics

**Example Usage:**
```python
from data.summary_generator import generate_ppc_summary

ppc_data = {...}  # processed data
summary_text = generate_ppc_summary(ppc_data, "Product Name", "ASIN123")
warehouse.save_summary("ppc_performance_ASIN123", summary_text)
```

### 3. Workflow Orchestrator (`workflows/orchestrator.py`)

**Purpose:** Runs scheduled or manual workflows that chain skills together.

**Features:**
- Load workflows from YAML definitions
- List available workflows
- Execute workflows with step-by-step tracking
- Dry-run mode for testing
- Execution logging with JSON reports

**Key Methods:**
- `load_workflow(workflow_id)` - Load YAML workflow definition
- `list_workflows()` - List all available workflows
- `run_workflow(workflow_id, dry_run=False)` - Execute workflow with logging

**Workflow Definition Structure:**
```yaml
workflow:
  id: workflow_id
  description: "Human-readable description"
  schedule: "0 9 * * *"  # Cron format (optional)
  enabled: true
  steps:
    - skill: skill_name
      action: action_name
      params: {}
  post_actions:
    - type: email
      recipients: [...]
```

**Example Usage:**
```python
from workflows.orchestrator import WorkflowOrchestrator

orch = WorkflowOrchestrator(
    config_dir="/path/to/config",
    data_dir="/path/to/data",
    reports_dir="/path/to/reports"
)
result = orch.run_workflow("daily_ppc_analysis")
```

### 4. CLI Interface (`cli/main.py`)

**Purpose:** Command-line interface for all platform operations.

**Commands:**

#### `test-api`
Test API connections (SP API and Ads API).
```bash
python cli/main.py test-api [--env-file .env]
```

#### `pull-data`
Pull all data for a given ASIN.
```bash
python cli/main.py pull-data ASIN123 \
  [--competitors ASIN456,ASIN789] \
  [--days 31] \
  [--output-dir ./data/raw/brand/ASIN123]
```

#### `list-workflows`
List all available workflows.
```bash
python cli/main.py list-workflows
```

#### `run-workflow`
Run a specific workflow.
```bash
python cli/main.py run-workflow workflow_id [--dry-run]
```

#### `list-skills`
List all available skills.
```bash
python cli/main.py list-skills
```

### 5. Test Configuration (`tests/conftest.py`)

**Purpose:** Pytest fixtures for testing.

**Fixtures:**
- `project_root` - Path to project root
- `data_warehouse` - Temporary DataWarehouse instance for testing

**Example Test:**
```python
def test_warehouse(data_warehouse):
    path = data_warehouse.save_raw("test_brand", "TEST123", "listing", {"key": "value"})
    assert path.exists()
    data = data_warehouse.load_raw("test_brand", "TEST123", "listing")
    assert data["key"] == "value"
```

## Data Flow Architecture

```
API Data (Raw)
    ↓
[DataWarehouse.save_raw()]
    ↓
raw/{brand}/{asin}/data_type_{date}.json
    ↓
[Processing Skill]
    ↓
[DataWarehouse.save_processed()]
    ↓
processed/{category}/name_{date}.json
    ↓
[Summary Generator]
    ↓
[DataWarehouse.save_summary()]
    ↓
summaries/name_{date}.txt
    ↓
[LLM Analysis]
```

## Storage Capacity

- **Raw Layer:** Full API responses (JSON)
- **Processed Layer:** Cleaned, structured data (JSON)
- **Summaries Layer:** Text summaries optimized for LLMs (TXT, ≤8000 chars)
- **Snapshots Layer:** Historical snapshots for trending (JSON)

## Integration Points

### With Skills
- Skills read from `processed/` and `raw/` directories
- Skills write results to `processed/`
- Skills can trigger summary generation

### With Workflows
- Workflows coordinate skill execution
- Workflows can write execution logs
- Post-actions (emails, notifications, etc.)

### With CLI
- CLI uses DataWarehouse for file management
- CLI triggers WorkflowOrchestrator for automation
- CLI can test API connections and pull data

## Best Practices

1. **Always use date parameters** for reproducibility
2. **Save to appropriate tier** (raw for API, processed for analysis)
3. **Keep summaries concise** (≤2000 tokens)
4. **Use dry-run mode** before running workflows
5. **Monitor execution logs** for troubleshooting
