"""Testes do agente da Nara. Rodam sem discord.py, aiosqlite ou Gemini (tudo simulado).

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

# módulos pesados que ia_ferramentas importa só dentro de criar_registro
import datetime as _dt
_stub_san = types.ModuleType("cogs.santuario"); _stub_san.TEMAS = {"Ouro": 1, "Sangue": 2}
_stub_zer = types.ModuleType("cogs.zerados"); _stub_zer.PLATAFORMAS = ["PS5", "PC"]
_stub_pla = types.ModuleType("cogs.platinas"); _stub_pla.hoje = lambda: _dt.date(2026, 11, 2)
sys.modules.update({"cogs.santuario": _stub_san, "cogs.zerados": _stub_zer, "cogs.platinas": _stub_pla})

import loja  # noqa: E402
from ia_ferramentas import criar_registro  # noqa: E402
from ia_nucleo import (Adaptador, Ctx, ErroFerramenta, Ferramenta, Param, Registro, Risco,  # noqa: E402
                       rodar_agente, validar_args)


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ----------------------------------------------------------------------------- fakes
class Membro:
    def __init__(self, uid, nome, bot=False, admin=False):
        self.id, self.display_name, self.name, self.bot = uid, nome, nome.lower(), bot
        self.guild_permissions = SimpleNamespace(administrator=admin)


class Guild:
    def __init__(self, *membros):
        self.members = list(membros)

    def get_member(self, uid):
        return next((m for m in self.members if m.id == uid), None)


class FakeDB:
    def __init__(self):
        self.users = {}
        self.inv = {}          # (uid, item) -> [tipo, equipado]
        self.logs = []
        self.perfis = {}
        self.zerados = set()

    def dar(self, uid, xp=0, den=0):
        self.users[uid] = {"xp": xp, "denarios": den}

    async def get_user(self, uid):
        return self.users.setdefault(uid, {"xp": 0, "denarios": 0})

    async def inventario_do_usuario(self, uid):
        return [{"item": i, "tipo": t, "equipado": e} for (u, i), (t, e) in self.inv.items() if u == uid]

    async def comprar_item(self, uid, item, tipo, preco):
        if (uid, item) in self.inv:
            return "ja_tem"
        u = await self.get_user(uid)
        if u["denarios"] < preco:
            return "sem_saldo"
        u["denarios"] -= preco
        self.inv[(uid, item)] = [tipo, 0]
        return "ok"

    async def equipar_item(self, uid, item, tipo):
        if (uid, item) not in self.inv:
            return False
        self.inv[(uid, item)][1] = 1
        return True

    async def desequipar_tipo(self, uid, tipo):
        for (u, _), v in self.inv.items():
            if u == uid and v[0] == tipo:
                v[1] = 0

    async def log(self, actor, acao, det=""):
        self.logs.append((actor, acao, det))

    async def get_perfil(self, uid):
        return self.perfis.get(uid)

    async def atualizar_perfil(self, uid, **campos):
        self.perfis[uid].update(campos)

    async def zerado_duplicado(self, uid, jogo, plat):
        return (uid, jogo.lower(), plat.lower()) in self.zerados

    async def contar_platinas(self, uid): return 3
    async def contar_zerados(self, uid): return 2
    async def posicao_xp(self, xp): return 1
    async def posicao_platinas(self, q): return 1


class FakeZerados:
    def __init__(self): self.chamadas = []
    async def gravar_zerado(self, guild, user, d, jogo, plat, com, caps):
        self.chamadas.append((user.id, d, jogo, plat, com, caps))
        return [f"✅ {jogo} registrado"]


class FakeBot:
    def __init__(self, db, **cogs):
        self.db, self._cogs = db, cogs
    def get_cog(self, nome): return self._cogs.get(nome)


def montar(acoes_mod=False, den=500, xp=0):
    ana, bia = Membro(1, "Ana"), Membro(2, "Bia")
    db = FakeDB()
    db.dar(1, xp=xp, den=den)
    db.dar(2, xp=900, den=77)
    zer = FakeZerados()
    bot = FakeBot(db, Zerados=zer)
    guild = Guild(ana, bia)
    ctx = Ctx(bot=bot, guild=guild, autor=ana, eh_mod=False)
    return bot, db, ctx, criar_registro(bot, pesquisa=False, acoes_mod=acoes_mod), zer, bia


# ----------------------------------------------------------------------------- núcleo
class TestValidacao(unittest.TestCase):
    F = Ferramenta("t", "d", Risco.LEITURA,
                   (Param("n", "integer", "x", minimo=1, maximo=5), Param("modo", "string", "x", opcoes=("a", "b")),
                    Param("opc", "string", "x", obrigatorio=False, max_len=3)), None)

    def test_obrigatorio_e_enum(self):
        with self.assertRaises(ErroFerramenta): validar_args(self.F, {"modo": "a"})
        with self.assertRaises(ErroFerramenta): validar_args(self.F, {"n": 1, "modo": "z"})

    def test_coercao_limites_e_extras(self):
        self.assertEqual(validar_args(self.F, {"n": "3", "modo": "a", "user_id": 99}), {"n": 3, "modo": "a"})
        with self.assertRaises(ErroFerramenta): validar_args(self.F, {"n": 9, "modo": "a"})
        with self.assertRaises(ErroFerramenta): validar_args(self.F, {"n": True, "modo": "a"})
        with self.assertRaises(ErroFerramenta): validar_args(self.F, {"n": 1, "modo": "a", "opc": "longo demais"})


class TestRegistro(unittest.TestCase):
    def test_ferramenta_desconhecida(self):
        _, _, ctx, reg, *_ = montar()
        self.assertIn("erro", run(reg.executar("apagar_servidor", {}, ctx)))

    def test_moderacao_negada_em_codigo(self):
        _, db, ctx, reg, *_ = montar(acoes_mod=True)
        r = run(reg.executar("conceder_xp", {"membro_id": 2, "quantidade": 100, "motivo": "x"}, ctx))
        self.assertIn("erro", r); self.assertFalse(ctx.pendentes)

    def test_moderacao_ausente_quando_desligada(self):
        *_, = montar(acoes_mod=False)
        _, _, _, reg, *_ = montar(acoes_mod=False)
        self.assertNotIn("conceder_xp", reg.ferramentas)

    def test_chamada_repetida_executa_uma_vez(self):
        n = []
        async def f(ctx, a): n.append(1); return "ok"
        reg = Registro([Ferramenta("x", "d", Risco.PROPRIA, (), f)])
        ctx = Ctx(bot=None, guild=None, autor=Membro(1, "Ana"))
        run(reg.executar("x", {}, ctx)); run(reg.executar("x", {}, ctx))
        self.assertEqual(len(n), 1)

    def test_excecao_inesperada_nao_vaza(self):
        async def f(ctx, a): raise RuntimeError("segredo interno")
        reg = Registro([Ferramenta("x", "d", Risco.LEITURA, (), f)])
        r = run(reg.executar("x", {}, Ctx(bot=None, guild=None, autor=Membro(1, "Ana"))))
        self.assertNotIn("segredo", str(r))


# ----------------------------------------------------------------------------- ferramentas
class TestFerramentas(unittest.TestCase):
    def test_compra_so_acontece_apos_confirmar(self):
        _, db, ctx, reg, *_ = montar(den=500)
        r = run(reg.executar("comprar_item", {"item_id": "cor_brasa"}, ctx))
        self.assertEqual(r["status"], "aguardando_confirmacao")
        self.assertEqual(db.users[1]["denarios"], 500)                 # nada cobrado ainda
        self.assertEqual(len(ctx.pendentes), 1)
        texto = run(ctx.pendentes[0].executar())
        self.assertEqual(db.users[1]["denarios"], 400)
        self.assertIn((1, "cor_brasa"), db.inv)
        self.assertTrue(any(l[1] == "loja_compra" for l in db.logs))
        self.assertIn("comprou", texto)

    def test_compra_nao_duplica_e_sem_saldo(self):
        _, db, ctx, reg, *_ = montar(den=500)
        run(reg.executar("comprar_item", {"item_id": "cor_brasa"}, ctx))
        run(ctx.pendentes[0].executar())
        with self.assertRaises(ErroFerramenta): run(ctx.pendentes[0].executar())   # clique duplo/replay
        self.assertEqual(db.users[1]["denarios"], 400)
        _, db2, ctx2, reg2, *_ = montar(den=10)
        self.assertIn("erro", run(reg2.executar("comprar_item", {"item_id": "cor_brasa"}, ctx2)))
        self.assertFalse(ctx2.pendentes)

    def test_nivel_minimo_e_item_inexistente(self):
        _, _, ctx, reg, *_ = montar(den=9999, xp=0)
        self.assertIn("erro", run(reg.executar("comprar_item", {"item_id": "tit_renascido"}, ctx)))
        self.assertIn("erro", run(reg.executar("comprar_item", {"item_id": "item_falso"}, ctx)))

    def test_uma_acao_pendente_por_resposta(self):
        _, _, ctx, reg, *_ = montar(den=500)
        run(reg.executar("comprar_item", {"item_id": "cor_brasa"}, ctx))
        r = run(reg.executar("comprar_item", {"item_id": "cor_hera"}, ctx))
        self.assertIn("erro", r); self.assertEqual(len(ctx.pendentes), 1)

    def test_ia_nao_age_em_nome_de_outro(self):
        _, db, ctx, reg, _, bia = montar(den=500)
        run(reg.executar("comprar_item", {"item_id": "cor_brasa", "user_id": 2, "membro_id": 2}, ctx))
        self.assertEqual(ctx.pendentes[0].autor_id, 1)
        run(ctx.pendentes[0].executar())
        self.assertIn((1, "cor_brasa"), db.inv); self.assertNotIn((2, "cor_brasa"), db.inv)
        self.assertEqual(db.users[2]["denarios"], 77)

    def test_equipar(self):
        _, db, ctx, reg, *_ = montar()
        self.assertIn("erro", run(reg.executar("equipar_item", {"item_id": "cor_brasa"}, ctx)))
        db.inv[(1, "cor_brasa")] = ["cor", 0]
        self.assertIn("resultado", run(reg.executar("equipar_item", {"item_id": "cor_brasa"}, ctx)))
        self.assertEqual(db.inv[(1, "cor_brasa")][1], 1)

    def test_saldo_de_outro_membro_e_privado(self):
        _, _, ctx, reg, *_ = montar()
        outro = run(reg.executar("consultar_perfil", {"membro_id": 2}, ctx))
        proprio = run(reg.executar("consultar_perfil", {}, ctx))
        self.assertNotIn("denarios", outro); self.assertEqual(proprio["denarios"], 500)
        self.assertIn("erro", run(reg.executar("consultar_perfil", {"membro_id": 999}, ctx)))

    def test_zerado_valida_e_grava_no_nucleo_existente(self):
        _, db, ctx, reg, zer, _ = montar()
        self.assertIn("erro", run(reg.executar("registrar_zerado", {"jogo": "Elden Ring", "plataforma": "PC", "data": "31/12/2099"}, ctx)))
        self.assertIn("erro", run(reg.executar("registrar_zerado", {"jogo": "Elden Ring", "plataforma": "PC", "data": "ontem"}, ctx)))
        self.assertIn("erro", run(reg.executar("registrar_zerado", {"jogo": "X", "plataforma": "Atari"}, ctx)))
        db.zerados.add((1, "elden ring", "pc"))
        self.assertIn("erro", run(reg.executar("registrar_zerado", {"jogo": "Elden Ring", "plataforma": "PC"}, ctx)))
        db.zerados.clear()
        r = run(reg.executar("registrar_zerado", {"jogo": "Elden Ring", "plataforma": "PC", "data": "01/11/2026"}, ctx))
        self.assertEqual(r["status"], "aguardando_confirmacao"); self.assertFalse(zer.chamadas)
        run(ctx.pendentes[0].executar())
        self.assertEqual(zer.chamadas[0][0], 1); self.assertEqual(zer.chamadas[0][2], "Elden Ring")

    def test_santuario_exige_perfil_e_rede_valida(self):
        _, db, ctx, reg, *_ = montar()
        self.assertIn("erro", run(reg.executar("atualizar_santuario", {"frase": "oi"}, ctx)))
        db.perfis[1] = {"links": "{}", "tagline": ""}
        self.assertEqual(run(reg.executar("atualizar_santuario", {"frase": "oi", "tema": "Sangue"}, ctx))["status"], "aguardando_confirmacao")
        self.assertIn("erro", run(reg.executar("atualizar_santuario", {"tema": "Rosa"}, Ctx(bot=ctx.bot, guild=ctx.guild, autor=ctx.autor))))
        ctx2 = Ctx(bot=ctx.bot, guild=ctx.guild, autor=ctx.autor)
        self.assertIn("erro", run(reg.executar("definir_rede", {"rede": "steam", "acao": "adicionar", "link": "https://evil.com/x"}, ctx2)))
        r = run(reg.executar("definir_rede", {"rede": "twitch", "acao": "adicionar", "link": "@ana"}, ctx2))
        self.assertEqual(r["status"], "aguardando_confirmacao")
        run(ctx2.pendentes[0].executar())
        self.assertIn("twitch.tv/ana", db.perfis[1]["links"])

    def test_xp_de_moderacao_so_para_moderador_e_confirmado(self):
        bot, db, ctx, reg, *_ = montar(acoes_mod=True)
        ctx.eh_mod = True
        prog = SimpleNamespace(dado=[])
        async def conceder(guild, uid, q, motivo): prog.dado.append((uid, q))
        prog.conceder_xp = conceder
        bot._cogs["ProgressaoXP"] = prog
        r = run(reg.executar("conceder_xp", {"membro_id": 2, "quantidade": 100, "motivo": "evento"}, ctx))
        self.assertEqual(r["status"], "aguardando_confirmacao"); self.assertFalse(prog.dado)
        self.assertTrue(ctx.pendentes[0].exige_mod)
        run(ctx.pendentes[0].executar()); self.assertEqual(prog.dado, [(2, 100)])
        self.assertIn("erro", run(reg.executar("conceder_xp", {"membro_id": 2, "quantidade": 99999, "motivo": "x"}, Ctx(bot=bot, guild=ctx.guild, autor=ctx.autor, eh_mod=True))))


# ----------------------------------------------------------------------------- laço do agente
class _Fn:  # function_call falso
    def __init__(self, name, args): self.name, self.args = name, args


class _Parte:
    def __init__(self, text=None, fc=None): self.text, self.function_call, self.thought = text, fc, False


class _Resp:
    def __init__(self, *partes): self.candidates = [SimpleNamespace(content=SimpleNamespace(parts=list(partes)))]


class _Adapt(Adaptador):
    def conteudo_usuario(self, texto): return ("user", texto)
    def conteudo_funcoes(self, respostas): return ("tool", respostas)
    def parte_resposta(self, nome, resultado): return (nome, resultado)


class TestLaco(unittest.TestCase):
    def test_modelo_chama_ferramenta_e_depois_responde(self):
        _, db, ctx, reg, *_ = montar(den=500)
        vistos = []
        respostas = iter([_Resp(_Parte(fc=_Fn("listar_loja", {}))), _Resp(_Parte(text="Você tem 500."))])
        async def gerar(contents, usar):
            vistos.append(list(contents)); return next(respostas)
        texto = run(rodar_agente(gerar, _Adapt(), "quanto tenho?", reg, ctx))
        self.assertEqual(texto, "Você tem 500.")
        nome, resultado = vistos[1][-1][1][0]
        self.assertEqual(nome, "listar_loja"); self.assertEqual(resultado["saldo_denarios"], 500)

    def test_fluxo_de_compra_termina_com_pendente(self):
        _, db, ctx, reg, *_ = montar(den=500)
        respostas = iter([_Resp(_Parte(fc=_Fn("comprar_item", {"item_id": "cor_hera"}))),
                          _Resp(_Parte(text="Preparei. Toque em Confirmar."))])
        async def gerar(c, u): return next(respostas)
        run(rodar_agente(gerar, _Adapt(), "compra a hera", reg, ctx))
        self.assertEqual(len(ctx.pendentes), 1); self.assertEqual(db.users[1]["denarios"], 500)

    def test_limite_de_voltas_forca_resposta_sem_ferramentas(self):
        _, _, ctx, reg, *_ = montar()
        chamadas = []
        async def gerar(contents, usar):
            chamadas.append(usar)
            return _Resp(_Parte(fc=_Fn("listar_loja", {}))) if usar else _Resp(_Parte(text="Fechando."))
        texto = run(rodar_agente(gerar, _Adapt(), "x", reg, ctx, max_passos=3))
        self.assertEqual(texto, "Fechando."); self.assertEqual(chamadas, [True, True, True, False])


if __name__ == "__main__":
    unittest.main()
