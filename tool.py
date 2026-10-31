"""Query OADP/Velero backups covering the selected namespace and flag stale or incomplete backups."""
import argparse
from decimal import Decimal
import json
import sys
import subprocess
from datetime import datetime, timezone
from oc_client import Client, VM, VMI, MIG, SNAP, quantity, age_hours, condition, require_name, stopped, escape, migration


def execute(client,args):
    backups = Client(args.context,args.backup_namespace).items('backups.velero.io')
    rows = []
    for backup in backups:
        spec,status = backup.get('spec',{}),backup.get('status',{})
        included,excluded = spec.get('includedNamespaces',['*']),spec.get('excludedNamespaces',[])
        if args.namespace in excluded or ('*' not in included and args.namespace not in included): continue
        age = age_hours(status.get('completionTimestamp'))
        rows.append({'name':backup['metadata']['name'],'phase':status.get('phase'),'age_hours':age,'stale_or_incomplete':status.get('phase') != 'Completed' or age is None or age > args.max_age_hours,
                     'resource_filter':spec.get('includedResources',[]),'label_selector':spec.get('labelSelector'),'errors':status.get('errors',0),'warnings':status.get('warnings',0)})
    return {'namespace':args.namespace,'backups':rows,'namespace_coverage_only':True}


def main():
    parser = argparse.ArgumentParser(description='Query OADP/Velero backups covering the selected namespace and flag stale or incomplete backups.')
    parser.add_argument('--context',required=True,help='Explicit existing oc kubeconfig context')
    parser.add_argument('--namespace',required=True,help='Namespace for workload operations')
    parser.add_argument('--name',help='Exact workload/resource name where required')
    parser.add_argument('--apply',action='store_true',help='Execute the requested change; default is preview')
    parser.add_argument('--backup-namespace',default='openshift-adp')
    parser.add_argument('--max-age-hours',type=float,default=24)
    args = parser.parse_args()
    try:
        result = execute(Client(args.context,args.namespace),args)
        print(json.dumps({'context':args.context,'namespace':args.namespace,'collected_at':datetime.now(timezone.utc).isoformat(),'result':result},indent=2))
    except (RuntimeError,ValueError,KeyError,OSError,TimeoutError,subprocess.SubprocessError) as error:
        print(str(error),file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__': raise SystemExit(main())
