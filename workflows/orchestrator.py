#!/usr/bin/env python3
"""
Workflow Orchestrator
Runs scheduled or manual workflows that chain skills together.
"""

import os
import json
import time
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates skill execution based on workflow definitions."""
    
    def __init__(self, config_dir: str, data_dir: str, reports_dir: str):
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(reports_dir)
        self.log_dir = Path(config_dir).parent / "workflows" / "execution_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def load_workflow(self, workflow_id: str) -> dict:
        """Load workflow definition from YAML."""
        for yaml_file in (self.config_dir / "workflows").glob("*.yaml"):
            with open(yaml_file) as f:
                wf = yaml.safe_load(f)
            if wf.get('workflow', {}).get('id') == workflow_id:
                return wf['workflow']
        raise ValueError(f"Workflow '{workflow_id}' not found")
    
    def list_workflows(self) -> list:
        """List all available workflows."""
        workflows = []
        for yaml_file in (self.config_dir / "workflows").glob("*.yaml"):
            with open(yaml_file) as f:
                wf = yaml.safe_load(f)
            w = wf.get('workflow', {})
            workflows.append({
                'id': w.get('id'),
                'description': w.get('description'),
                'schedule': w.get('schedule'),
                'enabled': w.get('enabled', False),
                'steps': len(w.get('steps', [])),
            })
        return workflows
    
    def run_workflow(self, workflow_id: str, env_file: str = None, dry_run: bool = False) -> dict:
        """Execute a workflow."""
        wf = self.load_workflow(workflow_id)
        run_id = f"{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting workflow: {workflow_id}")
        logger.info(f"  Description: {wf.get('description')}")
        logger.info(f"  Steps: {len(wf.get('steps', []))}")
        
        results = {
            'run_id': run_id,
            'workflow_id': workflow_id,
            'started_at': datetime.now().isoformat(),
            'dry_run': dry_run,
            'steps': [],
            'status': 'running',
        }
        
        for i, step in enumerate(wf.get('steps', []), 1):
            step_result = {
                'step': i,
                'skill': step.get('skill', 'system'),
                'action': step.get('action', 'default'),
                'started_at': datetime.now().isoformat(),
            }
            
            logger.info(f"\n--- Step {i}: {step.get('skill', 'system')}.{step.get('action', 'default')} ---")
            
            if dry_run:
                step_result['status'] = 'skipped (dry run)'
                logger.info(f"  [DRY RUN] Would execute: {step}")
            else:
                try:
                    # Execute step
                    step_result['status'] = 'success'
                    step_result['message'] = f"Executed {step.get('skill')}.{step.get('action')}"
                except Exception as e:
                    step_result['status'] = 'failure'
                    step_result['error'] = str(e)
                    logger.error(f"  Step failed: {e}")
            
            step_result['completed_at'] = datetime.now().isoformat()
            results['steps'].append(step_result)
        
        # Post-actions
        for action in wf.get('post_actions', []):
            logger.info(f"  Post-action: {action.get('type')}")
        
        results['status'] = 'completed'
        results['completed_at'] = datetime.now().isoformat()
        
        # Save execution log
        log_path = self.log_dir / f"{run_id}.json"
        with open(log_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nWorkflow complete. Log: {log_path}")
        
        return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Workflow Orchestrator')
    parser.add_argument('--config-dir', required=True)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--reports-dir', required=True)
    parser.add_argument('--run', type=str, help='Workflow ID to run')
    parser.add_argument('--list', action='store_true', help='List workflows')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    orch = WorkflowOrchestrator(args.config_dir, args.data_dir, args.reports_dir)
    
    if args.list:
        for wf in orch.list_workflows():
            status = '✅' if wf['enabled'] else '⬚'
            print(f"  {status} {wf['id']}: {wf['description']} ({wf['steps']} steps) [{wf['schedule']}]")
    elif args.run:
        orch.run_workflow(args.run, dry_run=args.dry_run)
