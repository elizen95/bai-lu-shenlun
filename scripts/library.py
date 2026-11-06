"""Read the local course and writing library without third-party dependencies."""
from pathlib import Path
import argparse
import json
import sqlite3
import sys

BASE = Path(__file__).resolve().parents[1]


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stats', 'search', 'show', 'questions', 'themes'])
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--kind', choices=['source', 'article'], default='source')
    parser.add_argument('--course', default='')
    parser.add_argument('--theme', default='')
    parser.add_argument('--stage', default='')
    parser.add_argument('--type', default='')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--length', type=int, default=6000)
    parser.add_argument('--section', choices=['student', 'teacher'], default='student')
    parser.add_argument('--include-legacy', action='store_true')
    args = parser.parse_args()
    connection = sqlite3.connect((BASE / 'assets/library.sqlite3').as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    if args.command == 'stats':
        for table in ('sources', 'articles', 'questions'):
            print(table, connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0])
        for row in connection.execute('SELECT stage,status,count(*) AS count FROM questions GROUP BY stage,status'):
            print(dict(row))
    elif args.command == 'themes':
        print((BASE / 'assets/taxonomy.json').read_text(encoding='utf-8'))
    elif args.command == 'search':
        table = 'articles' if args.kind == 'article' else 'sources'
        conditions, values = [], []
        for token in args.query.split():
            conditions.append('instr(text, ?) > 0')
            values.append(token)
        if args.course:
            field = 'source_id' if table == 'articles' else 'course'
            conditions.append(f'{field} LIKE ?')
            values.append(args.course + '%' if table == 'articles' else args.course)
        if args.theme:
            if table != 'articles':
                parser.error('--theme requires --kind article')
            conditions.append('instr(themes, ?) > 0')
            values.append(args.theme)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        for row in connection.execute(f'SELECT * FROM {table}{where} ORDER BY id LIMIT ?', values + [min(max(args.limit, 1), 100)]):
            entry = dict(row)
            body = entry.pop('text')
            entry.pop('metadata', None)
            entry.pop('tips', None)
            position = body.find(args.query.split()[0]) if args.query else 0
            position = max(position - 80, 0)
            entry['excerpt_start'] = position
            entry['excerpt'] = body[position:position + 500]
            print(json.dumps(entry, ensure_ascii=False))
    elif args.command == 'questions':
        conditions, values = [], []
        if not args.include_legacy:
            conditions.append("stage != '旧题待核'")
        for field, value in [('stage', args.stage), ('type', args.type)]:
            if value:
                conditions.append(f'{field} = ?')
                values.append(value)
        if args.query:
            conditions.append('instr(student, ?) > 0')
            values.append(args.query)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        statement = 'SELECT id,source_id,title,type,stage,score,word_limit,status,family,key_source,explanation_source,notes FROM questions'
        for row in connection.execute(statement + where + ' ORDER BY id LIMIT ?', values + [min(max(args.limit, 1), 100)]):
            print(json.dumps(dict(row), ensure_ascii=False))
    else:
        row = connection.execute('SELECT * FROM sources WHERE id=?', (args.query,)).fetchone()
        table = 'sources'
        if row is None:
            row = connection.execute('SELECT * FROM articles WHERE id=?', (args.query,)).fetchone()
            table = 'articles'
        if row is None:
            row = connection.execute('SELECT * FROM questions WHERE id=?', (args.query,)).fetchone()
            table = 'questions'
        if row is None:
            parser.error('Unknown source, article or question ID')
        entry = dict(row)
        if table == 'questions':
            body = entry[args.section]
            if not body:
                parser.error('No teacher key stored. Retrieve key_source or explanation_source separately.')
            entry.pop('student')
            entry.pop('teacher')
        else:
            body = entry.pop('text')
        entry.pop('metadata', None)
        entry.pop('tips', None)
        entry['total_characters'] = len(body)
        entry['start'] = max(0, args.start)
        entry['length'] = min(max(1, args.length), 60000)
        print(json.dumps(entry, ensure_ascii=False))
        print(body[entry['start']:entry['start'] + entry['length']])
    connection.close()


if __name__ == '__main__':
    main()
