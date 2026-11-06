"""Persist the learner profile and explicit practice events atomically."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import sys
import tempfile

BASE = Path(__file__).resolve().parents[1]
ERRORS = {f'E{number}' for number in range(1, 17)}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['read', 'profile', 'record'])
    parser.add_argument('--file', type=Path)
    parser.add_argument('--state', type=Path, default=BASE / 'state/learner.json')
    args = parser.parse_args()
    target = args.state.resolve()
    initial = {'schema_version': 1, 'profile': {}, 'events': []}
    if args.command == 'read':
        print(target.read_text(encoding='utf-8') if target.exists() else json.dumps(initial, ensure_ascii=False))
        return
    if not args.file:
        parser.error('--file is required for updates')
    update = json.loads(args.file.read_text(encoding='utf-8'))
    if not isinstance(update, dict):
        parser.error('Input must be a JSON object')
    if args.command == 'record':
        required = {'event_id', 'kind', 'question_id'}
        if not required.issubset(update) or not all(isinstance(update[key], str) and update[key] for key in required):
            parser.error('An event needs event_id, kind and question_id')
        if update['kind'] not in ('assigned', 'attempt', 'review', 'retest'):
            parser.error('Invalid event kind')
        if update['kind'] in ('attempt', 'retest'):
            if update.get('mode') not in ('independent', 'guided', 'rewrite', 'transfer', 'retest'):
                parser.error('Attempt requires a valid mode')
            if not isinstance(update.get('answer'), str) or not update['answer'].strip():
                parser.error('Attempt requires the actual learner answer')
            if not isinstance(update.get('errors', []), list) or any(code not in ERRORS for code in update.get('errors', [])):
                parser.error('Unknown error code')
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_suffix('.lock')
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        parser.error('Another update holds the learner lock. Retry after it completes.')
    try:
        os.close(descriptor)
        state = json.loads(target.read_text(encoding='utf-8')) if target.exists() else initial
        if args.command == 'profile':
            state['profile'].update(update)
        else:
            previous = next((event for event in state['events'] if event['event_id'] == update['event_id']), None)
            if previous:
                comparable = {key: value for key, value in previous.items() if key != 'recorded_at'}
                incoming = {key: value for key, value in update.items() if key != 'recorded_at'}
                if comparable != incoming:
                    parser.error('Event ID already exists with different content')
                print('Event already recorded')
                return
            update.setdefault('recorded_at', datetime.now(timezone.utc).isoformat())
            state['events'].append(update)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=target.parent, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(state, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        print('Saved', target)
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
