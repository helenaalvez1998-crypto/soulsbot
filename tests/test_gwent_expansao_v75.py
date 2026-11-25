from copy import deepcopy

from sistemas import gwent
from sistemas.cartas import CARTAS_EXPANSAO_V75, CARTAS_PACOTE, get_carta


def _unit(cid, power=4, row='melee', **extra):
    unit = {
        'id': cid, 'nome': cid, 'categoria': 'Unidade', 'especial': False,
        'poder': power, 'bonus': 0, 'tipo': 'Força', 'faccao': 'Ordem Áurea',
        'habilidade': '', 'row': row, 'fileira': row, 'escudo': 0,
        'sangramento': 0, 'geada': 0, 'podrida': 0, 'loucura': 0,
    }
    unit.update(extra)
    return unit


def _card(card_id, power=4, row='melee', **extra):
    card = _unit(card_id, power, row, **extra)
    card['bonus'] = 0
    return card


def test_expansion_has_exactly_twelve_cards_four_per_faction_and_is_in_pack_pool():
    assert len(CARTAS_EXPANSAO_V75) == 12
    counts = {'Ordem Áurea': 0, 'Véu Carmesim': 0, 'Lua Negra': 0}
    for model in CARTAS_EXPANSAO_V75:
        payload = model.para_dict()
        counts[payload['faccao']] += 1
        assert model.id in {card.id for card in CARTAS_PACOTE}
        assert get_carta(model.id) is model
        assert payload['categoria'] == 'Unidade'
        assert payload['fileira'] in gwent.ROWS
        assert 3 <= model.poder <= 5
        assert model.raridade in {'Rara', 'Épica'}
        prepared = gwent.preparar_carta(payload)
        if model.id in {
            'gwent_v75_ordem_veterano_juramento', 'gwent_v75_ordem_confessora_graca',
            'gwent_v75_veu_acolito_sangue', 'gwent_v75_veu_carrasco_preco',
            'gwent_v75_lua_oraculo_geada', 'gwent_v75_lua_graviturgista',
        }:
            assert prepared['habilidade_identidade'] is True
            assert prepared['habilidade_texto'] != 'Sem habilidade especial.'
        else:
            assert prepared['habilidade_identidade'] is False
            assert 'combo compatível' in prepared['habilidade_texto'].casefold()
    assert counts == {'Ordem Áurea': 4, 'Véu Carmesim': 4, 'Lua Negra': 4}


def test_v75_faction_combos_require_two_distinct_tags_and_trigger_once_per_round():
    pairs = [
        ('gwent_v75_ordem_veterano_juramento', 'gwent_v75_ordem_guardiao_crisol', 'v75_juramento_dois_crisol'),
        ('gwent_v75_veu_acolito_sangue', 'gwent_v75_veu_devota_hemorragia', 'v75_banquete_hemorragia'),
        ('gwent_v75_lua_oraculo_geada', 'gwent_v75_lua_cartografo_lunar', 'v75_convergencia_gelida'),
    ]
    for first, second, combo_id in pairs:
        player = {'board': [_card(first)], 'synergy_used': {}}
        completing = _card(second)
        result = gwent._aplicar_combo_de_cartas(player, completing)
        assert result == gwent.SYNERGY_COMBOS[combo_id]['name']
        assert completing['bonus'] == 2
        assert completing['combo_ativado'] == combo_id
        assert gwent._aplicar_combo_de_cartas(player, _card(second)) is None


def test_order_golden_vow_and_crucible_guard():
    player = {'board': [_unit('ally', 3, 'melee')], 'discard': []}
    card = _card('gwent_v75_ordem_veterano_juramento')
    assert gwent._aplicar_habilidade_identidade(player, {'board': []}, card, {'weather': {}}, 'melee') == 'Juramento Dourado'
    assert card['bonus'] == 1 and player['board'][0]['bonus'] == 1



def test_order_grace_mender_and_golden_standard():
    ally_a = _unit('a', 3, 'siege', geada=1)
    ally_b = _unit('b', 4, 'siege', podrida=1)
    player = {'board': [ally_a, ally_b], 'discard': []}
    card = _card('gwent_v75_ordem_confessora_graca', row='siege')
    gwent._aplicar_habilidade_identidade(player, {'board': []}, card, {'weather': {}}, 'siege')
    assert ally_a['geada'] == 0 and ally_b['podrida'] == 0
    assert ally_a['bonus'] == 1 and ally_b['bonus'] == 1


def test_veil_blood_mark_triggers_second_mark_and_feast_counts_up_to_two():
    enemy = _unit('enemy', 6, 'ranged', sangramento=1)
    player = {'board': [], 'discard': []}
    other = {'board': [enemy]}
    card = _card('gwent_v75_veu_acolito_sangue', row='ranged')
    gwent._aplicar_habilidade_identidade(player, other, card, {'weather': {}}, 'ranged')
    assert enemy['sangramento'] == 0 and enemy['bonus'] == -2 and card['bonus'] == 1


def test_veil_blood_price_sacrifices_weakest_and_pursuit_targets_bleeding_enemy():
    victim = _unit('victim', 3, 'melee', escudo=1)
    stronger = _unit('stronger', 5, 'melee')
    player = {'board': [victim, stronger], 'discard': [], 'baixas': 0}
    card = _card('gwent_v75_veu_carrasco_preco')
    gwent._aplicar_habilidade_identidade(player, {'board': []}, card, {'weather': {}}, 'melee')
    assert victim not in player['board'] and victim in player['discard']
    assert card['bonus'] == 3


def test_lunar_frost_cartography_gravity_and_ward():
    enemy = _unit('frost-target', 6, 'siege', geada=1)
    card = _card('gwent_v75_lua_oraculo_geada', row='siege')
    gwent._aplicar_habilidade_identidade({'board': [], 'discard': []}, {'board': [enemy]}, card, {'weather': {}}, 'siege')
    assert enemy['geada'] == 2 and card['bonus'] == 1

    enemies = [_unit('e1', 5, 'siege', bonus=2), _unit('e2', 4, 'siege', bonus=1), _unit('e3', 3, 'siege', bonus=0)]
    card = _card('gwent_v75_lua_graviturgista', row='siege')
    gwent._aplicar_habilidade_identidade({'board': [], 'discard': []}, {'board': enemies}, card, {'weather': {}}, 'siege')
    assert [u['bonus'] for u in enemies] == [1, 0, 0]
    assert card['bonus'] == 1


def test_new_cards_can_be_played_through_the_real_match_engine():
    deck_a = [gwent.preparar_carta(c.para_dict()) for c in CARTAS_EXPANSAO_V75[:4]]
    deck_b = [gwent.preparar_carta(c.para_dict()) for c in CARTAS_EXPANSAO_V75[4:8]]
    # Repetir payloads apenas para formar decks de teste de doze cartas.
    deck_a = (deck_a * 3)[:12]
    deck_b = (deck_b * 3)[:12]
    state = gwent.novo_estado(987, 1, 2, {'1': deck_a, '2': deck_b}, {
        '1': {'faction': 'Ordem Áurea'}, '2': {'faction': 'Véu Carmesim'}
    })
    state['phase'] = 'battle'
    state['players']['1']['mulligan_done'] = True
    state['players']['2']['mulligan_done'] = True
    state['players']['2']['passed'] = True
    state['turn'] = '1'
    result = gwent.aplicar_jogada(state, 1, card_id='gwent_v75_ordem_veterano_juramento', action='play', row='melee')
    assert 'error' not in result
    assert any(u['id'] == 'gwent_v75_ordem_veterano_juramento' for u in result['state']['players']['1']['board'])


def test_v75_combo_only_piece_resolves_with_real_rarity_amplification():
    first_model = get_carta('gwent_v75_ordem_veterano_juramento')
    second_model = get_carta('gwent_v75_ordem_guardiao_crisol')
    first = gwent.preparar_carta(first_model.para_dict())
    second = gwent.preparar_carta(second_model.para_dict())
    filler_a = [gwent.preparar_carta(CARTAS_EXPANSAO_V75[0].para_dict()) for _ in range(10)]
    filler_b = [gwent.preparar_carta(CARTAS_EXPANSAO_V75[4].para_dict()) for _ in range(10)]
    state = gwent.novo_estado(988, 1, 2, {'1': filler_a + [first, second], '2': filler_b + filler_b[:2]}, {
        '1': {'faction': 'Ordem Áurea'}, '2': {'faction': 'Véu Carmesim'}
    })
    player = state['players']['1']
    player['hand'] = [first, second, *filler_a[:8]]
    player['draw_pile'] = []
    player['mulligan_done'] = True
    state['players']['2']['mulligan_done'] = True
    state['players']['2']['passed'] = True
    state['phase'] = 'battle'
    state['turn'] = '1'

    first_result = gwent.aplicar_jogada(state, 1, card_id=first['id'], action='play', row='melee')
    assert 'error' not in first_result
    second_result = gwent.aplicar_jogada(first_result['state'], 1, card_id=second['id'], action='play', row='melee')
    assert 'error' not in second_result
    completing = next(u for u in second_result['state']['players']['1']['board'] if u['id'] == second['id'])
    assert completing['combo_ativado'] == 'v75_juramento_dois_crisol'
    # Base combo +2; Rara adds its one-point numeric-effect budget.
    assert completing['bonus'] == 3
