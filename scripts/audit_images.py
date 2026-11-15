"""Inventory missing catalog images from a private SQLite snapshot and source files."""

import argparse
import csv
import re
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.avif'}
COLUMNS = (
    'identificador', 'descricao', 'referencia_original', 'entidade_relacionada',
    'paginas_afetadas', 'local_da_referencia', 'diagnostico', 'evidencia',
    'situacao_atual', 'dimensoes_esperadas', 'destino_sugerido', 'prioridade',
    'ocorrencias',
)


def volume_files():
    try:
        result = subprocess.run(
            ['docker', 'compose', 'exec', '-T', 'app', 'find', '/var/www/media', '-type', 'f'],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode:
        return None
    return {line.removeprefix('/var/www/media/').replace('\\', '/')
            for line in result.stdout.splitlines()}


def code_references(root):
    references = defaultdict(set)
    static_root = root / 'dndtools' / 'static'
    files = list((root / 'dndtools' / 'templates').rglob('*.html'))
    files += list(static_root.rglob('*.css')) + list(static_root.rglob('*.js'))
    tag = re.compile(r"{%\s*(static|media)\s+['\"]([^'\"]+)['\"]", re.I)
    css_url = re.compile(r'url\(\s*[\'\"]?([^\)\'\"]+)', re.I)
    literal = re.compile(r"(?:src|href)\s*=\s*['\"](/(?:static|media)/[^'\"]+)", re.I)
    for file in files:
        relative_file = file.relative_to(root).as_posix()
        for number, line in enumerate(file.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            found = [(kind.lower(), value) for kind, value in tag.findall(line)]
            found += [('literal', value) for value in literal.findall(line)]
            if file.suffix == '.css':
                found += [('css', value) for value in css_url.findall(line)]
            for kind, value in found:
                value = value.split('?', 1)[0].strip()
                if value.startswith(('data:', '#')):
                    continue
                if value.startswith(('http://', 'https://')):
                    path = urlsplit(value).path
                    if Path(path).suffix.lower() in IMAGE_SUFFIXES:
                        references[('external', value)].add(f'{relative_file}:{number}')
                    continue
                if kind == 'css':
                    candidate = (file.parent / value).resolve()
                    if static_root not in candidate.parents and candidate != static_root:
                        continue
                    path = candidate.relative_to(static_root).as_posix()
                    kind = 'static'
                elif kind == 'literal':
                    kind, path = value.lstrip('/').split('/', 1)
                else:
                    path = value.lstrip('/')
                if Path(path).suffix.lower() in IMAGE_SUFFIXES:
                    references[(kind, path)].add(f'{relative_file}:{number}')
    return references


def add_missing(records, original, *, description, entity, page, location, dimensions,
                static_root, volume, priority='alta'):
    normalized = original.lstrip('/').removeprefix('media/')
    parts = PurePosixPath(normalized).parts
    if '..' in parts or not parts:
        return
    local_candidates = [static_root / original, static_root / 'media' / normalized,
                        static_root.parent / 'media' / normalized]
    if any(path.is_file() for path in local_candidates) or volume is not None and normalized in volume:
        return
    confirmed = volume is not None
    key = ('catalog', normalized)
    record = records.setdefault(key, {
        'identificador': 'media:' + normalized,
        'descricao': description,
        'referencia_original': original,
        'entidade_relacionada': [], 'paginas_afetadas': [], 'local_da_referencia': [],
        'diagnostico': 'Arquivo ausente no código e no volume de mídia' if confirmed else 'Arquivo ausente no código; volume não verificado',
        'evidencia': 'Caminhos do projeto verificados' + ('; /var/www/media verificado' if confirmed else '; volume indisponível'),
        'situacao_atual': 'pendente' if confirmed else 'não confirmada',
        'dimensoes_esperadas': dimensions,
        'destino_sugerido': '/var/www/media/' + normalized,
        'prioridade': priority,
        'ocorrencias': 0,
    })
    record['entidade_relacionada'].append(entity)
    record['paginas_afetadas'].append(page)
    record['local_da_referencia'].append(location)
    record['ocorrencias'] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=Path('docs'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    static_root = root / 'dndtools' / 'static'
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    volume = volume_files()
    records = {}
    db = sqlite3.connect('file:' + args.sqlite.resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            parser.error('SQLite integrity check failed.')
        books = list(db.execute('''SELECT b.id, b.name, b.slug, b.image, e.slug AS edition_slug,
                                      e.id AS edition_id FROM dnd_rulebook b
                                  JOIN dnd_dndedition e ON e.id = b.dnd_edition_id'''))
        races = list(db.execute('''SELECT r.id, r.name, r.slug, r.image, b.slug AS book_slug,
                                      b.id AS book_id FROM dnd_race r
                                  JOIN dnd_rulebook b ON b.id = r.rulebook_id'''))
        for book in books:
            if book['image']:
                add_missing(records, book['image'], description='Capa de ' + book['name'],
                            entity=f"Rulebook #{book['id']}: {book['name']}",
                            page=f"/rulebooks/{book['edition_slug']}--{book['edition_id']}/{book['slug']}--{book['id']}/",
                            location='dnd_rulebook.image; dndtools/templates/dnd/rulebooks/rulebook_detail.html',
                            dimensions='200 × ~250 px (ajuda do modelo)', static_root=static_root, volume=volume)
        for race in races:
            if race['image']:
                add_missing(records, race['image'], description='Ilustração de ' + race['name'],
                            entity=f"Race #{race['id']}: {race['name']}",
                            page=f"/races/{race['book_slug']}--{race['book_id']}/{race['slug']}--{race['id']}/",
                            location='dnd_race.image; dndtools/templates/dnd/races/race_detail.html',
                            dimensions='até 500 × 500 px (ajuda do modelo)', static_root=static_root, volume=volume)

        inline_count = 0
        image_tag = re.compile(r'<img\b[^>]*\bsrc\s*=\s*[\'\"]([^\'\"]+)', re.I)
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'dnd_%'"):
            columns = [row['name'] for row in db.execute(f'PRAGMA table_info("{table}")')
                       if row['type'].upper().startswith(('TEXT', 'VARCHAR'))]
            for column in columns:
                for row in db.execute(f'SELECT id, "{column}" FROM "{table}" WHERE "{column}" LIKE ?', ('%<img%',)):
                    for url in image_tag.findall(row[column] or ''):
                        inline_count += 1
                        # Inline images remain pending when their remote host cannot be inspected.
                        if url.startswith(('http://', 'https://')):
                            key = ('external', url)
                            record = records.setdefault(key, {
                                'identificador': 'external:' + str(len(records) + 1),
                                'descricao': 'Imagem externa em conteúdo do catálogo',
                                'referencia_original': url,
                                'entidade_relacionada': [], 'paginas_afetadas': [], 'local_da_referencia': [],
                                'diagnostico': 'Disponibilidade externa não verificada',
                                'evidencia': 'Referência encontrada em HTML persistido; sem teste HTTP',
                                'situacao_atual': 'não confirmada', 'dimensoes_esperadas': 'desconhecidas',
                                'destino_sugerido': 'a definir após verificar direitos e origem',
                                'prioridade': 'a definir', 'ocorrencias': 0,
                            })
                            record['entidade_relacionada'].append(f'{table} #{row["id"]}')
                            record['local_da_referencia'].append(f'{table}.{column}')
                            record['ocorrencias'] += 1

        source_refs = code_references(root)
        for (kind, path), locations in source_refs.items():
            if kind == 'external':
                exists = False
                diagnosis = 'Disponibilidade externa não verificada'
                evidence = 'Referência encontrada no código; sem teste HTTP'
                status = 'não confirmada'
                destination = 'a definir após verificar direitos e origem'
            else:
                normalized = path.removeprefix('media/') if kind == 'media' else path
                exists = (static_root / normalized).is_file() if kind == 'static' else (
                    (static_root.parent / 'media' / normalized).is_file() or volume is not None and normalized in volume)
                diagnosis = 'Arquivo ausente' if volume is not None or kind == 'static' else 'Volume não verificado'
                evidence = 'Caminho relativo verificado no projeto' + (' e no volume' if volume is not None else '')
                status = 'pendente' if diagnosis == 'Arquivo ausente' else 'não confirmada'
                destination = ('dndtools/static/' if kind == 'static' else '/var/www/media/') + normalized
            if exists:
                continue
            key = (kind, path)
            if key in records:
                records[key]['local_da_referencia'].extend(sorted(locations))
                records[key]['ocorrencias'] += len(locations)
                continue
            records[key] = {
                'identificador': f'{kind}:{path}', 'descricao': 'Imagem referenciada no código',
                'referencia_original': path, 'entidade_relacionada': [], 'paginas_afetadas': [],
                'local_da_referencia': sorted(locations), 'diagnostico': diagnosis,
                'evidencia': evidence, 'situacao_atual': status,
                'dimensoes_esperadas': 'desconhecidas', 'destino_sugerido': destination,
                'prioridade': 'média', 'ocorrencias': len(locations),
            }
        output = []
        for record in records.values():
            output.append({key: '; '.join(dict.fromkeys(value)) if isinstance(value, list) else value
                           for key, value in record.items()})
        output.sort(key=lambda row: row['identificador'])
        csv_path = output_dir / 'image-inventory.csv'
        with csv_path.open('w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(output)
        markdown = [
            '# Inventário de imagens pendentes', '',
            f"Gerado em {datetime.now(ZoneInfo('America/Sao_Paulo')):%Y-%m-%d %H:%M} (São Paulo).",
            '',
            f'- Fonte de dados: SQLite íntegro em modo somente leitura, {len(books)} livros e {len(races)} raças.',
            f"- Sem imagem cadastrada: {sum(not book['image'] for book in books)} livros e {sum(not race['image'] for race in races)} raças. Ausência de cadastro não significa que existia uma imagem.",
            f'- Arquivos estáticos versionados: {sum(1 for file in static_root.rglob("*") if file.suffix.lower() in IMAGE_SUFFIXES)} imagens.',
            f'- Referências literais em templates/CSS/JS: {len(source_refs)} únicas; HTML persistido com `<img>`: {inline_count} ocorrências.',
            '- Volume `/var/www/media`: ' + ('verificado' if volume is not None else 'não foi possível verificar') + '.',
            '- O marcador visual usado no site não conta como imagem recuperada. O nome original permanece no banco.',
            '- URLs externas não recebem diagnóstico de ausência sem verificação HTTP conclusiva.',
            '', '## Referências pendentes', '',
            '| Identificador | Entidade e página | Diagnóstico | Ocorrências |',
            '| --- | --- | --- | ---: |',
        ]
        for record in output:
            entity = record['entidade_relacionada'] or record['local_da_referencia']
            page = record['paginas_afetadas'] or 'página não determinada'
            markdown.append(f"| `{record['identificador']}` | {entity}; `{page}` | {record['diagnostico']} | {record['ocorrencias']} |")
        markdown += ['', 'O [CSV](image-inventory.csv) traz o caminho original, localização da referência, evidência, dimensões esperadas e destino sugerido de cada arquivo.', '']
        (output_dir / 'image-inventory.md').write_text('\n'.join(markdown), encoding='utf-8')
        print(f'{len(output)} references pending; CSV and Markdown written to {output_dir}.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
