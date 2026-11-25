from copy import deepcopy
import random

from sistemas import gwent
from sistemas.cartas import get_carta


def _unit(card_id, name, power=3, row='melee', **extra):
    payload = {
        'id': card_id, 'nome': name, 'categoria': 'Unidade', 'especial': False,
        'poder': power, 'bonus': 0, 'tipo': 'Força', 'faccao': 'Ordem Áurea',
        'habilidade': '', 'row': row, 'fileira': row, 'escudo': 0,
        'sangramento': 0, 'geada': 0, 'podrida': 0, 'loucura': 0,
    }
    payload.update(extra)
    return payload


def _state(relic_id=''):
    deck_a = [_unit(f'a{i}', f'A{i}', power=1 + (i % 3)) for i in range(12)]
    deck_b = [_unit(f'b{i}', f'B{i}', power=1 + (i % 3)) for i in range(12)]
    return gwent.novo_estado(
        777, 10, 20, {'10': deck_a, '20': deck_b},
        {'10': {'faction': 'Ordem Áurea', 'relic_id': relic_id}},
    )


def test_secure_shuffle_returns_permutation_and_does_not_mutate_source():
    deck = [{'id': str(i)} for i in range(12)]
    original = deepcopy(deck)
    shuffled = gwent.embaralhar_deck(deck, random.Random(42))
    assert deck == original
    assert {item['id'] for item in shuffled} == {str(i) for i in range(12)}
    assert shuffled != deck


def test_faction_must_be_predominant_and_specials_do_not_count():
    cards = ([{'tipo': 'Força', 'categoria': 'Unidade'}] * 5
             + [{'tipo': 'Magia', 'categoria': 'Unidade'}] * 3
             + [{'tipo': 'Destreza', 'categoria': 'Especial', 'especial': True}] * 4)
    valid, counts = gwent.validar_faccao_deck(cards, 'Ordem Áurea')
    assert valid is True
    assert counts == {'Ordem Áurea': 5, 'Véu Carmesim': 0, 'Lua Negra': 3}
    assert gwent.validar_faccao_deck(cards, 'Lua Negra')[0] is False


def test_faction_tie_allows_either_predominant_faction():
    cards = ([{'tipo': 'Força'}] * 4 + [{'tipo': 'Magia'}] * 4)
    assert gwent.validar_faccao_deck(cards, 'Ordem Áurea')[0] is True
    assert gwent.validar_faccao_deck(cards, 'Lua Negra')[0] is True
    assert gwent.validar_faccao_deck(cards, 'Véu Carmesim')[0] is False


def test_round_cleanup_resets_temporary_fields_and_uses_previous_weather_for_survivor():
    state = _state()
    p = state['players']['10']
    p['board'] = [
        _unit('survivor-melee', 'Sobrevivente Corpo a Corpo', 7, 'melee',
              habilidade='sobrevivente', bonus=0, escudo=1, geada=1, combo_ativado='combo-x'),
        _unit('survivor-ranged', 'Sobrevivente Longa Distância', 7, 'ranged',
              habilidade='sobrevivente', bonus=0, escudo=1, podrida=1),
        _unit('fallen', 'Unidade caída', 5, 'siege', bonus=3, escudo=1, loucura=2),
    ]
    state['players']['20']['board'] = [_unit('enemy', 'Inimigo', 1)]
    state['weather'] = {'melee': 2, 'ranged': 0, 'siege': 0}
    state['round_starter'] = '10'
    p['astral_thread_ready'] = True
    gwent._resolve_round(state)
    kept = p['board']
    assert len(kept) == 1
    # A unidade de Longa Distância vale 6 sob o clima anterior; a de melee valia 5.
    assert kept[0]['id'] == 'survivor-ranged'
    assert kept[0]['bonus'] == 0 and kept[0]['escudo'] == 0
    assert kept[0]['podrida'] == 0 and kept[0]['sangramento'] == 0
    discarded = next(card for card in p['discard'] if card['id'] == 'fallen')
    assert discarded['bonus'] == 0 and discarded['escudo'] == 0
    assert discarded['loucura'] == 0
    assert 'astral_thread_ready' not in p
    assert state['weather'] == {'melee': 0, 'ranged': 0, 'siege': 0}


def test_initiative_alternates_even_when_previous_starter_wins_round():
    state = _state()
    state['players']['10']['board'] = [_unit('winner', 'Vencedor', 9)]
    state['players']['20']['board'] = [_unit('loser', 'Derrotado', 1)]
    state['round_starter'] = '10'
    gwent._resolve_round(state)
    assert state['crowns']['10'] == 1
    assert state['round_starter'] == '20'
    assert state['turn'] == '20'


def test_relic_target_options_are_returned_for_targeted_relics():
    state = _state('reliquia_lamina_negra')
    state['players']['20']['board'] = [_unit('enemy-target', 'Alvo', 5, 'ranged', bonus=3)]
    options = gwent.opcoes_de_reliquia(state, 10)
    assert options['requires_row'] is True
    assert options['requires_target'] is True
    assert options['rows']['ranged'][0]['id'] == 'enemy-target'


def test_black_blade_relic_uses_selected_target():
    state = _state('reliquia_lamina_negra')
    target = _unit('enemy-target', 'Alvo', 5, 'ranged', bonus=4)
    state['players']['20']['board'] = [target]
    state['phase'] = 'battle'
    state['players']['10']['mulligan_done'] = True
    state['players']['20']['mulligan_done'] = True
    result = gwent.aplicar_jogada(state, 10, action='relic', row='ranged', target_id='enemy-target')
    assert 'error' not in result
    after = result['state']
    assert after['players']['20']['board'][0]['bonus'] == 1
    assert after['players']['10']['relic_used'] is True


def test_black_blade_shield_blocks_without_consuming_relic_or_turn_state():
    state = _state('reliquia_lamina_negra')
    state['players']['20']['board'] = [_unit('enemy-target', 'Alvo protegido', 5, 'ranged', bonus=4, escudo=1)]
    state['phase'] = 'battle'
    state['players']['10']['mulligan_done'] = True
    state['players']['20']['mulligan_done'] = True
    result = gwent.aplicar_jogada(state, 10, action='relic', row='ranged', target_id='enemy-target')
    assert 'error' not in result
    after = result['state']
    target = after['players']['20']['board'][0]
    assert target['escudo'] == 0 and target['bonus'] == 4
    assert after['players']['10']['relic_used'] is False
    assert after['turn'] == '20'


def test_ai_considers_equipped_relic_as_a_legal_candidate():
    state = _state('reliquia_lamina_negra')
    state['turn'] = '-1'
    state['phase'] = 'battle'
    ai = state['players']['20']
    human = state['players']['10']
    # Converte o segundo jogador no agente técnico da NARA para o teste.
    state['players']['-1'] = ai
    del state['players']['20']
    state['crowns'] = {'10': 0, '-1': 0}
    state['turn'] = '-1'
    ai['equipped_relic_id'] = 'reliquia_lamina_negra'
    ai['board'] = []
    ai['hand'] = [_unit(f'ai-{i}', f'IA {i}', 1) for i in range(10)]
    human['board'] = [_unit('human-target', 'Alvo humano', 1, 'melee', bonus=5)]
    human['hand'] = [_unit(f'h-{i}', f'H {i}', 1) for i in range(10)]
    human['mulligan_done'] = True
    ai['mulligan_done'] = True
    state['players'] = {'10': human, '-1': ai}
    state['round_starter'] = '10'
    result = gwent.executar_turno_ia(state, -1)
    assert result['players']['-1']['relic_used'] is True


def test_geada_and_podrida_rarity_text_matches_engine_threshold():
    from sistemas.cartas import HABILIDADES, get_carta
    assert 'Lendárias ou superiores' in HABILIDADES['gwent_geada']['texto']
    assert 'Lendárias ou superiores' in HABILIDADES['gwent_nevoa']['texto']
    for skill in ('gwent_geada', 'gwent_nevoa'):
        card = next(c for c in __import__('sistemas.cartas', fromlist=['CARTAS_POR_ID']).CARTAS_POR_ID.values() if c.habilidade == skill)
        rare = gwent.preparar_carta({**card.para_dict(), 'raridade': 'Rara'})
        legendary = gwent.preparar_carta({**card.para_dict(), 'raridade': 'Lendária'})
        assert 'raridade rara:' not in rare['habilidade_texto'].casefold()
        assert 'segunda marca' in legendary['habilidade_texto'].casefold()


def test_night_and_flame_relic_exposes_two_modes_and_resolves_selected_mode():
    # Noite: aplica Geada em todas as unidades da fileira escolhida.
    state = _state('reliquia_noite_chama')
    state['phase'] = 'battle'
    state['players']['10']['mulligan_done'] = True
    state['players']['20']['mulligan_done'] = True
    state['players']['20']['board'] = [
        _unit('enemy-1', 'Inimigo 1', 5, 'ranged'),
        _unit('enemy-2', 'Inimigo 2', 4, 'ranged'),
    ]
    options = gwent.opcoes_de_reliquia(state, 10)
    assert options['supports_modes'] is True
    result = gwent.aplicar_jogada(state, 10, action='relic', row='ranged', target_id='noite')
    assert 'error' not in result
    assert [unit['geada'] for unit in result['state']['players']['20']['board']] == [1, 1]

    # Chama: atinge apenas a unidade de maior poder efetivo na fileira.
    state = _state('reliquia_noite_chama')
    state['phase'] = 'battle'
    state['players']['10']['mulligan_done'] = True
    state['players']['20']['mulligan_done'] = True
    state['players']['20']['board'] = [
        _unit('enemy-1', 'Inimigo 1', 5, 'ranged', bonus=1),
        _unit('enemy-2', 'Inimigo 2', 4, 'ranged'),
    ]
    result = gwent.aplicar_jogada(state, 10, action='relic', row='ranged', target_id='chama')
    assert 'error' not in result
    enemies = result['state']['players']['20']['board']
    assert enemies[0]['poder'] == 4 and enemies[0]['bonus'] == -1
    assert enemies[1]['poder'] == 4 and enemies[1]['bonus'] == 0


def test_relics_do_not_advertise_or_receive_hidden_rarity_power():
    relic = get_carta('reliquia_lamina_negra')
    prepared = gwent.preparar_carta({**relic.para_dict(), 'raridade': 'Mítica'})
    assert prepared['potencia_raridade'] == 0
    assert 'Potência Mítica' not in prepared['habilidade_texto']


def test_pvp_and_solo_start_paths_use_server_side_secure_shuffle_and_relic_options():
    from pathlib import Path
    source = Path(__file__).resolve().parents[1].joinpath('bot.py').read_text(encoding='utf-8')
    assert 'match_decks = {uid: embaralhar_deck(deck) for uid, deck in match_decks.items()}' in source
    assert 'str(user_id): embaralhar_deck(deck)' in source
    assert 'str(AI_PLAYER_ID): embaralhar_deck(ai_deck)' in source
    assert '"relic_options": opcoes_de_reliquia(state, user_id)' in source
