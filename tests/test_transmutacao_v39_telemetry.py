import asyncio
from sistemas.transmutacao_telemetria import gerar_relatorio_telemetria

class FakeDB:
    def __init__(self, attempts, cards):
        self.attempts, self.cards = attempts, cards
        self.calls = []
    async def _all(self, sql, args=()):
        self.calls.append((sql, args))
        return self.attempts if 'cartas_transmutacoes' in sql else self.cards


def test_telemetry_is_aggregate_and_flags_integrity_issues():
    db = FakeDB(
        [{'status':'sucesso','probability':25,'roll':10,'failure_reason':'','created_at':'now'},
         {'status':'falha','probability':95,'roll':100,'failure_reason':'','created_at':'now'}],
        [{'rarity':'Lendária','art_status':'validated','status':'published','has_exemplar':1,'has_art_path':1},
         {'rarity':'Mítica','art_status':'pending','status':'generated','has_exemplar':0,'has_art_path':0}],
    )
    report = asyncio.run(gerar_relatorio_telemetria(db, dias=30))
    assert report['attempts_total'] == 2
    assert report['integrity_checks']['invalid_probability_records'] == 1
    assert report['integrity_checks']['invalid_roll_records'] == 1
    assert report['integrity_checks']['cards_without_validated_art'] == 1
    assert report['integrity_checks']['cards_without_exemplar'] == 1
    assert report['read_only'] is True
    assert 'owner_id' not in repr(report) and 'tx_key' not in repr(report)
    assert len(db.calls) == 2


def test_telemetry_clamps_window_and_reports_empty_data():
    db = FakeDB([], [])
    report = asyncio.run(gerar_relatorio_telemetria(db, dias=9999))
    assert report['window_days'] == 365
    assert report['attempts_total'] == report['generated_cards_total'] == 0
    assert report['alerts'] == []
