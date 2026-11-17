"""Testes da base FAQ local e do reconhecimento de paráfrases."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import faq_base  # noqa: E402
import nara_local  # noqa: E402


def test_todas_as_perguntas_cadastradas_sao_reconhecidas():
    base = faq_base.carregar_base()
    total = 0
    for item in base["intents"]:
        for pergunta in item.get("examples", []):
            assert nara_local.classificar_resposta_local(pergunta) == item["intent"], pergunta
            total += 1
    assert total >= 1450


def test_parafrases_naturais_sao_identificadas():
    casos = {
        "cadastrei a platina onde coloco": "como_registrar_platina",
        "errei um jogo que marquei como terminado da pra tirar": "como_remover_zerado",
        "como faço para apagar uma zerada que lancei errada": "como_remover_zerado",
        "tem como eu ver os jogos que terminei": "como_ver_zerados",
        "onde ativo o alerta quando o canal entrar ao vivo": "youtube",
        "como vejo quantas moedas tenho aqui": "meu_saldo",
        "me explica como funcionam as patentes": "patentes",
        "quais canais aparecem pra mim": "canais_servidor",
        "quero saber minhas estatísticas no servidor": "meu_perfil",
            "como compro coisas com meus denarios": "loja",
        "como desbloqueio os canais do servidor": "canais_servidor",
        "como receber notificacao de live": "youtube",
        "como funcionam os pontos de experiencia": "como_ganhar_xp",
        "me fala quantos denarios eu tenho": "meu_saldo",
    }
    for pergunta, esperado in casos.items():
        assert nara_local.classificar_resposta_local(pergunta) == esperado, pergunta


def test_perguntas_de_assunto_externo_nao_sao_absorvidas_pelo_faq():
    casos = [
        "como configurar bitrate do OBS para Twitch",
        "qual placa de vídeo comprar para streaming",
        "como instalar Windows no computador",
    ]
    for pergunta in casos:
        assert faq_base.classificar(pergunta)[0] is None


def test_respostas_prontas_sao_mensagens_finais_e_nao_prompts():
    texto = faq_base.resposta_pronta("como_registrar_platina")
    assert texto and "`/nara`" in texto and "Registrar platina" in texto
    assert "Você é" not in texto and "instrução" not in texto.lower()


def test_consultas_dinamicas_nao_ficam_com_resposta_estatica():
    assert faq_base.resposta_pronta("meu_saldo") is None
    assert faq_base.resposta_pronta("meu_perfil") is None
    assert faq_base.resposta_pronta("ranking_xp") is None


def test_base_tem_schema_e_respostas():
    base = json.loads(faq_base.BASE_PATH.read_text(encoding="utf-8"))
    assert base["language"] == "pt-BR"
    assert len(base["intents"]) >= 125
    assert faq_base.estatisticas()["respostas_prontas"] >= 20



def test_parafrases_adicionais_com_variacao_de_palavras():
    casos = {
        "quero saber onde mando a foto que prova minha conquista": "como_comprovante",
        "meu xp nao subiu depois que mandei a run": "quando_recebo_recompensa",
        "onde posso gastar as moedas que ganhei": "loja",
        "qual o cargo que ganho quando subo de nível": "patentes",
        "como consulto meus dados pessoais": "privacidade",
        "quem pode ver minhas moedas": "privacidade",
        "me diz como chamar a assistente": "como_chamar_nara",
        "onde eu clico para cadastrar o game que fechei": "como_registrar_zerado",
    }
    for pergunta, esperado in casos.items():
        assert nara_local.classificar_resposta_local(pergunta) == esperado, pergunta


def test_intencao_desconhecida_nao_e_adivinhada():
    assert faq_base.classificar("qual notebook devo comprar para editar vídeos") [0] is None


def test_categorias_da_central_tem_perguntas_estaticas():
    base = faq_base.carregar_base()
    categorias = {
        item.get("category") for item in base["intents"] if item.get("answer")
    }
    assert {
        "Platinas e conquistas", "Jogos zerados", "Runs e desafios",
        "XP e patentes", "Perfis e Santuários",
        "Loja e Denários", "Servidor, cargos e painéis", "YouTube e ofertas",
        "Administração e Nara", "Perfis e rankings", "IA e funcionamento",
    }.issubset(categorias)



def test_pergunta_desconhecida_em_canal_livre_pede_mencao_e_ajuda():
    rota, intent = nara_local.decidir_rota(
        "qual notebook devo comprar para editar vídeos",
        direcionada=False,
        canal_livre=True,
    )
    assert rota == "fallback"
    assert intent is None


def test_pergunta_desconhecida_fora_de_canal_livre_e_sem_mencao_e_ignorada():
    rota, intent = nara_local.decidir_rota(
        "qual notebook devo comprar para editar vídeos",
        direcionada=False,
        canal_livre=False,
    )
    assert rota == "ignorar"
    assert intent is None



def test_handlers_dinamicos_tem_categoria_e_nao_resposta_estatica():
    base = faq_base.carregar_base()
    dinâmicos = {item["intent"]: item for item in base["intents"] if item.get("handler")}
    esperados = {
        "meu_saldo", "meu_perfil", "minhas_platinas", "meus_zerados",
        "minhas_runs", "meu_inventario", "ranking_xp", "ranking_platinas",
        "ranking_zerados", "ajuda", "canais_servidor", "meus_cargos",
        "sistemas_ativos", "recompensas", "como_ganhar_xp", "como_ganhar_denarios",
    }
    assert esperados.issubset(dinâmicos)
    for intent in esperados:
        item = dinâmicos[intent]
        assert item.get("category")
        assert faq_base.resposta_pronta(intent) is None


def test_novas_perguntas_tecnicas_cobrem_regras_confirmadas():
    casos = {
        "posso fazer uma run sozinho ou preciso de outra pessoa?": "xp_por_voz",
        "qual a fórmula para chegar no level 20": "formula_nivel",
        "qual é o tamanho máximo do vídeo de uma platina": "regras_comprovante_platina",
        "o cadastro do jogo zerado é automático": "zerado_sem_aprovacao",
        "as cores que compro dão mais xp?": "loja_catalogo_precos",
        "como tiro a conquista do hall depois que foi aprovada": "invalidar_run",
        "o painel de teste do youtube faz postagem pública": "youtube_testes_status",
    }
    for pergunta, esperado in casos.items():
        assert nara_local.classificar_resposta_local(pergunta) == esperado, pergunta



def test_base_auditada_tem_fontes_e_categorias_com_limitede_select_discord():
    base = faq_base.carregar_base()
    por_categoria = {}
    for item in base["intents"]:
        assert item.get("category")
        fontes = item.get("verified_sources", {}).get("files", [])
        assert fontes, item["intent"]
        assert item.get("answer") or item.get("handler"), item["intent"]
        por_categoria[item["category"]] = por_categoria.get(item["category"], 0) + 1
    assert max(por_categoria.values()) <= 25


def test_total_de_intencoes_e_handlers_dinamicos_da_versao_auditada():
    stats = faq_base.estatisticas()
    assert stats["intencoes"] >= 125
    assert stats["exemplos"] >= 1450
    assert stats["handlers_dinamicos"] >= 16



def test_parafrases_operacionais_novas():
    casos = {
        "onde vejo meu inventário de denarios": "meu_inventario",
        "qual limite de xp por mensagen": "xp_por_mensagem",
        "minha platina ficou pendente no painel": "status_aprovacao_platina",
        "como adicionar meu twitch no santuario": "redes_santuario",
        "quanto tempo posso enviar compovante de run": "enviar_prova_run_dm",
        "sou moderador e não consigo abrir /adm": "painel_adm_comando",
        "como publicar o botão para visitar santuários": "painel_santuarios_publicar",
    }
    for pergunta, esperado in casos.items():
        assert nara_local.classificar_resposta_local(pergunta) == esperado, pergunta


def test_privacidade_do_santuario_nao_e_confundida_com_perfil():
    pergunta = "meu santuário mostra minhas moedas para quem visita?"
    assert nara_local.classificar_resposta_local(pergunta) == "santuario_acesso_privacidade"


def test_central_de_ajuda_tem_no_maximo_25_perguntas_por_categoria():
    base = faq_base.carregar_base()
    por_categoria = {}
    for item in base["intents"]:
        if item.get("answer") or item.get("handler"):
            por_categoria[item["category"]] = por_categoria.get(item["category"], 0) + 1
    assert len(por_categoria) == 11
    assert max(por_categoria.values()) <= 25


def test_perguntas_sobre_compra_e_paineis_diferenciam_interface_publica_e_privada():
    assert nara_local.classificar_resposta_local(
        "o painel da loja mostra meu saldo para todo mundo"
    ) == "painel_loja_publicar"
    assert nara_local.classificar_resposta_local(
        "como publicar o painel de informações do coliseu"
    ) == "painel_colizeu_publicar"


def test_perguntas_fora_do_escopo_continuam_sem_resposta_local():
    casos = [
        "qual notebook comprar para editar vídeos",
        "como fazer thumbnail no photoshop",
        "qual melhor placa de captura para streaming",
    ]
    for pergunta in casos:
        assert faq_base.classificar(pergunta)[0] is None
