"""Testes da conversa econômica da Nara (sem discord.py, SDK Gemini ou rede).

    python -m unittest discover -s tests -v
"""
import asyncio
import os
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nara_conversa as conv  # noqa: E402
from gemini_resilience import GeminiUnavailableError, _state_path, _register_block, _reset_for_tests  # noqa: E402
from ia_multi import RoteadorIA, TodosProvedoresIndisponiveis  # noqa: E402
from nara_local import classificar_resposta_local, decidir_rota  # noqa: E402


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Relogio:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class RoteamentoTests(unittest.TestCase):
    def rota(self, msg):
        return decidir_rota(msg, direcionada=True, canal_livre=False)[0]

    def test_perguntas_do_print_vao_para_conversa(self):
        for msg in ("me ensina a ativar a transmissão?", "me ensine a voltar a transmissão do discord",
                    "nao pode usar o prompt ?", "pq nao usa a ia?", "me ajuda a ativar a transmissão"):
            self.assertEqual(self.rota(msg), "fallback", msg)

    def test_faq_e_sqlite_continuam_locais(self):
        for msg, intent in (("meu saldo", "meu_saldo"), ("ajuda", "ajuda"), ("oi", "saudacao"),
                            ("como registrar platina", "como_registrar_platina"), ("quem tem mais xp", "ranking_xp")):
            self.assertEqual(decidir_rota(msg, direcionada=True, canal_livre=False), ("local", intent))

    def test_frase_longa_com_palavra_social_nao_vira_menu(self):
        self.assertIsNone(classificar_resposta_local("me ajuda a configurar o OBS pra live"))
        self.assertIsNone(classificar_resposta_local("valeu mas eu queria saber como funciona o stream no celular de verdade"))

    def test_sem_mencao_nao_gasta(self):
        self.assertEqual(decidir_rota("me ensina a ativar a transmissão no canal do NARA?", direcionada=False, canal_livre=False)[0], "ignorar")


class PedidoTests(unittest.TestCase):
    def test_pedido_curto_sem_dados_privados(self):
        p = conv.montar_pedido("Quase Pro", "x" * 5000, "y" * 5000)
        self.assertLessEqual(len(p), conv.MAX_ENTRADA + conv.MAX_CONTEXTO + 120)
        self.assertIn("[Mensagem de Quase Pro]", p)

    def test_resposta_sem_mencao_em_massa_e_com_corte(self):
        self.assertNotIn("@everyone", conv.limpar_resposta("oi @everyone"))
        longa = ("Frase completa. " * 200)
        out = conv.limpar_resposta(longa)
        self.assertLessEqual(len(out), conv.MAX_SAIDA)
        self.assertTrue(out.endswith("."))

    def test_prompt_existe_e_define_personalidade(self):
        txt = conv.carregar_prompt()
        self.assertIn("Nara", txt)
        self.assertNotIn("/jogo_buscar", txt)  # comando removido
        self.assertLess(len(txt), 8500)  # personalidade compacta (inclui a persona humana) para conter custo por chamada
        self.assertIn("apenas por texto no Discord", txt)
        self.assertIn("não fala nem envia áudio", txt)


class CacheCooldownTests(unittest.TestCase):
    def test_cache_expira_e_respeita_limite(self):
        r = Relogio()
        c = conv.CacheConversa(maximo=2, ttl=10, relogio=r)
        c.guardar("a", "A"); c.guardar("b", "B"); c.guardar("c", "C")
        self.assertIsNone(c.obter("a"))
        self.assertEqual(c.obter("c"), "C")
        r.t += 11
        self.assertIsNone(c.obter("c"))

    def test_cooldown_por_usuario(self):
        r = Relogio()
        cd = conv.Cooldown(6, relogio=r)
        self.assertTrue(cd.liberar(1))
        self.assertFalse(cd.liberar(1))
        self.assertTrue(cd.liberar(2))
        r.t += 7
        self.assertTrue(cd.liberar(1))


class FakeAdaptador:
    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.chamadas = resposta, erro, []

    async def conversar(self, system, texto, max_tokens=320):
        self.chamadas.append((system, texto, max_tokens))
        if self.erro:
            raise self.erro
        return self.resposta


def roteador(primario, reserva):
    r = RoteadorIA.__new__(RoteadorIA)
    r.gemini_primary, r.gemini_backup, r.init_errors = primario, reserva, []
    return r


class FailoverTests(unittest.TestCase):
    def test_usa_principal(self):
        p, b = FakeAdaptador("oi"), FakeAdaptador("reserva")
        self.assertEqual(run(roteador(p, b).conversar("sys", "oi", 100)), "oi")
        self.assertEqual(len(b.chamadas), 0)
        self.assertEqual(p.chamadas[0][2], 100)

    def test_quota_do_principal_usa_reserva(self):
        p = FakeAdaptador(erro=GeminiUnavailableError("quota", 3600, "429", provider="primary"))
        b = FakeAdaptador("da reserva")
        self.assertEqual(run(roteador(p, b).conversar("s", "t")), "da reserva")

    def test_dois_fora_levanta_para_o_cog_responder_local(self):
        e = GeminiUnavailableError("quota", 3600, "429", provider="primary")
        with self.assertRaises(TodosProvedoresIndisponiveis):
            run(roteador(FakeAdaptador(erro=e), FakeAdaptador(erro=e)).conversar("s", "t"))

    def test_falha_nos_dois_primeiros_usa_terceiro(self):
        e1 = GeminiUnavailableError("quota", 3600, "429", provider="primary")
        e2 = GeminiUnavailableError("rate_limit", 60, "429", provider="backup")
        r = roteador(FakeAdaptador(erro=e1), FakeAdaptador(erro=e2))
        r.gemini_third = FakeAdaptador("terceira")
        self.assertEqual(run(r.conversar("s", "t")), "terceira")
        self.assertEqual(len(r.gemini_third.chamadas), 1)

    def test_tres_indisponiveis_gera_fallback_controlado(self):
        e1 = GeminiUnavailableError("quota", 3600, "429", provider="primary")
        e2 = GeminiUnavailableError("rate_limit", 60, "429", provider="backup")
        e3 = GeminiUnavailableError("unavailable", 45, "503", provider="tertiary")
        r = roteador(FakeAdaptador(erro=e1), FakeAdaptador(erro=e2))
        r.gemini_third = FakeAdaptador(erro=e3)
        with self.assertRaises(TodosProvedoresIndisponiveis):
            run(r.conversar("s", "t"))

    def test_terceiro_tem_arquivo_de_circuito_independente(self):
        primary = _state_path("primary")
        backup = _state_path("backup")
        third = _state_path("tertiary")
        self.assertNotEqual(primary, backup)
        self.assertNotEqual(primary, third)
        self.assertNotEqual(backup, third)

    def test_backoff_exponencial_por_circuito(self):
        with tempfile.TemporaryDirectory() as folder:
            old = os.environ.get("GEMINI_THIRD_CIRCUIT_STATE_FILE")
            os.environ["GEMINI_THIRD_CIRCUIT_STATE_FILE"] = os.path.join(folder, "third.json")
            try:
                _reset_for_tests()
                self.assertEqual(_register_block("tertiary", "unavailable", 5, "timeout"), 5)
                self.assertEqual(_register_block("tertiary", "unavailable", 5, "timeout"), 10)
            finally:
                _reset_for_tests()
                if old is None:
                    os.environ.pop("GEMINI_THIRD_CIRCUIT_STATE_FILE", None)
                else:
                    os.environ["GEMINI_THIRD_CIRCUIT_STATE_FILE"] = old


# ------------------------------------------------------------ cog (discord simulado)
def _carregar_cog():
    """Importa cogs/nara_ia.py com discord e dependências pesadas substituídos por stubs."""
    class Message:  # noqa: D401
        pass

    class Cog:
        @staticmethod
        def listener(*a, **k):
            return lambda f: f

    discord = types.ModuleType("discord")
    discord.Message = Message
    discord.Interaction = object
    discord.AllowedMentions = SimpleNamespace(none=lambda: None)
    discord.app_commands = SimpleNamespace(
        command=lambda **k: (lambda f: f), default_permissions=lambda **k: (lambda f: f))
    ext = types.ModuleType("discord.ext")
    commands = types.ModuleType("discord.ext.commands")
    commands.Cog = Cog
    commands.CommandNotFound = type("CommandNotFound", (Exception,), {})
    ext.commands = commands
    discord.ext = ext
    stubs = {
        "discord": discord, "discord.ext": ext, "discord.ext.commands": commands,
        "cogs.platinas": types.ModuleType("cogs.platinas"),
        "ia_confirmacao": types.ModuleType("ia_confirmacao"),
        "ia_ferramentas": types.ModuleType("ia_ferramentas"),
        "levels": types.ModuleType("levels"),
        "ia_provedores": types.ModuleType("ia_provedores"),
    }
    stubs["cogs.platinas"].eh_moderador = None
    stubs["ia_confirmacao"].AtalhoView = stubs["ia_confirmacao"].ConfirmarAcaoView = object
    stubs["ia_ferramentas"].criar_registro = None
    stubs["levels"].nivel_por_xp = stubs["levels"].patente_por_nivel = None
    stubs["ia_provedores"].pesquisa_status = lambda: {}
    sys.modules.update(stubs)
    sys.modules.pop("cogs.nara_ia", None)
    import importlib
    return importlib.import_module("cogs.nara_ia"), Message


class FakeDB:
    def __init__(self):
        self.uso = {}
        self.conn = self

    async def _one(self, sql, params):
        qtd = self.uso.get(params)
        return {"qtd": qtd} if qtd else None

    async def execute(self, sql, params):
        self.uso[params[:2]] = self.uso.get(params[:2], 0) + 1

    async def commit(self):
        pass


class CogConversaTests(unittest.TestCase):
    def setUp(self):
        self.mod, self.Message = _carregar_cog()
        self.bot = SimpleNamespace(db=FakeDB(), user=SimpleNamespace(id=1))
        self.cog = self.mod.NaraIA(self.bot)
        self.cog._dia = lambda: "2026-11-10"

    def msg(self, uid=10, nome="Quase Pro"):
        m = self.Message()
        m.author = SimpleNamespace(id=uid, display_name=nome, bot=False)
        m.reference = None
        return m

    def test_responde_com_ia_e_registra_uso(self):
        self.cog.ia = FakeAdaptador("Transmissão é no canal de voz, clique em Compartilhar tela.")
        out = run(self.cog._conversar(self.msg(), "me ensina a ativar a transmissão no canal do NARA?"))
        self.assertIn("Transmissão", out)
        self.assertEqual(self.bot.db.uso[(10, "chat:2026-11-10")], 1)
        self.assertEqual(self.bot.db.uso[(0, "chat:2026-11-10")], 1)
        system, pedido, max_tokens = self.cog.ia.chamadas[0]
        self.assertIn("Nara", system)
        self.assertEqual(max_tokens, conv.MAX_TOKENS)
        self.assertNotIn("saldo", pedido.lower())

    def test_pergunta_repetida_vem_do_cache_sem_gastar(self):
        self.cog.ia = FakeAdaptador("Resposta única.")
        run(self.cog._conversar(self.msg(10), "como ativo a transmissão no canal do NARA"))
        out = run(self.cog._conversar(self.msg(11, "Outro"), "Como ativo a transmissão no canal do NARA?"))
        self.assertEqual(out, "Resposta única.")
        self.assertEqual(len(self.cog.ia.chamadas), 1)

    def test_cooldown_nao_chama_ia(self):
        self.cog.ia = FakeAdaptador("ok")
        run(self.cog._conversar(self.msg(), "como registro minha platina no NARA?"))
        out = run(self.cog._conversar(self.msg(), "como registro meu zerado no NARA?"))
        self.assertIn("Calma", out)
        self.assertEqual(len(self.cog.ia.chamadas), 1)

    def test_limite_diario_do_usuario(self):
        self.cog.ia = FakeAdaptador("ok")
        self.bot.db.uso[(10, "chat:2026-11-10")] = conv.LIMITE_USUARIO_DIA
        out = run(self.cog._conversar(self.msg(), "como funciona o ranking do servidor?"))
        self.assertIn("cota", out)
        self.assertEqual(self.cog.ia.chamadas, [])

    def test_teto_global(self):
        self.cog.ia = FakeAdaptador("ok")
        self.bot.db.uso[(0, "chat:2026-11-10")] = conv.LIMITE_GLOBAL_DIA
        out = run(self.cog._conversar(self.msg(), "oi gente"))
        self.assertIn(out, conv.RESPOSTAS_SEM_IA)
        self.assertEqual(self.cog.ia.chamadas, [])

    def test_quota_do_gemini_cai_para_resposta_local_sem_registrar_uso(self):
        e = GeminiUnavailableError("quota", 3600, "429", provider="primary")
        self.cog.ia = roteador(FakeAdaptador(erro=e), FakeAdaptador(erro=e))
        out = run(self.cog._conversar(self.msg(), "como funciona a loja do NARA?"))
        self.assertIn(out, conv.RESPOSTAS_SEM_IA)
        self.assertEqual(self.bot.db.uso, {})

    def test_sem_provedor_configurado(self):
        self.cog.ia = None
        self.assertIn(run(self.cog._conversar(self.msg(), "oi?")), conv.RESPOSTAS_SEM_IA)

    def test_so_marcou_sem_texto_nao_gasta(self):
        self.cog.ia = FakeAdaptador("não deveria chamar")
        run(self.cog._conversar(self.msg(), "   "))
        self.assertEqual(self.cog.ia.chamadas, [])


if __name__ == "__main__":
    unittest.main()


def test_prompt_carrega_personalidade_canonica_completa_e_regras_da_conversa():
    txt = conv.carregar_prompt()
    personalidade = conv.carregar_personalidade()
    assert personalidade in txt
    assert "Administradora implacável" in personalidade
    assert "Especialista técnica" in personalidade
    assert "Júnior" in personalidade and "criador" in personalidade
    assert "ESCOPO DESTA ROTA: CONVERSA TEXTUAL" in txt
    assert "Não invente fatos" in txt


def test_pedido_de_acao_e_separado_de_pergunta_explicativa():
    from nara_local import decidir_rota
    assert decidir_rota("Nara, compra uma cor na loja", direcionada=True, canal_livre=False)[0] == "acao"
    assert decidir_rota("Nara, equipa meu título", direcionada=True, canal_livre=False)[0] == "acao"
    rota, intent = decidir_rota("Como compro itens na loja?", direcionada=True, canal_livre=False)
    assert rota in {"local", "fallback"}
    assert rota != "acao"
