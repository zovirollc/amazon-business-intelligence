#!/usr/bin/env python3
"""
Amazon Business Intelligence CLI
Entry point for all operations.
"""

import argparse
import sys
import os
import json
from pathlib import Path


# Resolve project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_test_api(args):
    """Test API connections."""
    from api.auth import CredentialManager
    
    CredentialManager(env_file=args.env_file)
    missing = CredentialManager.validate()
    if missing:
        print(f"Warning: Missing credentials: {', '.join(missing)}")
        return
    
    from api.sp_api_client import test_connection as test_sp
    from api.ads_api_client import test_connection as test_ads
    
    print("Testing SP API...")
    test_sp(args.env_file)
    print("\nTesting Ads API...")
    test_ads(args.env_file)


def cmd_pull_data(args):
    """Pull all data for an ASIN."""
    from api.auth import CredentialManager
    from api.data_fetcher import DataFetcher
    
    CredentialManager(env_file=args.env_file)
    fetcher = DataFetcher(env_file=args.env_file)
    
    competitors = args.competitors.split(',') if args.competitors else None
    output_dir = args.output_dir or str(PROJECT_ROOT / "data" / "raw" / "zoviro" / args.asin)
    os.makedirs(output_dir, exist_ok=True)
    
    result = fetcher.pull_all_data(
        asin=args.asin,
        competitor_asins=competitors,
        days_back=args.days,
        output_dir=output_dir,
    )
    return result


def cmd_list_workflows(args):
    """List available workflows."""
    from workflows.orchestrator import WorkflowOrchestrator
    
    orch = WorkflowOrchestrator(
        config_dir=str(PROJECT_ROOT / "config"),
        data_dir=str(PROJECT_ROOT / "data"),
        reports_dir=str(PROJECT_ROOT / "reports"),
    )
    
    print("\nAvailable Workflows:")
    for wf in orch.list_workflows():
        status = '✅' if wf['enabled'] else '⬚'
        print(f"  {status} {wf['id']}: {wf['description']} ({wf['steps']} steps) [{wf['schedule']}]")


def cmd_run_workflow(args):
    """Run a workflow."""
    from api.auth import CredentialManager
    from workflows.orchestrator import WorkflowOrchestrator
    
    CredentialManager(env_file=args.env_file)
    
    orch = WorkflowOrchestrator(
        config_dir=str(PROJECT_ROOT / "config"),
        data_dir=str(PROJECT_ROOT / "data"),
        reports_dir=str(PROJECT_ROOT / "reports"),
    )
    
    result = orch.run_workflow(args.workflow_id, dry_run=args.dry_run)
    return result


def cmd_list_skills(args):
    """List available skills."""
    skills_dir = PROJECT_ROOT / "skills"
    print("\nAvailable Skills:")
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
            skill_md = skill_dir / "SKILL.md"
            desc = ""
            if skill_md.exists():
                with open(skill_md) as f:
                    for line in f:
                        if line.startswith('# '):
                            desc = line.strip('# \n')
                            break
            print(f"  • {skill_dir.name}: {desc}")


def main():
    parser = argparse.ArgumentParser(
        description='Amazon Business Intelligence Platform',
        prog='amazon-bi',
    )
    parser.add_argument('--env-file', default=None, help='Path to .env file')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # test-api
    sub = subparsers.add_parser('test-api', help='Test API connections')
    sub.set_defaults(func=cmd_test_api)
    
    # pull-data
    sub = subparsers.add_parser('pull-data', help='Pull all data for an ASIN')
    sub.add_argument('asin', help='Product ASIN')
    sub.add_argument('--competitors', type=str, help='Comma-separated competitor ASINs')
    sub.add_argument('--days', type=int, default=31, help='Days back for reports')
    sub.add_argument('--output-dir', type=str, help='Output directory')
    sub.set_defaults(func=cmd_pull_data)
    
    # list-workflows
    sub = subparsers.add_parser('list-workflows', help='List available workflows')
    sub.set_defaults(func=cmd_list_workflows)
    
    # run-workflow
    sub = subparsers.add_parser('run-workflow', help='Run a workflow')
    sub.add_argument('workflow_id', help='Workflow ID')
    sub.add_argument('--dry-run', action='store_true', help='Dry run (no execution)')
    sub.set_defaults(func=cmd_run_workflow)
    
    # list-skills
    sub = subparsers.add_parser('list-skills', help='List available skills')
    sub.set_defaults(func=cmd_list_skills)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()
