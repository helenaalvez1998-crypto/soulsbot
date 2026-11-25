import sqlite3
from sistemas.transmutacao_readiness import (
    REQUIRED_TABLES, avaliar_arquivos, avaliar_dependencias, avaliar_ambiente,
    avaliar_schema, consolidar_preflight,
)


def test_readiness_blocks_missing_files_and_dependencies(tmp_path):
    checks = avaliar_arquivos(tmp_path) + avaliar_dependencias([])
    report = consolidar_preflight(checks)
    assert report['status'] == 'blocked'
    assert report['production_approved'] is False


def test_readiness_passes_only_when_required_files_and_deps_exist(tmp_path):
    from sistemas.transmutacao_readiness import REQUIRED_FILES
    for name in REQUIRED_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# fixture', encoding='utf-8')
    report = consolidar_preflight(
        avaliar_arquivos(tmp_path),
        avaliar_dependencias(['aiosqlite==0.22.1', 'aiohttp==3.14.5', 'Pillow==13.0.0']),
        avaliar_ambiente({'DISCORD_TOKEN': 'secret', 'DATA_DIR': '/persistent'}),
    )
    assert report['status'] == 'pass'
    assert 'secret' not in repr(report)
    assert report['production_approved'] is False


def test_schema_preflight_checks_required_tables():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE cartas_exemplares(id INTEGER)')
    checks = avaliar_schema(conn)
    assert len(checks) == len(REQUIRED_TABLES)
    assert next(x for x in checks if x['check'] == 'table:cartas_exemplares')['status'] == 'ok'
    assert consolidar_preflight(checks)['status'] == 'blocked'
