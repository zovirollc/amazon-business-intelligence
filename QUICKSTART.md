# Quick Start Guide

## Data Warehouse Examples

### Basic Usage

```python
from data.warehouse import DataWarehouse

# Initialize warehouse
warehouse = DataWarehouse("./data")

# Save raw API data
warehouse.save_raw(
    brand="zoviro",
    asin="B0ABCDEF1",
    data_type="product_listing",
    data={"title": "Product Name", "price": 29.99},
    date="2026-03-02"
)

# Load raw data
raw_data = warehouse.load_raw("zoviro", "B0ABCDEF1", "product_listing", date="2026-03-02")
print(raw_data)  # {"title": "Product Name", "price": 29.99}

# Save processed data
warehouse.save_processed(
    category="ppc",
    name="campaign_analysis",
    data={"total_spend": 150.50, "sales": 2000.00, "acos": 7.5},
    date="2026-03-02"
)

# Load processed data
processed = warehouse.load_processed("ppc", "campaign_analysis", date="2026-03-02")

# Get latest processed data (ignoring date)
latest = warehouse.load_latest_processed("ppc", "campaign_analysis")
```

### Summaries for LLMs

```python
from data.warehouse import DataWarehouse
from data.summary_generator import generate_ppc_summary

warehouse = DataWarehouse("./data")

# Generate token-optimized summary
ppc_data = {
    "period": "2026-02-01 to 2026-03-01",
    "total_spend": 1500.50,
    "total_sales": 15000.00,
    "overall_acos": 10.0,
    "target_acos": 8.0,
    "roas": 10.0,
    "total_unique_terms": 250,
    "classification": {"branded": 50, "competitor": 100, "generic": 100},
    "top_winners": [
        {"keyword": "best product for x", "sales": 500, "acos": 5.0},
        {"keyword": "product review", "sales": 450, "acos": 6.2},
    ],
    "negative_candidates": [
        {"keyword": "cheap knockoff", "spend": 25.00},
        {"keyword": "broken product", "spend": 15.00},
    ],
    "actions": [
        "Add 'cheap knockoff' to negatives",
        "Increase bid for 'best product for x'",
        "Create new branded campaign",
    ]
}

summary = generate_ppc_summary(ppc_data, "Zoviro Water Bottle", "B0ABCDEF1")
print(summary)  # ≤8000 chars, formatted for LLM
warehouse.save_summary("ppc_analysis_B0ABCDEF1", summary)
```

### Snapshots for Trending

```python
from data.warehouse import DataWarehouse

warehouse = DataWarehouse("./data")

# Save daily snapshot
snapshot = {
    "date": "2026-03-02",
    "products": {
        "B0ABCDEF1": {
            "sales": 250.00,
            "spend": 25.00,
            "acos": 10.0,
            "bsr": 1234
        },
        "B0BCDEFGH": {
            "sales": 180.00,
            "spend": 20.00,
            "acos": 11.1,
            "bsr": 2345
        }
    }
}

warehouse.save_snapshot("daily", snapshot, date="2026-03-02")

# Load recent snapshots for trending
recent = warehouse.load_snapshots("daily", limit=30)
for snapshot in recent:
    print(f"Date: {snapshot['date']}, Products: {len(snapshot['products'])}")

# List available dates
dates = warehouse.list_dates(category="processed")
print(f"Available data: {dates}")  # ['2026-03-02', '2026-03-01', ...]
```

## Workflow Orchestration Examples

### List Available Workflows

```python
from workflows.orchestrator import WorkflowOrchestrator

orch = WorkflowOrchestrator(
    config_dir="./config",
    data_dir="./data",
    reports_dir="./reports"
)

workflows = orch.list_workflows()
for wf in workflows:
    status = "enabled" if wf['enabled'] else "disabled"
    print(f"{wf['id']}: {wf['description']} ({status})")
```

### Execute a Workflow

```python
from workflows.orchestrator import WorkflowOrchestrator

orch = WorkflowOrchestrator(
    config_dir="./config",
    data_dir="./data",
    reports_dir="./reports"
)

# Dry run first
result = orch.run_workflow("daily_ppc_analysis", dry_run=True)
print(f"Dry run: {len(result['steps'])} steps would execute")

# Then run for real
result = orch.run_workflow("daily_ppc_analysis")
print(f"Completed: {result['status']}")
for step in result['steps']:
    print(f"  Step {step['step']}: {step['skill']}.{step['action']} - {step['status']}")
```

### Workflow YAML Definition

```yaml
workflow:
  id: daily_ppc_analysis
  description: "Daily PPC performance analysis and optimization recommendations"
  schedule: "0 9 * * *"  # Run at 9 AM daily
  enabled: true
  
  steps:
    - skill: ppc-optimization
      action: pull_data
      params:
        days_back: 7
    
    - skill: ppc-optimization
      action: analyze_performance
      params:
        min_spend: 10
        target_acos: 8.0
    
    - skill: ppc-optimization
      action: generate_report
      params:
        format: xlsx
  
  post_actions:
    - type: email
      recipients: ["seller@example.com"]
      subject: "PPC Daily Report"
    - type: slack
      webhook_url: "${SLACK_WEBHOOK_URL}"
      channel: "#ppc-alerts"
```

## CLI Examples

### Test API Connections

```bash
# Test with default .env
python cli/main.py test-api

# Test with custom .env
python cli/main.py test-api --env-file /path/to/.env
```

### Pull Data for Product

```bash
# Basic pull for one ASIN
python cli/main.py pull-data B0ABCDEF1

# With competitors
python cli/main.py pull-data B0ABCDEF1 \
  --competitors B0BCDEFGH,B0CDEFGHI

# Custom output directory
python cli/main.py pull-data B0ABCDEF1 \
  --output-dir ./data/raw/custom/B0ABCDEF1

# 60 days history
python cli/main.py pull-data B0ABCDEF1 --days 60
```

### List and Run Workflows

```bash
# List all workflows
python cli/main.py list-workflows

# Dry run workflow
python cli/main.py run-workflow daily_ppc_analysis --dry-run

# Execute workflow
python cli/main.py run-workflow daily_ppc_analysis

# List available skills
python cli/main.py list-skills
```

## Testing Examples

### Pytest with Fixtures

```python
# tests/test_warehouse.py
from pathlib import Path

def test_save_and_load_raw(data_warehouse):
    """Test raw data save/load cycle."""
    test_data = {"key": "value", "number": 42}
    
    # Save
    path = data_warehouse.save_raw(
        "test_brand",
        "TEST123",
        "listing",
        test_data,
        date="2026-03-02"
    )
    assert path.exists()
    
    # Load
    loaded = data_warehouse.load_raw(
        "test_brand",
        "TEST123",
        "listing",
        date="2026-03-02"
    )
    assert loaded == test_data


def test_processed_data(data_warehouse):
    """Test processed data operations."""
    test_data = {"metric1": 100, "metric2": 200}
    
    # Save
    path = data_warehouse.save_processed(
        "analysis",
        "metrics",
        test_data
    )
    assert path.exists()
    
    # Load latest
    loaded = data_warehouse.load_latest_processed("analysis", "metrics")
    assert loaded == test_data


def test_summaries(data_warehouse):
    """Test summary operations."""
    summary_text = "This is a test summary\n" * 100
    
    # Save
    path = data_warehouse.save_summary("test_summary", summary_text)
    assert path.exists()
    
    # Load
    loaded = data_warehouse.load_summary("test_summary")
    assert loaded == summary_text
    
    # Load all
    all_summaries = data_warehouse.load_all_summaries()
    assert "test_summary" in all_summaries
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_warehouse.py::test_save_and_load_raw

# Verbose output
pytest -v tests/

# With coverage
pytest --cov=data tests/
```

## Integration Workflow

1. **Data Collection** → Use DataWarehouse to save raw API data
2. **Processing** → Skills read raw data, save to processed
3. **Summary Generation** → Create token-optimized LLM summaries
4. **Analysis** → LLM analyzes summaries for insights
5. **Automation** → WorkflowOrchestrator chains steps together
6. **CLI Control** → Use CLI for manual triggers and monitoring

## Common Patterns

### Process New Data

```python
from data.warehouse import DataWarehouse
from data.summary_generator import generate_ppc_summary

warehouse = DataWarehouse("./data")

# 1. Load raw data
raw = warehouse.load_raw("zoviro", "B0ABCDEF1", "ppc_report")

# 2. Process (in skill)
processed = {
    "total_spend": sum(row['spend'] for row in raw['rows']),
    "total_sales": sum(row['sales'] for row in raw['rows']),
    # ... more processing
}

# 3. Save processed
warehouse.save_processed("ppc", "campaign_B0ABCDEF1", processed)

# 4. Generate summary
summary = generate_ppc_summary(processed, "Product Name", "B0ABCDEF1")
warehouse.save_summary("ppc_B0ABCDEF1", summary)
```

### Monitor Trends

```python
warehouse = DataWarehouse("./data")

# Load snapshots
snapshots = warehouse.load_snapshots("daily", limit=30)

# Analyze trend
sales_trend = [s['products']['B0ABCDEF1']['sales'] for s in snapshots]
avg_sales = sum(sales_trend) / len(sales_trend)
print(f"Average daily sales: ${avg_sales:.2f}")
```

## Troubleshooting

### File Not Found

```python
# Check what dates have data
dates = warehouse.list_dates("raw")
print(f"Available: {dates}")

# Use correct date format
# Raw data: YYYY-MM-DD (2026-03-02)
# Summaries: YYYYMMDD (20260302)
```

### Workflow Execution Failed

1. Check execution logs: `workflows/execution_logs/`
2. Try dry-run first: `--dry-run`
3. Verify workflow YAML syntax
4. Check skill dependencies exist

### Import Errors

```python
# Make sure PROJECT_ROOT is in sys.path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.warehouse import DataWarehouse
```
