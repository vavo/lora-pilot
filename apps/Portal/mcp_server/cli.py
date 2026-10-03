"""Offline bootstrap for a trusted workspace administrator. Never an MCP tool."""
import argparse
import json
import re
from pathlib import Path

from .contracts import READ_SCOPES
from .files import Rejected
from .store import Store


def main():
    parser = argparse.ArgumentParser(description='Offline MCP bootstrap. Stop Portal before changing its ledger.')
    parser.add_argument('--workspace', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('disable')
    create = commands.add_parser('create-read-client')
    create.add_argument('--label', required=True)
    create.add_argument('--dataset', action='append', default=[])
    create.add_argument('--run', action='append', default=[])
    create.add_argument('--days', type=int, default=30)
    args = parser.parse_args()
    store = Store(args.workspace)
    try:
        store.initialize()
        store.claim()  # Refuse changes while Portal owns this workspace.
        if args.command == 'disable':
            store.set_enabled(False)
            print('MCP disabled. Existing files and running processes were not changed.')
        else:
            if not 1 <= len(args.label) <= 80:
                raise Rejected('INVALID_INPUT')
            for name in args.dataset:
                if Path(name).name != name or name in {'', '.', '..'}:
                    raise Rejected('INVALID_INPUT')
                with store.files.directory('datasets/' + name):
                    pass
            for run_id in args.run:
                if not re.fullmatch(r'[a-f0-9]{32}', run_id) or store.files.json('config/training/' + run_id + '/run.json').get('id') != run_id:
                    raise Rejected('INVALID_INPUT')
            client_id, token = store.create_client(args.label, sorted(READ_SCOPES), args.dataset, args.run, args.days)
            store.set_enabled(True)
            print(json.dumps(dict(client_id=client_id, token=token)))
    except Exception:
        parser.exit(1, 'MCP bootstrap refused: check workspace ownership, selected objects, ledger integrity and whether Portal is stopped.\n')
    finally:
        store.close()


if __name__ == '__main__':
    main()
