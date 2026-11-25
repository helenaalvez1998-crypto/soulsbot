"""
Catálogo comunitário de ports e mods para Discord, operado por botões.

ÚNICO COMANDO:  /catalogo  (admin) -> publica o catálogo no canal onde for usado.

A mensagem publicada tem 4 botões:
  📚 Ver catálogo  -> filtro por plataforma, paginação e ficha do port (capa, download, ISO original, tutorial)
  🔎 Buscar port   -> busca pelo nome
  📤 Enviar port   -> qualquer pessoa sugere um port; fica PENDENTE até aprovação da moderação
  🛠 Admin         -> só para quem tem "Gerenciar Servidor": adicionar, editar, remover,
                      aprovar/rejeitar pendentes e escolher o canal de avisos

Variáveis de ambiente:
  DISCORD_TOKEN = token do bot
  DATA_DIR      = (opcional) pasta persistente para jogos.db e capas

Instalação:  pip install -r requirements.txt
Execução:    python bot.py
"""
import asyncio
import math
import json
import os
import sqlite3
import logging
import uuid
import re
import unicodedata
from difflib import SequenceMatcher
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps

import discord
from discord.ext import commands

from admin_config import GuildConfig
from utils import get_text_channel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Dados isolados do catálogo, mas dentro do volume persistente da NARA.
# Para reutilizar o diretório do bot antigo, defina CATALOGO_DATA_DIR para a pasta
# que contém jogos.db, capas/ e capas_mods/.
from config import DATA_DIR as NARA_DATA_DIR
CATALOGO_DATA_DIR = os.path.abspath(os.getenv("CATALOGO_DATA_DIR") or str(NARA_DATA_DIR))
os.makedirs(CATALOGO_DATA_DIR, exist_ok=True)
FONT_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")

DB_PATH = os.path.join(CATALOGO_DATA_DIR, "jogos.db")
CAPAS_DIR = os.path.join(CATALOGO_DATA_DIR, "capas")
MODS_DIR = os.path.join(CATALOGO_DATA_DIR, "capas_mods")
bot = None  # Recebe a instância única da NARA em CatalogoIntegrado.cog_load().
PAGE_SIZE = 5  # cinco itens por página: leitura rápida e navegação leve
MAX_CAPA_BYTES = 8 * 1024 * 1024
MAX_PENDENTES_POR_USUARIO = 3

# Plataformas disponíveis para identificar cada port (máximo 24 itens, limite do Discord para menus)
PLATAFORMAS = {
    "PlayStation 1": "🟦",
    "PlayStation 2": "🟦",
    "PlayStation 3": "🟦",
    "PlayStation 4": "🟦",
    "PlayStation 5": "🟦",
    "PSP": "🟦",
    "PS Vita": "🟦",
    "Xbox": "🟩",
    "Xbox 360": "🟩",
    "Xbox One / Series": "🟩",
    "NES": "🟥",
    "Super Nintendo": "🟥",
    "Nintendo 64": "🟥",
    "GameCube": "🟥",
    "Wii": "🟥",
    "Wii U": "🟥",
    "Switch": "🟥",
    "Game Boy / GBA": "🟥",
    "DS / 3DS": "🟥",
    "Mega Drive": "🟪",
    "Sega Saturn": "🟪",
    "Dreamcast": "🟪",
    "Outra": "🌐",
}

# ------------------------------------------------------------------ banco de dados


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(CAPAS_DIR, exist_ok=True)
    os.makedirs(MODS_DIR, exist_ok=True)
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS jogos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                descricao TEXT,
                link TEXT NOT NULL,
                tutorial TEXT,
                capa TEXT,
                iso TEXT,
                status TEXT NOT NULL DEFAULT 'aprovado',
                autor_id INTEGER
            )"""
        )
        # migração: bancos criados por versões anteriores ganham as colunas novas
        existentes = {r[1] for r in conn.execute("PRAGMA table_info(jogos)")}
        for coluna, ddl in (("iso", "TEXT"), ("status", "TEXT NOT NULL DEFAULT 'aprovado'"), ("autor_id", "INTEGER"), ("outros_links", "TEXT")):
            if coluna not in existentes:
                conn.execute(f"ALTER TABLE jogos ADD COLUMN {coluna} {ddl}")
        conn.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
        # Catálogo de mods separado do catálogo de ports.
        conn.execute("""CREATE TABLE IF NOT EXISTS mods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_nome TEXT NOT NULL,
            mod_nome TEXT NOT NULL,
            descricao TEXT,
            imagem TEXT,
            link TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'aprovado',
            autor_id INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS nomes_jogos_alias (
            alias_normalizado TEXT PRIMARY KEY,
            nome_canonico TEXT NOT NULL
        )""")
        colunas_mods = {r[1] for r in conn.execute("PRAGMA table_info(mods)")}
        for coluna, ddl in (("status", "TEXT NOT NULL DEFAULT 'aprovado'"), ("autor_id", "INTEGER")):
            if coluna not in colunas_mods:
                conn.execute(f"ALTER TABLE mods ADD COLUMN {coluna} {ddl}")
        # Converte caminhos relativos herdados sem mover ou apagar as imagens.
        for tabela, coluna in (("jogos", "capa"), ("mods", "imagem")):
            for row in conn.execute(f"SELECT id, {coluna} AS caminho FROM {tabela} WHERE {coluna} IS NOT NULL"):
                caminho = row["caminho"]
                if caminho and not os.path.isabs(caminho):
                    conn.execute(
                        f"UPDATE {tabela} SET {coluna}=? WHERE id=?",
                        (os.path.abspath(os.path.join(CATALOGO_DATA_DIR, caminho)), row["id"]),
                    )


def get_config(chave):
    with db() as conn:
        r = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
    return r["valor"] if r else None


def set_config(chave, valor):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)", (chave, valor))


def listar(plataforma=None, query=None, page=0, status="aprovado", page_size=PAGE_SIZE):
    where, params = ["status = ?"], [status]
    if plataforma:
        where.append("plataforma = ?")
        params.append(plataforma)
    if query:
        where.append("nome LIKE ?")
        params.append(f"%{query}%")
    clause = "WHERE " + " AND ".join(where)
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM jogos {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, nome, plataforma, capa FROM jogos {clause} "
            "ORDER BY nome COLLATE NOCASE LIMIT ? OFFSET ?",
            params + [page_size, page * page_size],
        ).fetchall()
    return rows, total


def get_jogo(jogo_id):
    with db() as conn:
        return conn.execute("SELECT * FROM jogos WHERE id = ?", (jogo_id,)).fetchone()


def contar_pendentes(autor_id=None):
    with db() as conn:
        if autor_id:
            return conn.execute("SELECT COUNT(*) FROM jogos WHERE status = 'pendente' AND autor_id = ?",
                                (autor_id,)).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM jogos WHERE status = 'pendente'").fetchone()[0]


def link_valido(s):
    return s.strip().lower().startswith(("http://", "https://"))


def apagar_arquivo(path):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


async def salvar_capa(att: discord.Attachment):
    """Guarda uma cópia local da imagem enviada. Retorna (caminho, erro)."""
    if not (att.content_type or "").startswith("image/"):
        return None, "o arquivo enviado não é uma imagem (use png, jpg, webp...)"
    if att.size > MAX_CAPA_BYTES:
        return None, "a imagem é grande demais (máximo 8 MB)"
    ext = os.path.splitext(att.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        ext = ".png"
    path = os.path.join(CAPAS_DIR, f"{uuid.uuid4().hex}{ext}")
    try:
        await att.save(path)
    except Exception:
        return None, "não consegui baixar a imagem enviada"
    return path, None


def eh_admin(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.manage_guild:
        return True
    try:
        from config import MOD_ROLE_ID
        return bool(MOD_ROLE_ID and any(role.id == MOD_ROLE_ID for role in interaction.user.roles))
    except Exception:
        return False


def validar_links(**links):
    """Recebe nome=valor; valores vazios são ignorados. Retorna mensagem de erro ou None."""
    for valor in links.values():
        if valor and not link_valido(valor):
            return "❌ Os links precisam começar com http:// ou https://"
    return None


MAX_LINKS_OPCIONAIS = 5  # slots 'Programa N' por port (guardados em jogos.outros_links, JSON)


def formatar_outros_links(valor):
    import json
    try:
        dados = json.loads(valor or "[]")
        return dados if isinstance(dados, list) else []
    except (TypeError, ValueError):
        return []


# ------------------------------------------------------------------ embeds e botões de link


def jogo_embed(j):
    pendente = j["status"] == "pendente"
    emb = discord.Embed(
        title=j["nome"],
        description=(j["descricao"] or "")[:1500] or None,
        color=discord.Color.orange() if pendente else discord.Color.blurple(),
    )
    emoji = PLATAFORMAS.get(j["plataforma"], "🎮")
    emb.add_field(name="Plataforma", value=f"{emoji} {j['plataforma']}", inline=True)
    if j["iso"]:
        emb.add_field(name="ISO original", value="✅ Disponível", inline=True)
    if j["tutorial"]:
        emb.add_field(name="Tutorial", value="✅ Disponível", inline=True)
    if pendente:
        if j["autor_id"]:
            emb.add_field(name="Enviado por", value=f"<@{j['autor_id']}>", inline=True)
        emb.set_footer(text="⏳ Aguardando aprovação")
    file = None
    if j["capa"] and os.path.exists(j["capa"]):
        fname = os.path.basename(j["capa"])
        file = discord.File(j["capa"], filename=fname)
        emb.set_image(url=f"attachment://{fname}")  # capa grande
    return emb, file


def link_buttons(j):
    btns = [discord.ui.Button(label="Baixar", emoji="⬇️", style=discord.ButtonStyle.link, url=j["link"])]
    if j["iso"]:
        btns.append(discord.ui.Button(label="ISO", emoji="💿", style=discord.ButtonStyle.link, url=j["iso"]))
    if j["tutorial"]:
        btns.append(discord.ui.Button(label="Tutorial", emoji="📖", style=discord.ButtonStyle.link, url=j["tutorial"]))
    extras = formatar_outros_links(j["outros_links"] if "outros_links" in j.keys() else None)
    for item in extras:
        if item.get("nome") and item.get("url"):
            btns.append(discord.ui.Button(label=item["nome"][:80], emoji="🔗",
                                          style=discord.ButtonStyle.link, url=item["url"]))
    return btns


def main_content():
    """Conteúdo Markdown do painel principal; os botões ficam na mesma mensagem."""
    return (
        "# 🎮 Ports & Mods\n"
        "Explore ports de jogos por plataforma, consulte detalhes e acesse os links de download, ISO original e tutoriais quando disponíveis. Os mods ficam em um catálogo relacionado aos ports. Sugestões da comunidade passam pela revisão da equipe.\n\n"
        "📚 **Ver ports** — explore as capas e filtre pela plataforma\n"
        "🔎 **Buscar port** — encontre um port pelo nome\n"
        "📤 **Enviar port** — sugira um port para análise da moderação\n"
        "🧩 **Catálogo de mods** — navegue pelos mods associados aos ports\n\n"
        "-# Os envios da comunidade só aparecem depois da aprovação da moderação."
    )


def admin_content():
    """Conteúdo Markdown do painel administrativo."""
    return "## 🛠️ Painel de administração\nEscolha uma ação no menu abaixo. A biblioteca precisa de ordem, não de improviso."


def send_kwargs(emb, file, view):
    """Argumentos para InteractionResponse.send_message (usa file/files)."""
    kwargs = {"embed": emb, "view": view}
    if file:
        kwargs["file"] = file
    return kwargs


def edit_kwargs(emb, file, view):
    """Argumentos para InteractionResponse.edit_message (usa attachments)."""
    return {"embed": emb, "view": view, "attachments": [file] if file else []}


def render_kwargs(text_or_embed, file, view):
    """Prepara uma resposta mantendo embeds apenas quando a imagem/layout visual é necessário."""
    if isinstance(text_or_embed, discord.Embed):
        return {"content": None, "embed": text_or_embed,
                "attachments": [file] if file else [], "view": view}
    return {"content": text_or_embed, "embed": None, "attachments": [], "view": view}


# ------------------------------------------------------------------ grade visual do catálogo


_CACHE_GRADES: dict[tuple, bytes] = {}
_CACHE_GRADES_MAX = 64


def _assinatura_grade(rows) -> tuple:
    """Chave que muda quando nomes, plataformas ou os arquivos de capa mudam."""
    partes = []
    for jogo in rows:
        capa = jogo["capa"]
        try:
            mtime = os.stat(capa).st_mtime_ns if capa and os.path.isfile(capa) else 0
        except OSError:
            mtime = 0
        partes.append((capa, mtime, str(jogo["nome"]), str(jogo["plataforma"])))
    return tuple(partes)


def criar_grade_capas(rows):
    """Grade de capas com cache: páginas já vistas voltam instantaneamente."""
    chave = _assinatura_grade(rows)
    png = _CACHE_GRADES.get(chave)
    if png is None:
        png = _desenhar_grade_capas(rows)
        if len(_CACHE_GRADES) >= _CACHE_GRADES_MAX:
            _CACHE_GRADES.pop(next(iter(_CACHE_GRADES)))
        _CACHE_GRADES[chave] = png
    return discord.File(BytesIO(png), filename="catalogo.png")


def _desenhar_grade_capas(rows) -> bytes:
    """Monta uma grade 4x2 com capas e nomes (PNG em bytes)."""
    largura_capa, altura_capa = 180, 240
    margem, espacamento, faixa_titulo = 18, 14, 58
    colunas = 5
    linhas = max(1, math.ceil(len(rows) / colunas))
    largura = margem * 2 + colunas * largura_capa + (colunas - 1) * espacamento
    altura_cartao = altura_capa + faixa_titulo
    altura = margem * 2 + linhas * altura_cartao + (linhas - 1) * espacamento
    fundo = (32, 34, 39)
    cartao = (45, 48, 54)
    img = Image.new("RGB", (largura, altura), fundo)
    draw = ImageDraw.Draw(img)

    try:
        fonte_titulo = ImageFont.truetype(FONT_PATH, 15)
        fonte_plataforma = ImageFont.truetype(FONT_PATH, 11)
    except OSError:
        try:
            fonte_titulo = ImageFont.load_default(size=15)
            fonte_plataforma = ImageFont.load_default(size=11)
        except TypeError:  # Pillow antigo
            fonte_titulo = fonte_plataforma = ImageFont.load_default()

    for i, jogo in enumerate(rows):
        x = margem + (i % colunas) * (largura_capa + espacamento)
        y = margem + (i // colunas) * (altura_cartao + espacamento)
        draw.rounded_rectangle((x, y, x + largura_capa, y + altura_cartao), radius=8, fill=cartao)
        capa_path = jogo["capa"]
        try:
            if capa_path and os.path.isfile(capa_path):
                with Image.open(capa_path) as original:
                    capa = ImageOps.fit(original.convert("RGB"), (largura_capa, altura_capa), method=Image.Resampling.LANCZOS)
            else:
                capa = Image.new("RGB", (largura_capa, altura_capa), (24, 26, 31))
                placeholder = ImageDraw.Draw(capa)
                placeholder.text((largura_capa // 2, altura_capa // 2), "SEM CAPA", anchor="mm", fill=(190, 190, 190), font=fonte_titulo)
        except (OSError, ValueError):
            capa = Image.new("RGB", (largura_capa, altura_capa), (24, 26, 31))
            ImageDraw.Draw(capa).text((largura_capa // 2, altura_capa // 2), "CAPA INVÁLIDA", anchor="mm", fill=(190, 190, 190), font=fonte_plataforma)
        img.paste(capa, (x, y))

        nome = str(jogo["nome"])
        max_chars = 23
        if len(nome) > max_chars:
            nome = nome[:max_chars - 1].rstrip() + "…"
        draw.text((x + 8, y + altura_capa + 7), nome, fill=(255, 255, 255), font=fonte_titulo)
        plataforma = str(jogo["plataforma"])
        if len(plataforma) > 27:
            plataforma = plataforma[:26] + "…"
        draw.text((x + 8, y + altura_capa + 32), plataforma, fill=(185, 190, 198), font=fonte_plataforma)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# ------------------------------------------------------------------ catálogo (navegação)


class PlataformaSelect(discord.ui.Select):
    def __init__(self, atual):
        opts = [discord.SelectOption(label="Todas as plataformas", value="all", emoji="📚", default=atual is None)]
        for n, e in PLATAFORMAS.items():
            opts.append(discord.SelectOption(label=n, value=n, emoji=e, default=(n == atual)))
        super().__init__(placeholder="Filtrar por plataforma", options=opts, row=0)

    async def callback(self, interaction: discord.Interaction):
        v: CatalogView = self.view
        v.plataforma = None if self.values[0] == "all" else self.values[0]
        v.page = 0
        await v.atualizar(interaction)


class JogoSelect(discord.ui.Select):
    PLACEHOLDERS = {
        "ver": "Abrir um port...",
        "editar": "Escolha o port para editar...",
        "remover": "Escolha o port para remover...",
        "pendentes": "Escolha um envio para analisar...",
    }

    def __init__(self, rows, mode):
        opts = [
            discord.SelectOption(
                label=r["nome"][:100], value=str(r["id"]),
                description=r["plataforma"], emoji=PLATAFORMAS.get(r["plataforma"], "🎮"),
            )
            for r in rows
        ]
        super().__init__(placeholder=self.PLACEHOLDERS[mode], options=opts, row=2)

    async def callback(self, interaction: discord.Interaction):
        v: CatalogView = self.view
        jogo = get_jogo(int(self.values[0]))
        if not jogo:
            await interaction.response.send_message("Esse port não existe mais.", ephemeral=True)
            return
        emb, file = jogo_embed(jogo)
        if v.mode == "ver":
            # No catálogo público, selecionar um port funciona como um salto
            # direto na navegação: atualiza a mesma mensagem para a posição
            # daquele jogo, sem abrir a ficha em outra tela.
            alvo_id = int(self.values[0])
            paginas = max(1, math.ceil(v.total / PAGE_SIZE))
            encontrado = False
            for pagina in range(paginas):
                lote, _ = listar(
                    v.plataforma, v.query, pagina, v.status, page_size=PAGE_SIZE
                )
                for indice, item in enumerate(lote):
                    if int(item["id"]) == alvo_id:
                        v.page = pagina * PAGE_SIZE + indice
                        encontrado = True
                        break
                if encontrado:
                    break
            if not encontrado:
                await interaction.response.send_message(
                    "Esse port não está mais disponível nesse filtro.", ephemeral=True
                )
                return
            await v.atualizar(interaction)
            return
        elif v.mode == "editar":
            view = EditarView(jogo, v.estado())
        elif v.mode == "remover":
            emb.title = f"🗑 Remover: {jogo['nome']}?"
            view = RemoverView(jogo, v.estado())
        else:
            view = PendenteView(jogo, v.estado())
        await interaction.response.edit_message(embed=emb, attachments=[file] if file else [], view=view)


class PageButton(discord.ui.Button):
    def __init__(self, delta, disabled):
        super().__init__(
            label="Anterior" if delta < 0 else "Próxima",
            emoji="⬅️" if delta < 0 else "➡️",
            style=discord.ButtonStyle.secondary, disabled=disabled, row=3,
        )
        self.delta = delta

    async def callback(self, interaction: discord.Interaction):
        v: CatalogView = self.view
        v.page += self.delta
        await v.atualizar(interaction)


class PainelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Painel", emoji="🛠", style=discord.ButtonStyle.primary, row=4)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=admin_content(), embed=None, attachments=[], view=AdminView())


class JogoCardButton(discord.ui.Button):
    """Atalho individual de cada cartão da galeria visual."""
    def __init__(self, jogo, index, estado):
        nome = jogo["nome"][:75]
        super().__init__(label=nome, emoji=PLATAFORMAS.get(jogo["plataforma"], "🎮"),
                         style=discord.ButtonStyle.primary, row=1)
        self.jogo_id = int(jogo["id"])
        self.estado = estado

    async def callback(self, interaction: discord.Interaction):
        jogo = get_jogo(self.jogo_id)
        if not jogo:
            await interaction.response.send_message("Esse port não existe mais.", ephemeral=True)
            return
        emb, file = jogo_embed(jogo)
        await interaction.response.edit_message(
            **edit_kwargs(emb, file, DetalheView(jogo, self.estado))
        )


class CatalogView(discord.ui.View):
    TITULOS = {"ver": "📚 Catálogo de ports", "editar": "✏️ Editar port",
               "remover": "🗑 Remover port", "pendentes": "📥 Envios pendentes"}

    def __init__(self, mode="ver", plataforma=None, query=None, page=0, callback_voltar=None):
        super().__init__(timeout=900)
        self.mode, self.plataforma, self.query, self.page = mode, plataforma, query, page
        self.callback_voltar = callback_voltar
        self.status = "pendente" if mode == "pendentes" else "aprovado"
        self.rows, self.total = [], 0
        self.build()

    def estado(self):
        return dict(mode=self.mode, plataforma=self.plataforma, query=self.query, page=self.page, callback_voltar=self.callback_voltar)

    def build(self):
        self.clear_items()
        self.rows, self.total = listar(
            self.plataforma, self.query, self.page, self.status,
            page_size=1 if self.mode == "ver" else PAGE_SIZE,
        )
        page_size = 1 if self.mode == "ver" else PAGE_SIZE
        pages = max(1, math.ceil(self.total / page_size))
        self.add_item(PlataformaSelect(self.plataforma))
        if self.rows:
            if self.mode == "ver":
                for index, jogo in enumerate(self.rows):
                    self.add_item(JogoCardButton(jogo, index, self.estado()))
            # O preview mostra um jogo por vez, mas o menu deve listar os ports
            # da plataforma/filtro atual. Discord limita Select a 25 opções.
            select_rows, _ = listar(
                self.plataforma, self.query, 0, self.status, page_size=25
            )
            self.add_item(JogoSelect(select_rows, self.mode))
        if self.mode == "ver":
            # A ação permanece disponível mesmo quando há resultados parciais:
            # o membro pode estar procurando um título específico que não apareceu.
            enviar = discord.ui.Button(
                label="Não encontrou? Enviar port", emoji="📤",
                style=discord.ButtonStyle.success, row=3, custom_id="catalogo:enviar_ausente",
            )
            async def _enviar_ausente(interaction: discord.Interaction):
                texto = (
                    "## 📤 Cadastrar port ausente\n\n"
                    "Escolha a plataforma e envie as informações do port. A equipe revisará o cadastro."
                )
                await interaction.response.send_message(
                    content=texto, view=PlataformaPickView(publico=True), ephemeral=True
                )
            enviar.callback = _enviar_ausente
            self.add_item(enviar)
        self.add_item(PageButton(-1, self.page <= 0))
        self.add_item(PageButton(+1, self.page >= pages - 1))
        if self.mode != "ver":
            self.add_item(PainelButton())
        if self.callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, self.callback_voltar, label="Voltar à Nara", emoji="🏠")

    def render(self):
        page_size = 1 if self.mode == "ver" else PAGE_SIZE
        pages = max(1, math.ceil(self.total / page_size))
        titulo = self.TITULOS[self.mode]
        if self.query:
            titulo += f" • busca: {self.query}"
        if self.plataforma:
            titulo += f" • {self.plataforma}"

        file = None
        if self.mode == "ver":
            if self.rows:
                # Exibe um único jogo por página usando a imagem grande do Embed.
                # Isso evita comprimir várias capas em uma única imagem de grade.
                jogo = get_jogo(self.rows[0]["id"])
                if jogo:
                    emb, file = jogo_embed(jogo)
                    emb.title = f"📚 {jogo['nome']}"
                    emb.description = (
                        (jogo["descricao"] or "")[:1200]
                        or f"**Plataforma:** {PLATAFORMAS.get(jogo['plataforma'], '🎮')} {jogo['plataforma']}"
                    )
                else:
                    emb = discord.Embed(title=titulo, description="Este port não está mais disponível.", color=discord.Color.blurple())
                    file = None
            else:
                emb = discord.Embed(title=titulo, description="Nenhum port encontrado. Tente outra busca ou plataforma.", color=discord.Color.blurple())
                file = None
            emb.set_footer(text=f"Jogo {self.page + 1}/{self.total} • Use Anterior/Próxima para navegar")
            return emb, file

        if self.mode == "pendentes" and not self.rows:
            desc = "Nenhum envio aguardando aprovação."
        elif self.rows:
            desc = "\n".join(
                f"{i}. {PLATAFORMAS.get(r['plataforma'], '🎮')} **{r['nome']}** — {r['plataforma']}"
                for i, r in enumerate(self.rows, start=1)
            )
        else:
            desc = "Nenhum port encontrado."
        status = {"editar": "Selecione um port no menu para alterar os dados ou a descrição.",
                  "remover": "Selecione um port no menu para revisar e confirmar a remoção.",
                  "pendentes": "Selecione um envio no menu para aprovar ou rejeitar."}.get(self.mode, "")
        resumo = f"## {titulo}\n\n{status}\n\n{desc}\n\n-# Página {self.page + 1}/{pages} · {self.total} port(s)"
        return resumo, None

    def embed(self):
        # Compatibilidade para os modos administrativos, que não usam a grade anexada.
        emb, _ = self.render()
        return emb

    async def atualizar(self, interaction: discord.Interaction):
        self.build()
        emb, file = self.render()
        await interaction.response.edit_message(**render_kwargs(emb, file, self))


class DetalheView(discord.ui.View):
    def __init__(self, jogo, estado):
        super().__init__(timeout=900)
        self.estado = estado
        for b in link_buttons(jogo):
            self.add_item(b)
        voltar = discord.ui.Button(label="Voltar", emoji="⬅️", style=discord.ButtonStyle.secondary)
        voltar.callback = self.voltar
        self.add_item(voltar)

    async def voltar(self, interaction: discord.Interaction):
        v = CatalogView(**self.estado)
        emb, file = v.render()
        await interaction.response.edit_message(**render_kwargs(emb, file, v))


# ------------------------------------------------------------------ busca


class BuscaModal(discord.ui.Modal, title="Buscar port"):
    nome = discord.ui.TextInput(label="Nome do port", max_length=100, placeholder="Ex.: nome do jogo portado")

    def __init__(self, callback_voltar=None):
        super().__init__()
        self.callback_voltar = callback_voltar

    async def on_submit(self, interaction: discord.Interaction):
        termo = self.nome.value.strip()
        v = CatalogView(query=termo, callback_voltar=self.callback_voltar)
        if v.total == 1:
            jogo = get_jogo(v.rows[0]["id"])
            emb, file = jogo_embed(jogo)
            await interaction.response.send_message(
                ephemeral=True, **send_kwargs(emb, file, DetalheView(jogo, v.estado()))
            )
        else:
            emb, file = v.render()
            await interaction.response.send_message(
                **send_kwargs(emb, file, v), ephemeral=True
            )


class BuscarModModal(discord.ui.Modal, title="Buscar mod"):
    termo = discord.ui.TextInput(label="Nome do mod ou do port", max_length=100,
                                 placeholder="Ex.: Skyrim, texturas HD, roupa do Leon")

    def __init__(self, callback_voltar=None):
        super().__init__()
        self.callback_voltar = callback_voltar

    async def on_submit(self, interaction: discord.Interaction):
        termo = self.termo.value.strip()
        v = ModsCatalogView(query=termo, callback_voltar=self.callback_voltar)
        embed, file = await v.render()
        kwargs = {"embed": embed, "view": v, "ephemeral": True}
        if file:
            kwargs["file"] = file
        await interaction.response.send_message(**kwargs)


# ------------------------------------------------------------------ enviar / adicionar port


class PlataformaPickView(discord.ui.View):
    """Escolha da plataforma. publico=True: envio de usuário (vai para moderação)."""

    def __init__(self, publico=False):
        super().__init__(timeout=900)
        self.publico = publico
        opts = [discord.SelectOption(label=n, value=n, emoji=e) for n, e in PLATAFORMAS.items()]
        sel = discord.ui.Select(placeholder="Plataforma do port", options=opts, row=0)
        sel.callback = self.escolheu
        self.select = sel
        self.add_item(sel)
        if not publico:
            voltar = discord.ui.Button(label="Voltar", emoji="⬅️", style=discord.ButtonStyle.secondary, row=2)
            voltar.callback = self.voltar
            self.add_item(voltar)

    async def escolheu(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddModal(self.select.values[0], self.publico))

    async def voltar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=admin_content(), embed=None, view=AdminView())


class LinksOpcionaisView(discord.ui.View):
    """Abre um formulário separado para cada par nome/link opcional."""
    def __init__(self, jogo_id):
        super().__init__(timeout=900)
        self.jogo_id = jogo_id
        for numero in range(1, MAX_LINKS_OPCIONAIS + 1):
            botao = discord.ui.Button(
                label=f"Programa {numero}", emoji="🔗",
                style=discord.ButtonStyle.secondary, row=(numero - 1) // 2
            )
            async def callback(interaction, n=numero):
                jogo = get_jogo(self.jogo_id)
                if not jogo:
                    await interaction.response.send_message("❌ Port não encontrado.", ephemeral=True)
                    return
                if interaction.user.id != jogo["autor_id"] and not eh_admin(interaction):
                    await interaction.response.send_message("⛔ Você não pode alterar estes links.", ephemeral=True)
                    return
                await interaction.response.send_modal(LinkOpcionalModal(self.jogo_id, n, jogo))
            botao.callback = callback
            self.add_item(botao)


class LinkOpcionalModal(discord.ui.Modal):
    def __init__(self, jogo_id, numero, jogo):
        super().__init__(title=f"Link opcional • Programa {numero}")
        self.jogo_id = jogo_id
        self.numero = numero
        links = formatar_outros_links(jogo["outros_links"] if "outros_links" in jogo.keys() else None)
        atual = links[numero - 1] if len(links) >= numero else {}
        self.nome = discord.ui.TextInput(
            label="Nome do programa", required=False, max_length=80,
            default=atual.get("nome", ""), placeholder="Ex.: 7-Zip"
        )
        self.url = discord.ui.TextInput(
            label="Link para baixar", required=False, max_length=500,
            default=atual.get("url", ""), placeholder="https://..."
        )
        self.add_item(self.nome)
        self.add_item(self.url)

    async def on_submit(self, interaction: discord.Interaction):
        nome, url = self.nome.value.strip(), self.url.value.strip()
        if bool(nome) != bool(url):
            await interaction.response.send_message(
                "❌ Preencha o nome e o link, ou deixe os dois vazios para remover este programa.", ephemeral=True
            )
            return
        if url and not link_valido(url):
            await interaction.response.send_message("❌ O link precisa começar com http:// ou https://", ephemeral=True)
            return
        jogo = get_jogo(self.jogo_id)
        if not jogo:
            await interaction.response.send_message("❌ Port não encontrado.", ephemeral=True)
            return
        links = formatar_outros_links(jogo["outros_links"] if "outros_links" in jogo.keys() else None)
        while len(links) < MAX_LINKS_OPCIONAIS:
            links.append({})
        links[self.numero - 1] = ({"nome": nome, "url": url} if nome and url else {})
        # Mantém os espaços independentes para que Programa 2 não mude de posição.
        with db() as conn:
            conn.execute("UPDATE jogos SET outros_links = ? WHERE id = ?", (json.dumps(links, ensure_ascii=False), self.jogo_id))
        await interaction.response.send_message(
            f"✅ Programa {self.numero} salvo." if nome else f"✅ Programa {self.numero} removido.",
            ephemeral=True, view=LinksOpcionaisView(self.jogo_id)
        )


class AddModal(discord.ui.Modal):
    def __init__(self, plataforma, publico=False):
        super().__init__(title=f"{'Enviar' if publico else 'Novo'} port • {plataforma}"[:45])
        self.plataforma, self.publico = plataforma, publico
        self.nome = discord.ui.TextInput(label="Nome do port", max_length=100)
        self.link = discord.ui.TextInput(label="Link de download do port", max_length=500, placeholder="https://...")
        self.iso = discord.ui.TextInput(label="Link da ISO original (opcional)", required=False, max_length=500)
        self.tutorial = discord.ui.TextInput(
            label="Link do tutorial (opcional)", required=False, max_length=500,
            placeholder="https://...")
        self.capa = discord.ui.FileUpload(required=True, min_values=1, max_values=1)
        self.add_item(self.nome)
        self.add_item(self.link)
        self.add_item(self.iso)
        self.add_item(self.tutorial)
        self.add_item(discord.ui.Label(text="Imagem de capa (quanto maior, melhor)", component=self.capa))

    async def on_submit(self, interaction: discord.Interaction):
        if not self.publico and not eh_admin(interaction):
            await interaction.response.send_message("⛔ Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        if self.publico and contar_pendentes(interaction.user.id) >= MAX_PENDENTES_POR_USUARIO:
            await interaction.edit_original_response(content=(
                f"❌ Você já tem {MAX_PENDENTES_POR_USUARIO} envios aguardando aprovação. "
                "Espere a moderação analisar antes de enviar mais."), embed=None, view=None)
            return
        link, iso = self.link.value.strip(), self.iso.value.strip()
        tutorial = self.tutorial.value.strip()
        extras = []
        erro = validar_links(link=link, iso=iso, tutorial=tutorial)
        if erro:
            await interaction.edit_original_response(content=erro, embed=None, view=None)
            return
        if not self.capa.values:
            await interaction.edit_original_response(content="❌ Envie a imagem de capa.", embed=None, view=None)
            return
        path, erro = await salvar_capa(self.capa.values[0])
        if erro:
            await interaction.edit_original_response(content=f"❌ Capa: {erro}.", embed=None, view=None)
            return
        status = "pendente" if self.publico else "aprovado"
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO jogos (nome, plataforma, link, iso, tutorial, capa, status, autor_id, outros_links) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.nome.value.strip(), self.plataforma, link, iso or None, tutorial or None,
                 path, status, interaction.user.id, __import__("json").dumps(extras, ensure_ascii=False)),
            )
        jogo = get_jogo(cur.lastrowid)
        emb, file = jogo_embed(jogo)
        if self.publico:
            await avisar_moderacao(jogo, interaction.guild_id)
            await interaction.edit_original_response(
                content="✅ **Port enviado!** Ele aparecerá no catálogo após a aprovação da moderação.\n\nPrévia:",
                embed=emb, attachments=[file] if file else [], view=LinksOpcionaisView(jogo["id"]))
        else:
            await interaction.edit_original_response(
                content="✅ **Port adicionado!** Prévia:", embed=emb,
                attachments=[file] if file else [], view=LinksOpcionaisView(jogo["id"]))


# ------------------------------------------------------------------ moderação


async def obter_canal_moderacao(guild_id: int):
    """Usa exclusivamente o canal central configurado em /adm; o legado é fallback opcional."""
    if bot is None or getattr(bot, "db", None) is None:
        return None
    canal_id = await GuildConfig.get(bot.db, int(guild_id), "mod_channel")
    if not canal_id:
        return None
    return await get_text_channel(bot, canal_id)


async def avisar_moderacao(jogo, guild_id: int) -> bool:
    try:
        canal = await obter_canal_moderacao(guild_id)
        if canal is None:
            print(f"Canal central de moderação ausente/inacessível para guild={guild_id}; port #{jogo['id']} permanece pendente.")
            return False
        emb, file = jogo_embed(jogo)
        kw = {"file": file} if file else {}
        await canal.send(
            content="📥 **NOVO PORT — aguardando aprovação**\\n"
                    f"**ID:** `#{jogo['id']}` · **Autor:** <@{jogo['autor_id']}>\\n"
                    "Analise esta solicitação pela Central de Moderação da NARA.",
            embed=emb, **kw,
            view=PendenteView(jogo, {"mode": "pendentes", "plataforma": None, "query": None, "page": 0}),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return True
    except Exception:
        import logging
        logging.getLogger("catalogo").exception("Falha ao notificar port #%s no canal central.", jogo["id"])
        return False


async def avisar_autor(jogo, texto):
    if not jogo["autor_id"]:
        return
    try:
        user = bot.get_user(jogo["autor_id"]) or await bot.fetch_user(jogo["autor_id"])
        await user.send(texto)
    except Exception:
        pass  # DMs fechadas, tudo bem


async def conceder_drop_catalogo(tipo: str, registro):
    """Premia somente envios comunitários pendentes que foram aprovados."""
    autor_id = int(registro["autor_id"] or 0)
    if not autor_id or bot is None or getattr(bot, "db", None) is None:
        return None
    try:
        return await bot.db.coliseu_conceder_drop(
            autor_id, f"catalogo:{tipo}:{int(registro['id'])}", origem=tipo
        )
    except Exception:
        logging.getLogger("catalogo").exception(
            "Falha ao entregar drop de %s aprovado #%s para %s.", tipo, registro["id"], autor_id
        )
        return None


def texto_recompensa_catalogo(drop) -> str:
    if not drop:
        return "\n⚠️ O envio foi aprovado, mas o drop não pôde ser confirmado. Avise a moderação para conferirem a recompensa."
    outcome = str(drop.get("outcome") or "")
    if outcome == "carta":
        return f"\n🃏 Recompensa: **{drop.get('card_name', 'Carta')}** · {drop.get('card_rarity', 'Comum')}."
    if outcome == "almas":
        return f"\n✨ Duplicata convertida em **{drop.get('card_almas', 0)} Almas**."
    if outcome == "fragmentos":
        return f"\n🧩 Duplicata convertida em **{drop.get('card_fragmentos', 0)} fragmentos**."
    return ""


class VoltarPendentesView(discord.ui.View):
    def __init__(self, estado):
        super().__init__(timeout=900)
        self.estado = estado
        b = discord.ui.Button(label="Voltar aos pendentes", emoji="⬅️", style=discord.ButtonStyle.secondary)
        b.callback = self.voltar
        self.add_item(b)

    async def voltar(self, interaction: discord.Interaction):
        v = CatalogView(**self.estado)
        emb, file = v.render()
        await interaction.response.edit_message(**render_kwargs(emb, file, v))


class PendenteView(discord.ui.View):
    def __init__(self, jogo, estado):
        super().__init__(timeout=900)
        self.jogo, self.estado = jogo, estado
        for b in link_buttons(jogo):  # para o moderador conferir os links
            b.row = 0
            self.add_item(b)
        ok = discord.ui.Button(label="Aprovar", emoji="✅", style=discord.ButtonStyle.success, row=1)
        ok.callback = self.aprovar
        self.add_item(ok)
        no = discord.ui.Button(label="Rejeitar", emoji="❌", style=discord.ButtonStyle.danger, row=1)
        no.callback = self.rejeitar
        self.add_item(no)
        voltar = discord.ui.Button(label="Voltar", emoji="⬅️", style=discord.ButtonStyle.secondary, row=2)
        voltar.callback = self.voltar
        self.add_item(voltar)

    async def aprovar(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Sem permissão.", ephemeral=True)
            return
        with db() as conn:
            cur = conn.execute(
                "UPDATE jogos SET status = 'aprovado' WHERE id = ? AND status='pendente'",
                (self.jogo["id"],),
            )
        if cur.rowcount != 1:
            await interaction.response.send_message("Esse envio já foi processado.", ephemeral=True)
            return
        drop = await conceder_drop_catalogo("port", self.jogo)
        recompensa = texto_recompensa_catalogo(drop)
        await avisar_autor(
            self.jogo,
            f"✅ Seu port **{self.jogo['nome']}** foi aprovado e já está no catálogo!{recompensa}",
        )
        texto = f"## ✅ Port aprovado\n**{self.jogo['nome']}** já está no catálogo.{recompensa}"
        await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=VoltarPendentesView(self.estado))

    async def rejeitar(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Sem permissão.", ephemeral=True)
            return
        with db() as conn:
            conn.execute("DELETE FROM jogos WHERE id = ?", (self.jogo["id"],))
        apagar_arquivo(self.jogo["capa"])
        await avisar_autor(self.jogo, f"❌ Seu envio de port **{self.jogo['nome']}** não foi aprovado pela moderação.")
        texto = f"## ❌ Envio rejeitado\n**{self.jogo['nome']}** foi removido."
        await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=VoltarPendentesView(self.estado))

    async def voltar(self, interaction: discord.Interaction):
        v = CatalogView(**self.estado)
        emb, file = v.render()
        await interaction.response.edit_message(**render_kwargs(emb, file, v))


class CanalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=900)
        sel = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text],
                                       placeholder="Escolha o canal de avisos", row=0)
        sel.callback = self.escolheu
        self.sel = sel
        self.add_item(sel)
        voltar = discord.ui.Button(label="Voltar", emoji="⬅️", style=discord.ButtonStyle.secondary, row=2)
        voltar.callback = self.voltar
        self.add_item(voltar)

    async def escolheu(self, interaction: discord.Interaction):
        canal = self.sel.values[0]
        set_config("canal_avisos", str(canal.id))
        texto = f"## ✅ Canal de avisos definido\nNovos envios serão avisados em {canal.mention}."
        await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=AdminView())

    async def voltar(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=admin_content(), embed=None, view=AdminView())


class CatalogoPublicarChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        seletor = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Escolha onde publicar o painel do catálogo",
            min_values=1,
            max_values=1,
        )
        seletor.callback = self.publicar
        self.add_item(seletor)

    async def publicar(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            return await interaction.response.send_message("Acesso restrito à equipe.", ephemeral=True)
        cog = interaction.client.get_cog("CatalogoIntegrado")
        if cog is None:
            return await interaction.response.send_message("O catálogo não está disponível.", ephemeral=True)
        # O ChannelSelect entrega um AppCommandChannel; para enviar/buscar mensagens
        # é preciso o canal real do servidor.
        escolhido = self.children[0].values[0]
        canal = interaction.guild.get_channel(escolhido.id) if interaction.guild else None
        if canal is None:
            try:
                canal = await interaction.client.fetch_channel(escolhido.id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal = None
        if not isinstance(canal, discord.TextChannel):
            return await interaction.response.send_message(
                "Não consegui acessar esse canal. Escolha um canal de texto deste servidor.", ephemeral=True
            )
        await cog.publicar_painel_publico(interaction, canal)


# ------------------------------------------------------------------ painel admin


class AdminView(discord.ui.View):
    """Painel administrativo compacto: ações agrupadas em um menu único."""
    def __init__(self):
        super().__init__(timeout=900)
        n_jogos = contar_pendentes()
        n_mods = contar_mods_pendentes()
        options = [
            discord.SelectOption(label="Adicionar port", value="add_game", emoji="➕", description="Cadastrar um port"),
            discord.SelectOption(label="Editar port", value="edit_game", emoji="✏️", description="Alterar dados de um port"),
            discord.SelectOption(label="Remover port", value="delete_game", emoji="🗑️", description="Excluir um port"),
            discord.SelectOption(label=f"Aprovar ports ({n_jogos})", value="pending_games", emoji="🎮", description="Revisar envios de ports"),
            discord.SelectOption(label="Gerenciar mods", value="mods", emoji="🧩", description="Adicionar, editar, remover e moderar mods"),
            discord.SelectOption(label=f"Aprovar mods ({n_mods})", value="pending_mods", emoji="📥", description="Revisar envios de mods"),
            discord.SelectOption(label="Canal de avisos", value="channel", emoji="📢", description="Configurar notificações da moderação"),
            discord.SelectOption(label="Publicar painel público", value="publish_panel", emoji="📣", description="Publicar ou atualizar o catálogo em um canal"),
        ]
        sel = discord.ui.Select(placeholder="Escolha uma ação administrativa...", options=options)
        sel.callback = self.escolher
        self.add_item(sel)

    async def escolher(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem usar este painel.", ephemeral=True)
            return
        action = interaction.data.get("values", [""])[0]
        if action == "add_game":
            texto = "## ➕ Adicionar port\nEscolha a plataforma do port no menu abaixo para abrir o formulário."
            view = PlataformaPickView()
            await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=view)
        elif action == "edit_game":
            v = CatalogView(mode="editar")
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "delete_game":
            v = CatalogView(mode="remover")
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "pending_games":
            v = CatalogView(mode="pendentes")
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "mods":
            await interaction.response.edit_message(content="## 🧩 Administração de mods\nEscolha uma ação no menu abaixo.", embed=None, attachments=[], view=ModAdminView())
        elif action == "pending_mods":
            v = ModPendentesView()
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "publish_panel":
            await interaction.response.edit_message(
                content="## 📣 Publicar painel do catálogo\\nEscolha o canal onde os membros poderão abrir os catálogos.",
                embed=None, attachments=[], view=CatalogoPublicarChannelView(),
            )
        elif action == "channel":
            atual = get_config("canal_avisos")
            texto = (f"Canal atual: <#{atual}>\n\n" if atual else "Nenhum canal definido ainda.\n\n")
            texto += "Escolha onde avisar sobre envios que aguardam aprovação."
            await interaction.response.edit_message(content=f"## 📢 Canal de avisos\n\n{texto}", embed=None, attachments=[], view=CanalView())


class EditarView(discord.ui.View):
    def __init__(self, jogo, estado):
        super().__init__(timeout=900)
        self.jogo, self.estado = jogo, estado
        opts = [discord.SelectOption(label=n, value=n, emoji=e, default=(n == jogo["plataforma"]))
                for n, e in PLATAFORMAS.items()]
        sel = discord.ui.Select(placeholder="Mudar plataforma de origem", options=opts, row=0)
        sel.callback = self.mudar_plataforma
        self.select = sel
        self.add_item(sel)
        ed = discord.ui.Button(label="Editar dados", emoji="✏️", style=discord.ButtonStyle.primary, row=1)
        ed.callback = self.abrir_modal
        self.add_item(ed)
        ds = discord.ui.Button(label="Descrição", emoji="📝", style=discord.ButtonStyle.primary, row=1)
        ds.callback = self.abrir_descricao
        self.add_item(ds)
        voltar = discord.ui.Button(label="Voltar", emoji="⬅️", style=discord.ButtonStyle.secondary, row=2)
        voltar.callback = self.voltar
        self.add_item(voltar)

    async def mudar_plataforma(self, interaction: discord.Interaction):
        with db() as conn:
            conn.execute("UPDATE jogos SET plataforma = ? WHERE id = ?", (self.select.values[0], self.jogo["id"]))
        jogo = get_jogo(self.jogo["id"])
        emb, file = jogo_embed(jogo)
        await interaction.response.edit_message(
            embed=emb, attachments=[file] if file else [], view=EditarView(jogo, self.estado))

    async def abrir_modal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditModal(get_jogo(self.jogo["id"])))

    async def abrir_descricao(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DescricaoModal(get_jogo(self.jogo["id"])))

    async def voltar(self, interaction: discord.Interaction):
        v = CatalogView(**self.estado)
        emb, file = v.render()
        await interaction.response.edit_message(**render_kwargs(emb, file, v))


class EditModal(discord.ui.Modal):
    def __init__(self, jogo):
        super().__init__(title=f"Editar port • {jogo['nome']}"[:45])
        self.jogo = jogo
        self.nome = discord.ui.TextInput(label="Nome do port", max_length=100, default=jogo["nome"])
        self.link = discord.ui.TextInput(label="Link de download do port", max_length=500, default=jogo["link"])
        self.iso = discord.ui.TextInput(label="Link da ISO (vazio = sem ISO)", required=False, max_length=500,
                                        default=jogo["iso"] or "")
        self.tutorial = discord.ui.TextInput(
            label="Link do tutorial (opcional)", required=False, max_length=500,
            default=jogo["tutorial"] or "", placeholder="https://...")
        self.capa = discord.ui.FileUpload(required=False, min_values=0, max_values=1)
        self.add_item(self.nome)
        self.add_item(self.link)
        self.add_item(self.iso)
        self.add_item(self.tutorial)
        self.add_item(discord.ui.Label(text="Nova capa (opcional, vazio = manter)", component=self.capa))

    async def on_submit(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Sem permissão.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        link, iso = self.link.value.strip(), self.iso.value.strip()
        tutorial = self.tutorial.value.strip()
        extras = formatar_outros_links(self.jogo["outros_links"] if "outros_links" in self.jogo.keys() else None)
        erro = validar_links(link=link, iso=iso, tutorial=tutorial)
        if erro:
            await interaction.edit_original_response(content=erro, embed=None, view=None)
            return
        nova_capa = self.jogo["capa"]
        if self.capa.values:
            path, erro = await salvar_capa(self.capa.values[0])
            if erro:
                await interaction.edit_original_response(content=f"❌ Capa: {erro}.", embed=None, view=None)
                return
            apagar_arquivo(self.jogo["capa"])
            nova_capa = path
        with db() as conn:
            conn.execute(
                "UPDATE jogos SET nome = ?, link = ?, iso = ?, tutorial = ?, capa = ?, outros_links = ? WHERE id = ?",
                (self.nome.value.strip(), link, iso or None, tutorial or None, nova_capa,
                 __import__("json").dumps(extras, ensure_ascii=False), self.jogo["id"]),
            )
        emb, file = jogo_embed(get_jogo(self.jogo["id"]))
        await interaction.edit_original_response(
            content="✅ **Port atualizado!** Prévia:", embed=emb,
            attachments=[file] if file else [], view=LinksOpcionaisView(self.jogo["id"]))


class DescricaoModal(discord.ui.Modal):
    def __init__(self, jogo):
        super().__init__(title=f"Descrição • {jogo['nome']}"[:45])
        self.jogo = jogo
        self.descricao = discord.ui.TextInput(label="Descrição", required=False, style=discord.TextStyle.paragraph,
                                              max_length=1500, default=(jogo["descricao"] or "")[:1500])
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Sem permissão.", ephemeral=True)
            return
        with db() as conn:
            conn.execute("UPDATE jogos SET descricao = ? WHERE id = ?",
                         (self.descricao.value.strip() or None, self.jogo["id"]))
        await interaction.response.send_message("✅ Descrição atualizada.", ephemeral=True)


class RemoverView(discord.ui.View):
    def __init__(self, jogo, estado):
        super().__init__(timeout=900)
        self.jogo, self.estado = jogo, estado
        ok = discord.ui.Button(label="Confirmar remoção", emoji="🗑", style=discord.ButtonStyle.danger)
        ok.callback = self.confirmar
        self.add_item(ok)
        cancel = discord.ui.Button(label="Cancelar", emoji="⬅️", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancelar
        self.add_item(cancel)

    async def confirmar(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Sem permissão.", ephemeral=True)
            return
        with db() as conn:
            conn.execute("DELETE FROM jogos WHERE id = ?", (self.jogo["id"],))
        apagar_arquivo(self.jogo["capa"])
        texto = f"## 🗑️ Port removido\n**{self.jogo['nome']}** saiu do catálogo."
        await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=AdminView())

    async def cancelar(self, interaction: discord.Interaction):
        v = CatalogView(**self.estado)
        emb, file = v.render()
        await interaction.response.edit_message(**render_kwargs(emb, file, v))


# ------------------------------------------------------------------ mensagem principal (persistente)


class MainView(discord.ui.View):
    def __init__(self, callback_voltar=None):
        super().__init__(timeout=None if callback_voltar is None else 600)  # canal público persistente ou central privada
        self.callback_voltar = callback_voltar
        if callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, callback_voltar, label="Voltar à Nara", emoji="🏠")

    @discord.ui.button(label="Catálogo de ports", emoji="📚", style=discord.ButtonStyle.primary, custom_id="catalogo:ver", row=0)
    async def ver(self, interaction: discord.Interaction, button: discord.ui.Button):
        v = CatalogView(callback_voltar=self.callback_voltar)
        emb, file = v.render()
        if self.callback_voltar is not None:
            kwargs = edit_kwargs(emb, file, v)
            await interaction.response.edit_message(**kwargs)
        else:
            await interaction.response.send_message(**send_kwargs(emb, file, v), ephemeral=True)

    @discord.ui.button(label="Buscar port", emoji="🔎", style=discord.ButtonStyle.secondary, custom_id="catalogo:buscar", row=2)
    async def buscar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BuscaModal(callback_voltar=self.callback_voltar))

    @discord.ui.button(label="Enviar port", emoji="📤", style=discord.ButtonStyle.success, custom_id="catalogo:enviar", row=1)
    async def enviar(self, interaction: discord.Interaction, button: discord.ui.Button):
        texto = ("## 📤 Enviar um port\n\n"
                 "Escolha a **plataforma do port** no menu e preencha o formulário.\n"
                 "O envio será revisado pela **moderação** e só aparecerá no catálogo depois de aprovado.\n\n"
                 "-# Envios com links inválidos ou que violem as regras serão rejeitados.")
        await interaction.response.send_message(content=texto, view=PlataformaPickView(publico=True), ephemeral=True)

    @discord.ui.button(label="Enviar mod", emoji="📤", style=discord.ButtonStyle.success, custom_id="catalogo:enviarmod", row=1)
    async def enviar_mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdicionarModModal(publico=True))

    @discord.ui.button(label="Catálogo de mods", emoji="🧩", style=discord.ButtonStyle.primary, custom_id="catalogo:mods", row=0)
    async def abrir_mods(self, interaction: discord.Interaction, button: discord.ui.Button):
        v = ModsCatalogView(callback_voltar=self.callback_voltar)
        emb, file = await v.render()
        if self.callback_voltar is not None:
            await interaction.response.edit_message(embed=emb, attachments=[file] if file else [], view=v)
        else:
            kwargs = {"embed": emb, "view": v, "ephemeral": True}
            if file:
                kwargs["file"] = file
            await interaction.response.send_message(**kwargs)

    @discord.ui.button(label="Buscar mod", emoji="🔎", style=discord.ButtonStyle.secondary, custom_id="catalogo:buscarmod", row=2)
    async def buscar_mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BuscarModModal(callback_voltar=self.callback_voltar))




# ------------------------------------------------------------------ catálogo separado de mods


def normalizar_nome_jogo(nome):
    """Normaliza nomes para comparação local, sem IA ou serviços externos."""
    texto = unicodedata.normalize("NFKD", (nome or "").casefold())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def resolver_nome_jogo(nome, incluir_pendentes=False):
    """Retorna nome já usado quando há correspondência exata ou aproximada confiável."""
    original = " ".join((nome or "").strip().split())
    chave = normalizar_nome_jogo(original)
    if not chave:
        return original
    with db() as conn:
        alias = conn.execute(
            "SELECT nome_canonico FROM nomes_jogos_alias WHERE alias_normalizado = ?", (chave,)
        ).fetchone()
        if alias:
            return alias["nome_canonico"]
        status_clause = "" if incluir_pendentes else "WHERE status = 'aprovado'"
        nomes = [r[0] for r in conn.execute(
            f"SELECT jogo_nome FROM mods {status_clause} UNION SELECT nome FROM jogos WHERE status = 'aprovado'"
        ).fetchall()]
    unicos = {}
    for candidato in nomes:
        canon = " ".join((candidato or "").strip().split())
        norm = normalizar_nome_jogo(canon)
        if norm:
            unicos.setdefault(norm, canon)
    if chave in unicos:
        canon = unicos[chave]
    else:
        # Tolerância conservadora para erros de digitação; nomes curtos exigem correspondência exata.
        melhor_norm, melhor_score = None, 0.0
        for norm in unicos:
            if min(len(chave), len(norm)) < 6:
                continue
            score = SequenceMatcher(None, chave, norm).ratio()
            if score > melhor_score:
                melhor_norm, melhor_score = norm, score
        canon = unicos[melhor_norm] if melhor_norm and melhor_score >= 0.88 else original
    # Salva a grafia alternativa para reutilizá-la nas próximas submissões.
    if normalizar_nome_jogo(canon) != chave:
        with db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nomes_jogos_alias (alias_normalizado, nome_canonico) VALUES (?, ?)",
                (chave, canon),
            )
    return canon


def listar_mods(query=None, page=0):
    where, params = ["status = 'aprovado'"], []
    if query:
        where.append("(jogo_nome LIKE ? OR mod_nome LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM mods {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, jogo_nome, mod_nome, descricao, imagem, link FROM mods {clause} "
            "ORDER BY jogo_nome COLLATE NOCASE, mod_nome COLLATE NOCASE LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, page * PAGE_SIZE],
        ).fetchall()
    return rows, total


def contar_mods_pendentes():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM mods WHERE status = 'pendente'").fetchone()[0]


def get_mod(mod_id):
    with db() as conn:
        return conn.execute("SELECT * FROM mods WHERE id = ?", (mod_id,)).fetchone()


def criar_grade_mods(rows):
    """Gera grade visual exclusiva para o catálogo de mods."""
    # Adaptamos os nomes dos campos apenas para reutilizar o renderizador de capas.
    adaptados = [dict(capa=r["imagem"], nome=r["mod_nome"], plataforma=r["jogo_nome"]) for r in rows]
    arquivo = criar_grade_capas(adaptados)
    arquivo.filename = "catalogo_mods.png"
    return arquivo


class ModSelect(discord.ui.Select):
    def __init__(self, rows):
        options = [discord.SelectOption(
            label=r["mod_nome"][:100], value=str(r["id"]),
            description=f"Port: {r['jogo_nome']}"[:100], emoji="🧩") for r in rows]
        super().__init__(placeholder="Ou escolha pelo nome nesta lista", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        mod = get_mod(int(self.values[0]))
        if not mod:
            await interaction.response.send_message("Esse mod não existe mais.", ephemeral=True)
            return
        descricao = mod["descricao"] or "Sem descrição cadastrada."
        embed = discord.Embed(
            title=mod["mod_nome"],
            description=(f"**Port relacionado:** {mod['jogo_nome']}\n\n{descricao}")[:4000],
            color=discord.Color.dark_teal(),
        )
        file = None
        if mod["imagem"] and os.path.isfile(mod["imagem"]):
            filename = os.path.basename(mod["imagem"])
            file = discord.File(mod["imagem"], filename=filename)
            embed.set_image(url=f"attachment://{filename}")
        view = discord.ui.View(timeout=900)
        view.add_item(discord.ui.Button(label="Abrir / baixar mod", emoji="🔗",
                                        style=discord.ButtonStyle.link, url=mod["link"]))
        back = discord.ui.Button(label="Voltar ao catálogo", emoji="⬅️", style=discord.ButtonStyle.secondary)
        async def voltar(i: discord.Interaction):
            v = ModsCatalogView(self.view.query, self.view.page, callback_voltar=getattr(self.view, "callback_voltar", None))
            e, f = await v.render()
            await i.response.edit_message(embed=e, attachments=[f] if f else [], view=v)
        back.callback = voltar
        view.add_item(back)
        if file:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=view)
        else:
            texto = f"## 🧩 {mod['mod_nome']}\n\n**Port relacionado:** {mod['jogo_nome']}\n\n{descricao}"
            await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=view)


class ModCardButton(discord.ui.Button):
    """Botão individual de um cartão do catálogo de mods."""
    def __init__(self, mod, index):
        super().__init__(label=mod["mod_nome"][:75], emoji="🧩",
                         style=discord.ButtonStyle.primary, row=0)
        self.mod_id = int(mod["id"])

    async def callback(self, interaction: discord.Interaction):
        mod = get_mod(self.mod_id)
        if not mod:
            await interaction.response.send_message("Esse mod não existe mais.", ephemeral=True)
            return
        descricao = mod["descricao"] or "Sem descrição cadastrada."
        embed = discord.Embed(
            title=mod["mod_nome"],
            description=(f"**Port relacionado:** {mod['jogo_nome']}\n\n{descricao}")[:4000],
            color=discord.Color.dark_teal(),
        )
        file = None
        if mod["imagem"] and os.path.isfile(mod["imagem"]):
            filename = os.path.basename(mod["imagem"])
            file = discord.File(mod["imagem"], filename=filename)
            embed.set_image(url=f"attachment://{filename}")
        view = discord.ui.View(timeout=900)
        view.add_item(discord.ui.Button(label="Abrir / baixar mod", emoji="🔗",
                                        style=discord.ButtonStyle.link, url=mod["link"]))
        back = discord.ui.Button(label="Voltar ao catálogo", emoji="⬅️", style=discord.ButtonStyle.secondary)
        async def voltar(i: discord.Interaction):
            v = ModsCatalogView(self.view.query, self.view.page, callback_voltar=getattr(self.view, "callback_voltar", None))
            e, f = await v.render()
            await i.response.edit_message(embed=e, attachments=[f] if f else [], view=v)
        back.callback = voltar
        view.add_item(back)
        await interaction.response.edit_message(embed=embed, attachments=[file] if file else [], view=view)


class ModsPageButton(discord.ui.Button):
    def __init__(self, delta, disabled):
        super().__init__(label="Anterior" if delta < 0 else "Próxima",
                         emoji="⬅️" if delta < 0 else "➡️",
                         style=discord.ButtonStyle.secondary, disabled=disabled, row=2)
        self.delta = delta

    async def callback(self, interaction: discord.Interaction):
        self.view.page += self.delta
        self.view.rebuild()
        emb, file = await self.view.render()
        await interaction.response.edit_message(embed=emb, attachments=[file] if file else [], view=self.view)


class ModsCatalogView(discord.ui.View):
    def __init__(self, query=None, page=0, callback_voltar=None):
        super().__init__(timeout=900)
        self.query, self.page = query, page
        self.callback_voltar = callback_voltar
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        self.rows, self.total = listar_mods(self.query, self.page)
        pages = max(1, math.ceil(self.total / PAGE_SIZE))
        if self.rows:
            for index, mod in enumerate(self.rows):
                self.add_item(ModCardButton(mod, index))
            self.add_item(ModSelect(self.rows))
        # Não depende de zero resultados: a busca pode retornar itens parecidos,
        # mas não o mod específico que a pessoa procura.
        enviar = discord.ui.Button(
            label="Não encontrou? Enviar mod", emoji="📤",
            style=discord.ButtonStyle.success, row=3, custom_id="catalogo:mod:enviar_ausente",
        )
        async def _enviar_mod_ausente(interaction: discord.Interaction):
            await interaction.response.send_modal(AdicionarModModal(publico=True))
        enviar.callback = _enviar_mod_ausente
        self.add_item(enviar)
        self.add_item(ModsPageButton(-1, self.page <= 0))
        self.add_item(ModsPageButton(1, self.page >= pages - 1))
        if self.callback_voltar is not None:
            from utils import adicionar_botao_voltar
            adicionar_botao_voltar(self, self.callback_voltar, label="Voltar à Nara", emoji="🏠")

    async def render(self):
        pages = max(1, math.ceil(self.total / PAGE_SIZE))
        embed = discord.Embed(
            title="🧩 Catálogo de Mods",
            description=("Escolha um dos cinco cartões pelos botões ou use a lista por nome para ver descrição, imagem e link.\n\n"
                         "**Mods nesta página:**\n" + "\n".join(
                             f"🧩 **{r['mod_nome']}** — *{r['jogo_nome']}*" for r in self.rows))
                        if self.rows else "Nenhum mod cadastrado ainda.",
            color=discord.Color.dark_teal(),
        )
        file = await asyncio.to_thread(criar_grade_mods, self.rows) if self.rows else None
        if file:
            embed.set_image(url="attachment://catalogo_mods.png")
        embed.set_footer(text=f"Página {self.page + 1}/{pages} • {self.total} mod(s)")
        return embed, file


class AdicionarModModal(discord.ui.Modal):
    jogo_nome = discord.ui.TextInput(label="Nome do port", max_length=100, placeholder="Ex.: port de Skyrim")
    mod_nome = discord.ui.TextInput(label="Nome do mod", max_length=100, placeholder="Ex.: Texturas HD")
    descricao = discord.ui.TextInput(label="Descrição do mod", style=discord.TextStyle.paragraph,
                                     required=True, max_length=1500, placeholder="O que o mod altera/adiciona?")
    link = discord.ui.TextInput(label="Link do mod", max_length=500, placeholder="https://...")

    def __init__(self, publico=False):
        super().__init__(title="Enviar mod para aprovação" if publico else "Cadastrar mod")
        self.publico = publico
        self.imagem = discord.ui.FileUpload(required=True, min_values=1, max_values=1)
        self.add_item(discord.ui.Label(text="Imagem do mod", component=self.imagem))

    async def on_submit(self, interaction: discord.Interaction):
        if not self.publico and not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem cadastrar mods.", ephemeral=True)
            return
        link = self.link.value.strip()
        erro = validar_links(link=link)
        if erro:
            await interaction.response.send_message(erro, ephemeral=True)
            return
        if not self.imagem.values:
            await interaction.response.send_message("Envie a imagem do mod.", ephemeral=True)
            return
        att = self.imagem.values[0]
        if not (att.content_type or "").startswith("image/"):
            await interaction.response.send_message("O arquivo enviado precisa ser uma imagem.", ephemeral=True)
            return
        if att.size > MAX_CAPA_BYTES:
            await interaction.response.send_message("A imagem deve ter no máximo 8 MB.", ephemeral=True)
            return
        ext = os.path.splitext(att.filename)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            ext = ".png"
        path = os.path.join(MODS_DIR, f"{uuid.uuid4().hex}{ext}")
        try:
            await att.save(path)
        except Exception:
            await interaction.response.send_message("Não consegui salvar a imagem.", ephemeral=True)
            return
        jogo_informado = " ".join(self.jogo_nome.value.strip().split())
        jogo_canonico = resolver_nome_jogo(jogo_informado, incluir_pendentes=self.publico)
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO mods (jogo_nome, mod_nome, descricao, imagem, link, status, autor_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (jogo_canonico, self.mod_nome.value.strip(), self.descricao.value.strip(), path, link,
                 "pendente" if self.publico else "aprovado", interaction.user.id),
            )
            mod_id = cur.lastrowid
        if self.publico:
            await interaction.response.send_message(
                f"✅ Seu mod **{self.mod_nome.value.strip()}** foi enviado para análise da moderação.\n"
                f"Port identificado como: **{jogo_canonico}**.\n"
                "Ele aparecerá no catálogo após aprovação.",
                ephemeral=True,
            )
            try:
                canal = await obter_canal_moderacao(interaction.guild_id)
                if canal is None:
                    raise RuntimeError("Canal central de moderação não configurado ou inacessível.")
                embed = discord.Embed(
                    title="🛠️ NOVO MOD — aguardando aprovação",
                    description=(
                        f"**ID:** `#{mod_id}`\\n"
                        f"**Mod:** {discord.utils.escape_markdown(self.mod_nome.value.strip())}\\n"
                        f"**Jogo:** {discord.utils.escape_markdown(jogo_canonico)}\\n"
                        f"**Autor:** {interaction.user.mention}"
                    ),
                    color=discord.Color.orange(),
                )
                embed.set_footer(text="Analise esta solicitação pela Central de Moderação da NARA.")
                mod_row = get_mod(int(mod_id))
                files = []
                if mod_row and mod_row["imagem"] and os.path.exists(mod_row["imagem"]):
                    files.append(discord.File(mod_row["imagem"], filename="mod_pendente.png"))
                    embed.set_image(url="attachment://mod_pendente.png")
                await canal.send(
                    embed=embed, files=files,
                    view=ModDecisaoView(mod_row) if mod_row else None,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except Exception:
                import logging
                logging.getLogger("catalogo").exception("Falha ao notificar mod #%s no canal central.", mod_id)
        else:
            await interaction.response.send_message(
                f"✅ Mod **{self.mod_nome.value.strip()}** cadastrado no catálogo. ID: `{mod_id}`.", ephemeral=True,
            )


# ------------------------------------------------------------------ administração de mods

class ModAdminSelect(discord.ui.Select):
    def __init__(self, action, rows):
        self.action = action
        opts = [discord.SelectOption(label=f"{r['mod_nome']}"[:100], value=str(r['id']),
                                     description=f"Port: {r['jogo_nome']}"[:100], emoji="🧩") for r in rows]
        super().__init__(placeholder="Selecione o mod", options=opts, row=0)

    async def callback(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem gerenciar mods.", ephemeral=True)
            return
        mod = get_mod(int(self.values[0]))
        if not mod:
            await interaction.response.send_message("Esse mod não existe mais.", ephemeral=True)
            return
        if self.action == "editar":
            await interaction.response.send_modal(EditarModModal(mod))
        else:
            view = ConfirmarRemocaoModView(mod)
            texto = f"## 🗑️ Remover mod?\n\n**{mod['mod_nome']}**\nJogo: {mod['jogo_nome']}\n\n⚠️ Essa ação não pode ser desfeita."
            await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=view)


class ModAdminListView(discord.ui.View):
    def __init__(self, action, page=0):
        super().__init__(timeout=900)
        self.action, self.page = action, page
        with db() as conn:
            self.total = conn.execute("SELECT COUNT(*) FROM mods").fetchone()[0]
            self.rows = conn.execute("SELECT id, jogo_nome, mod_nome FROM mods ORDER BY jogo_nome COLLATE NOCASE, mod_nome COLLATE NOCASE LIMIT ? OFFSET ?", (25, page * 25)).fetchall()
        if self.rows:
            self.add_item(ModAdminSelect(action, self.rows))
        if page > 0:
            b = discord.ui.Button(label="Anterior", emoji="⬅️", row=1)
            b.callback = self.anterior
            self.add_item(b)
        if (page + 1) * 25 < self.total:
            b = discord.ui.Button(label="Próxima", emoji="➡️", row=1)
            b.callback = self.proxima
            self.add_item(b)
        b = discord.ui.Button(label="Painel de mods", emoji="⬅️", style=discord.ButtonStyle.secondary, row=2)
        b.callback = self.voltar
        self.add_item(b)

    def embed(self):
        verbo = "editar" if self.action == "editar" else "remover"
        desc = "Selecione o mod que deseja " + verbo + " no menu abaixo." if self.rows else "Nenhum mod cadastrado."
        lista = "\n".join(f"• **{r['mod_nome']}** — {r['jogo_nome']}" for r in self.rows[:10])
        if len(self.rows) > 10:
            lista += f"\n• … e mais {len(self.rows) - 10} mod(s) nesta página"
        return f"## 🧩 {verbo.capitalize()} mod\n\n{desc}\n\n{lista}\n\n-# Página {self.page + 1} · {self.total} mod(s)"

    async def anterior(self, interaction):
        v = ModAdminListView(self.action, self.page - 1)
        await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)

    async def proxima(self, interaction):
        v = ModAdminListView(self.action, self.page + 1)
        await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)

    async def voltar(self, interaction):
        await interaction.response.edit_message(content="## 🧩 Administração de mods\nEscolha uma opção no menu abaixo.", embed=None, attachments=[], view=ModAdminView())


class EditarModModal(discord.ui.Modal):
    def __init__(self, mod):
        super().__init__(title=f"Editar mod: {mod['mod_nome']}"[:45])
        self.mod_id = mod['id']
        self.mod = mod
        self.jogo_nome = discord.ui.TextInput(label="Nome do port", max_length=100, default=mod['jogo_nome'])
        self.mod_nome = discord.ui.TextInput(label="Nome do mod", max_length=100, default=mod['mod_nome'])
        self.descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, required=True, max_length=1500, default=(mod['descricao'] or '')[:1500])
        self.link = discord.ui.TextInput(label="Link do mod", max_length=500, default=mod['link'])
        self.add_item(self.jogo_nome)
        self.add_item(self.mod_nome)
        self.add_item(self.descricao)
        self.add_item(self.link)

    async def on_submit(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem editar mods.", ephemeral=True)
            return
        link = self.link.value.strip()
        erro = validar_links(link=link)
        if erro:
            await interaction.response.send_message(erro, ephemeral=True)
            return
        with db() as conn:
            conn.execute("UPDATE mods SET jogo_nome=?, mod_nome=?, descricao=?, link=? WHERE id=?", (self.jogo_nome.value.strip(), self.mod_nome.value.strip(), self.descricao.value.strip(), link, self.mod_id))
        await interaction.response.send_message(f"✅ **Mod atualizado:** {self.mod_nome.value.strip()}\nA imagem atual foi mantida. Para trocá-la, remova o mod e cadastre-o novamente com a nova capa.", ephemeral=True)


class ConfirmarRemocaoModView(discord.ui.View):
    def __init__(self, mod):
        super().__init__(timeout=120)
        self.mod = mod

    @discord.ui.button(label="Confirmar remoção", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem remover mods.", ephemeral=True)
            return
        with db() as conn:
            conn.execute("DELETE FROM mods WHERE id=?", (self.mod['id'],))
        apagar_arquivo(self.mod['imagem'])
        await interaction.response.edit_message(content=f"## 🗑️ Mod removido\n**{self.mod['mod_nome']}** foi removido do catálogo de mods.", embed=None, attachments=[], view=ModAdminView())

    @discord.ui.button(label="Cancelar", emoji="↩️", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="## 🧩 Administração de mods\nEscolha uma opção no menu abaixo.", embed=None, attachments=[], view=ModAdminView())


class ModPendentesSelect(discord.ui.Select):
    def __init__(self, rows):
        options = [discord.SelectOption(label=r["mod_nome"][:100], value=str(r["id"]), description=f"Port: {r['jogo_nome']}"[:100]) for r in rows]
        super().__init__(placeholder="Escolha um mod pendente", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem moderar mods.", ephemeral=True)
            return
        mod = get_mod(int(self.values[0]))
        if not mod or mod["status"] != "pendente":
            await interaction.response.send_message("Esse envio não está mais pendente.", ephemeral=True)
            return
        detalhes = (f"**Port relacionado:** {mod['jogo_nome']}\n**Descrição:** {mod['descricao'] or 'Sem descrição'}\n**Link:** {mod['link']}"
                    + (f"\n**Enviado por:** <@{mod['autor_id']}>" if mod['autor_id'] else ""))
        if mod["imagem"] and os.path.exists(mod["imagem"]):
            emb = discord.Embed(title=mod["mod_nome"], description=detalhes, color=discord.Color.orange())
            emb.set_image(url="attachment://mod_pendente.png")
            await interaction.response.edit_message(embed=emb, attachments=[discord.File(mod["imagem"], filename="mod_pendente.png")], view=ModDecisaoView(mod))
        else:
            texto = f"## 📥 {mod['mod_nome']}\n\n{detalhes}"
            await interaction.response.edit_message(content=texto, embed=None, attachments=[], view=ModDecisaoView(mod))


class ModPendentesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=900)
        with db() as conn:
            self.rows = conn.execute("SELECT id, jogo_nome, mod_nome FROM mods WHERE status='pendente' ORDER BY id DESC LIMIT 25").fetchall()
        if self.rows:
            self.add_item(ModPendentesSelect(self.rows))
        b = discord.ui.Button(label="Voltar", emoji="⬅️", row=1)
        b.callback = self.voltar
        self.add_item(b)

    def embed(self):
        return "## 📥 Mods pendentes\n\n" + ("Selecione um envio no menu abaixo para aprovar ou rejeitar." if self.rows else "Não há mods aguardando aprovação.")

    async def voltar(self, interaction):
        await interaction.response.edit_message(content="## 🧩 Administração de mods\nEscolha uma opção no menu abaixo.", embed=None, attachments=[], view=ModAdminView())


class ModDecisaoView(discord.ui.View):
    def __init__(self, mod):
        super().__init__(timeout=900)
        self.mod = mod

    @discord.ui.button(label="Aprovar", emoji="✅", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem moderar mods.", ephemeral=True); return
        with db() as conn:
            cur = conn.execute(
                "UPDATE mods SET status='aprovado' WHERE id=? AND status='pendente'", (self.mod["id"],)
            )
        if cur.rowcount != 1:
            await interaction.response.send_message("Esse envio já foi processado.", ephemeral=True)
            return
        drop = await conceder_drop_catalogo("mod", self.mod)
        recompensa = texto_recompensa_catalogo(drop)
        await avisar_autor(
            self.mod,
            f"✅ Seu mod **{self.mod['mod_nome']}** foi aprovado e já aparece no catálogo!{recompensa}",
        )
        await interaction.response.edit_message(
            content=f"## ✅ Mod aprovado\n**{self.mod['mod_nome']}** já aparece no catálogo de mods.{recompensa}",
            embed=None, attachments=[], view=ModPendentesView(),
        )

    @discord.ui.button(label="Rejeitar", emoji="❌", style=discord.ButtonStyle.danger)
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem moderar mods.", ephemeral=True); return
        with db() as conn:
            conn.execute("DELETE FROM mods WHERE id=?", (self.mod["id"],))
        apagar_arquivo(self.mod["imagem"])
        await interaction.response.edit_message(content=f"## ❌ Mod rejeitado\n**{self.mod['mod_nome']}** foi removido dos envios.", embed=None, attachments=[], view=ModPendentesView())


class ModAdminView(discord.ui.View):
    """Ações de mods reunidas em um menu, sem cascata de botões."""
    def __init__(self):
        super().__init__(timeout=900)
        n = contar_mods_pendentes()
        options = [
            discord.SelectOption(label="Adicionar mod", value="add", emoji="➕", description="Cadastrar um mod diretamente"),
            discord.SelectOption(label="Editar mod", value="edit", emoji="✏️", description="Alterar dados de um mod existente"),
            discord.SelectOption(label="Remover mod", value="remove", emoji="🗑️", description="Excluir um mod do catálogo"),
            discord.SelectOption(label=f"Envios pendentes ({n})", value="pending", emoji="📥", description="Aprovar ou rejeitar envios dos membros"),
            discord.SelectOption(label="Voltar ao painel principal", value="back", emoji="⬅️", description="Voltar às opções de ports e configuração"),
        ]
        sel = discord.ui.Select(placeholder="Gerenciar catálogo de mods...", options=options)
        sel.callback = self.escolher
        self.add_item(sel)

    async def escolher(self, interaction: discord.Interaction):
        if not eh_admin(interaction):
            await interaction.response.send_message("⛔ Apenas administradores podem gerenciar mods.", ephemeral=True)
            return
        action = interaction.data.get("values", [""])[0]
        if action == "add":
            await interaction.response.send_modal(AdicionarModModal(publico=False))
        elif action == "edit":
            v = ModAdminListView("editar")
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "remove":
            v = ModAdminListView("remover")
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "pending":
            v = ModPendentesView()
            await interaction.response.edit_message(content=v.embed(), embed=None, attachments=[], view=v)
        elif action == "back":
            await interaction.response.edit_message(content=admin_content(), embed=None, attachments=[], view=AdminView())





class CatalogoIntegrado(commands.Cog):
    """Catálogo de ports e mods incorporado à única aplicação NARA."""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def cog_load(self):
        global bot
        bot = self.bot
        init_db()
        # View persistente para mensagens antigas do catálogo que ainda estejam publicadas.
        self.bot.add_view(MainView())

    async def abrir_membros(self, interaction: discord.Interaction, callback_voltar=None):
        """Abre o catálogo dentro da mensagem da Nara quando há caminho de retorno."""
        view = MainView(callback_voltar=callback_voltar)
        if callback_voltar is not None:
            await interaction.response.edit_message(content=main_content(), embed=None, attachments=[], view=view)
        else:
            await interaction.response.send_message(content=main_content(), view=view, ephemeral=True)

    async def publicar_painel_publico(self, interaction: discord.Interaction, canal):
        if not eh_admin(interaction):
            return await interaction.response.send_message("Acesso restrito à equipe.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        chave = f"catalogo_msg_{canal.id}"
        mensagem = None
        atual_id = get_config(chave)
        if atual_id:
            try:
                candidata = await canal.fetch_message(int(atual_id))
                if candidata.author.id == self.bot.user.id:
                    mensagem = candidata
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
                mensagem = None
        if mensagem is None and hasattr(canal, "history"):
            try:
                async for candidata in canal.history(limit=100):
                    if candidata.author.id == self.bot.user.id and any(t in (candidata.content or "") for t in ("🎮 Catálogo de Jogos", "🎮 Ports & Mods")):
                        mensagem = candidata
                        break
            except (discord.Forbidden, discord.HTTPException):
                mensagem = None
        if mensagem:
            await mensagem.edit(content=main_content(), embed=None, attachments=[], view=MainView())
            acao = "atualizado"
        else:
            mensagem = await canal.send(content=main_content(), view=MainView())
            acao = "publicado"
        set_config(chave, str(mensagem.id))
        await interaction.edit_original_response(content=f"Painel de catálogo {acao} em {canal.mention}.")

    async def status(self):
        with db() as conn:
            jogos = conn.execute("SELECT COUNT(*) FROM jogos WHERE status='aprovado'").fetchone()[0]
            jogos_pendentes = conn.execute("SELECT COUNT(*) FROM jogos WHERE status='pendente'").fetchone()[0]
            mods = conn.execute("SELECT COUNT(*) FROM mods WHERE status='aprovado'").fetchone()[0]
            mods_pendentes = conn.execute("SELECT COUNT(*) FROM mods WHERE status='pendente'").fetchone()[0]
        return {"jogos": jogos, "jogos_pendentes": jogos_pendentes, "mods": mods, "mods_pendentes": mods_pendentes}


async def setup(bot):
    """Ponto de entrada exigido pelo carregador de extensões do discord.py."""
    await bot.add_cog(CatalogoIntegrado(bot))
