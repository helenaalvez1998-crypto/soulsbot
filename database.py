import asyncio
import os
from contextlib import asynccontextmanager
import aiosqlite
from levels import nivel_por_xp

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    xp        INTEGER NOT NULL DEFAULT 0,
    denarios  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS platinas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    game        TEXT NOT NULL,
    platform    TEXT NOT NULL,
    earned_at   TEXT NOT NULL,
    proof_url   TEXT NOT NULL,
    proof_msg_id INTEGER,
    catalog_game_id INTEGER,
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
    reviewer_id INTEGER,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_plat_user ON platinas(user_id, status);

-- Sistema de runs Soulslike integrado
CREATE TABLE IF NOT EXISTS sl_games (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    catalog_game_id INTEGER
);
CREATE TABLE IF NOT EXISTS sl_challenges (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE COLLATE NOCASE,
    rules   TEXT NOT NULL DEFAULT '',
    game_id INTEGER
);
CREATE TABLE IF NOT EXISTS sl_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    game_id       INTEGER NOT NULL,
    challenge_id  INTEGER NOT NULL,
    build         TEXT NOT NULL DEFAULT '',
    seconds       INTEGER NOT NULL,
    proof_msg_id  INTEGER,
    proof_url     TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'pending',
    reviewer_id   INTEGER,
    reject_reason TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sl_cat ON sl_runs(game_id, challenge_id, status);
CREATE TABLE IF NOT EXISTS platina_proofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platina_id INTEGER NOT NULL,
    proof_url TEXT NOT NULL,
    media_type TEXT,
    FOREIGN KEY(platina_id) REFERENCES platinas(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS zerados (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    game             TEXT NOT NULL,
    platform         TEXT NOT NULL,
    finished_at      TEXT NOT NULL,
    comment          TEXT NOT NULL DEFAULT '',
    xp_awarded       INTEGER NOT NULL DEFAULT 0,
    denarios_awarded INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'approved', -- pending | approved | rejected
    reviewer_id      INTEGER,
    proof_msg_id     INTEGER,
    approved_at      TEXT,
    catalog_game_id INTEGER,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_zer_user ON zerados(user_id);
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS perfis (
    user_id     INTEGER PRIMARY KEY,
    thread_id   INTEGER NOT NULL,
    card_msg_id INTEGER,
    tagline     TEXT NOT NULL DEFAULT '',
    bio         TEXT NOT NULL DEFAULT '',
    fav_game    TEXT NOT NULL DEFAULT '',
    theme       TEXT NOT NULL DEFAULT 'Ouro',
    links       TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS inventario (
    user_id    INTEGER NOT NULL,
    item       TEXT NOT NULL,
    tipo       TEXT NOT NULL,
    equipado   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, item)
);
CREATE INDEX IF NOT EXISTS idx_inventario_user_tipo ON inventario(user_id, tipo, equipado);

CREATE TABLE IF NOT EXISTS games_catalog (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name            TEXT NOT NULL,
    name_original   TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'review', -- review | ready | archived
    platforms_json  TEXT NOT NULL DEFAULT '[]',
    cover_url       TEXT NOT NULL DEFAULT '',
    sources_json    TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS game_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL,
    category        TEXT NOT NULL,
    name_pt         TEXT NOT NULL,
    name_original   TEXT NOT NULL DEFAULT '',
    description_pt  TEXT NOT NULL DEFAULT '',
    location_pt     TEXT NOT NULL DEFAULT '',
    acquisition_pt  TEXT NOT NULL DEFAULT '',
    dlc             TEXT NOT NULL DEFAULT '',
    ng_cycle        TEXT NOT NULL DEFAULT '',
    missable        INTEGER NOT NULL DEFAULT 0,
    source_url      TEXT NOT NULL DEFAULT '',
    verified        INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, category, name_original),
    FOREIGN KEY(game_id) REFERENCES games_catalog(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_game_items_game_category ON game_items(game_id, category);

CREATE TABLE IF NOT EXISTS game_trophies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL,
    name_pt         TEXT NOT NULL,
    name_original   TEXT NOT NULL DEFAULT '',
    description_pt  TEXT NOT NULL DEFAULT '',
    grade           TEXT NOT NULL DEFAULT '',
    is_platinum     INTEGER NOT NULL DEFAULT 0,
    dlc             TEXT NOT NULL DEFAULT '',
    missable        INTEGER NOT NULL DEFAULT 0,
    hidden          INTEGER NOT NULL DEFAULT 0,
    story_related   INTEGER NOT NULL DEFAULT 0,
    source_url      TEXT NOT NULL DEFAULT '',
    verified        INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, name_original),
    FOREIGN KEY(game_id) REFERENCES games_catalog(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_game_trophies_game ON game_trophies(game_id);

CREATE TABLE IF NOT EXISTS trophy_requirements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trophy_id       INTEGER NOT NULL,
    item_id         INTEGER,
    description_pt  TEXT NOT NULL DEFAULT '',
    quantity        INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(trophy_id) REFERENCES game_trophies(id) ON DELETE CASCADE,
    FOREIGN KEY(item_id) REFERENCES game_items(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_game_progress (
    user_id         INTEGER NOT NULL,
    game_id         INTEGER NOT NULL,
    last_viewed     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, game_id),
    FOREIGN KEY(game_id) REFERENCES games_catalog(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_collected_items (
    user_id         INTEGER NOT NULL,
    item_id         INTEGER NOT NULL,
    obtained        INTEGER NOT NULL DEFAULT 1,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, item_id),
    FOREIGN KEY(item_id) REFERENCES game_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_trophy_progress (
    user_id         INTEGER NOT NULL,
    trophy_id       INTEGER NOT NULL,
    completed       INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, trophy_id),
    FOREIGN KEY(trophy_id) REFERENCES game_trophies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS game_aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL,
    alias           TEXT NOT NULL COLLATE NOCASE,
    alias_norm      TEXT NOT NULL COLLATE NOCASE,
    source          TEXT NOT NULL DEFAULT 'ai_research',
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, alias_norm),
    FOREIGN KEY(game_id) REFERENCES games_catalog(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_game_alias_norm ON game_aliases(alias_norm);

CREATE TABLE IF NOT EXISTS catalog_search_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    kind            TEXT NOT NULL DEFAULT 'identify',   -- identify | research
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_catalog_search_user_time
    ON catalog_search_requests(user_id, created_at);

CREATE TABLE IF NOT EXISTS catalog_import_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requested_by    INTEGER NOT NULL,
    game_name       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
    progress        INTEGER NOT NULL DEFAULT 0,
    details         TEXT NOT NULL DEFAULT '',
    candidate_json  TEXT NOT NULL DEFAULT '',
    dedupe_key      TEXT NOT NULL DEFAULT '',
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT NOT NULL DEFAULT '',
    game_id         INTEGER,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS catalog_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER,
    game_name   TEXT NOT NULL DEFAULT '',
    actor_id    INTEGER NOT NULL DEFAULT 0,
    action      TEXT NOT NULL,
    details     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_catalog_history_game ON catalog_history(game_id, id);

CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id   INTEGER NOT NULL,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Contribuições editoriais e interações sociais da comunidade NARA
CREATE TABLE IF NOT EXISTS community_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    game_name TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    sources TEXT NOT NULL DEFAULT '',
    spoiler_level TEXT NOT NULL DEFAULT 'none',
    challenge_mode TEXT NOT NULL DEFAULT 'individual',
    challenge_goal INTEGER NOT NULL DEFAULT 0,
    origin_sector TEXT NOT NULL DEFAULT '',
    origin_channel_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    reviewer_id INTEGER,
    review_note TEXT NOT NULL DEFAULT '',
    xp_awarded INTEGER NOT NULL DEFAULT 0,
    published_channel_id INTEGER,
    published_message_id INTEGER,
    published_thread_id INTEGER,
    applied_target_type TEXT NOT NULL DEFAULT '',
    applied_target_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_community_contrib_status
    ON community_contributions(guild_id, status, created_at, id);
CREATE INDEX IF NOT EXISTS idx_community_contrib_author
    ON community_contributions(guild_id, user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_community_contrib_kind
    ON community_contributions(guild_id, kind, status);

CREATE TABLE IF NOT EXISTS community_xp_awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribution_id INTEGER NOT NULL UNIQUE,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    xp INTEGER NOT NULL DEFAULT 0,
    awarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(contribution_id) REFERENCES community_contributions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_community_xp_weekly
    ON community_xp_awards(guild_id, user_id, awarded_at);

CREATE TABLE IF NOT EXISTS community_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reaction_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, target_type, target_id, user_id, reaction_key)
);
CREATE INDEX IF NOT EXISTS idx_community_interactions_target
    ON community_interactions(guild_id, target_type, target_id, reaction_key);

CREATE TABLE IF NOT EXISTS community_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    thread_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    UNIQUE(guild_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_community_posts_message ON community_posts(message_id);

CREATE TABLE IF NOT EXISTS community_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    reporter_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    reviewer_id INTEGER,
    review_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_community_reports_status ON community_reports(guild_id,status,created_at,id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_community_reports_open_unique
    ON community_reports(guild_id,reporter_id,target_type,target_id) WHERE status='pending';

CREATE TABLE IF NOT EXISTS community_faq_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contribution_id INTEGER NOT NULL UNIQUE,
    guild_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(contribution_id) REFERENCES community_contributions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_community_faq_guild_status ON community_faq_entries(guild_id,status,created_at);

CREATE TABLE IF NOT EXISTS community_guestbook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    visitor_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(owner_id <> visitor_id)
);
CREATE INDEX IF NOT EXISTS idx_community_guestbook_owner ON community_guestbook(guild_id,owner_id,created_at DESC);

CREATE TABLE IF NOT EXISTS community_bookmarks (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(guild_id, user_id, target_type, target_id)
);

CREATE TABLE IF NOT EXISTS community_follows (
    guild_id INTEGER NOT NULL,
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(guild_id, follower_id, followed_id),
    CHECK(follower_id <> followed_id)
);

CREATE TABLE IF NOT EXISTS community_honors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    honor_key TEXT NOT NULL,
    week_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, from_user_id, week_key),
    CHECK(from_user_id <> to_user_id)
);
CREATE INDEX IF NOT EXISTS idx_community_honors_recipient
    ON community_honors(guild_id, to_user_id, week_key);

CREATE TABLE IF NOT EXISTS community_challenge_participants (
    guild_id INTEGER NOT NULL,
    contribution_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'joined',
    progress_note TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(guild_id, contribution_id, user_id),
    FOREIGN KEY(contribution_id) REFERENCES community_contributions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS community_activity_preferences (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    platinas INTEGER NOT NULL DEFAULT 1,
    zerados INTEGER NOT NULL DEFAULT 1,
    runs INTEGER NOT NULL DEFAULT 1,
    lore INTEGER NOT NULL DEFAULT 1,
    guides INTEGER NOT NULL DEFAULT 1,
    challenges INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(guild_id, user_id)
);

"""


# Colunas adicionadas depois da primeira versão: aplicadas em bancos já existentes.
MIGRACOES_COLUNAS = {
    "game_trophies": {
        "dlc": "TEXT NOT NULL DEFAULT ''",
        "missable": "INTEGER NOT NULL DEFAULT 0",
        "hidden": "INTEGER NOT NULL DEFAULT 0",
        "story_related": "INTEGER NOT NULL DEFAULT 0",
    },
    "catalog_search_requests": {"kind": "TEXT NOT NULL DEFAULT 'identify'"},
    "catalog_import_jobs": {
        "candidate_json": "TEXT NOT NULL DEFAULT ''",
        "dedupe_key": "TEXT NOT NULL DEFAULT ''",
        "attempts": "INTEGER NOT NULL DEFAULT 0",
        "last_error": "TEXT NOT NULL DEFAULT ''",
        "game_id": "INTEGER",
    },
    "platinas": {"catalog_game_id": "INTEGER"},
    "zerados": {
        "catalog_game_id": "INTEGER",
        # Registros anteriores continuam aprovados. Os novos entram como pending.
        "status": "TEXT NOT NULL DEFAULT 'approved'",
        "reviewer_id": "INTEGER",
        "proof_msg_id": "INTEGER",
        "approved_at": "TEXT",
        "source_platina_id": "INTEGER",
    },
    "sl_games": {"catalog_game_id": "INTEGER"},
    "sl_challenges": {
        # NULL mantém compatibilidade com desafios globais já cadastrados.
        "game_id": "INTEGER",
    },
    "community_contributions": {
        "applied_target_type": "TEXT NOT NULL DEFAULT ''",
        "applied_target_id": "INTEGER",
        "challenge_mode": "TEXT NOT NULL DEFAULT 'individual'",
        "challenge_goal": "INTEGER NOT NULL DEFAULT 0",
        "origin_sector": "TEXT NOT NULL DEFAULT ''",
        "origin_channel_id": "INTEGER",
    },
    "community_challenge_participants": {
        "evidence": "TEXT NOT NULL DEFAULT ''",
    },
    "community_posts": {
        "is_hidden": "INTEGER NOT NULL DEFAULT 0",
    },
}

# Índices que precisam das colunas acima; criados depois das migrações.
# Garante no máximo UM pedido ativo por jogo: repetir a pesquisa reaproveita o registro.
INDICES_POS_MIGRACAO = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalog_jobs_dedupe_ativo
    ON catalog_import_jobs(dedupe_key)
    WHERE dedupe_key <> '' AND status NOT IN ('published','rejected','resolved');
CREATE INDEX IF NOT EXISTS idx_catalog_jobs_status ON catalog_import_jobs(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_catalog_search_kind_time ON catalog_search_requests(kind, created_at);
CREATE INDEX IF NOT EXISTS idx_sl_challenges_game ON sl_challenges(game_id, name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_zerados_source_platina_unique
    ON zerados(source_platina_id) WHERE source_platina_id IS NOT NULL;
"""


class DatabaseSession:
    """Fachada mínima para operações dentro de uma conexão transacional isolada."""
    def __init__(self, conn):
        self.conn = conn

    async def _one(self, sql, args=()):
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchone()

    async def _all(self, sql, args=()):
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchall()


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        # SQLite :memory: usa uma única conexão compartilhada. Serializar transações
        # evita que duas corrotinas intercalem BEGIN/COMMIT na mesma conexão.
        self._memory_lock = asyncio.Lock()

    async def connect(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.conn = await aiosqlite.connect(self.path, timeout=10)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA busy_timeout = 10000")
        if self.path != ":memory:":
            await self.conn.execute("PRAGMA journal_mode = WAL")
            await self.conn.execute("PRAGMA synchronous = NORMAL")
        await self.conn.executescript(SCHEMA)
        # Migrações incrementais para bancos já existentes.
        cols = [r["name"] for r in await self._all("PRAGMA table_info(platinas)")]
        if "proof_msg_id" not in cols:
            await self.conn.execute("ALTER TABLE platinas ADD COLUMN proof_msg_id INTEGER")
        # Um alias conflitante não pode decidir qual jogo é o correto. Descarta aliases
        # ambíguos antigos antes de impor unicidade global.
        await self.conn.execute(
            """DELETE FROM game_aliases WHERE alias_norm IN (
                 SELECT alias_norm FROM game_aliases GROUP BY alias_norm
                 HAVING COUNT(DISTINCT game_id) > 1
               )"""
        )
        await self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_game_alias_norm_unique ON game_aliases(alias_norm)"
        )
        for tabela, colunas in MIGRACOES_COLUNAS.items():
            existentes = {r["name"] for r in await self._all(f"PRAGMA table_info({tabela})")}
            for coluna, ddl in colunas.items():
                if coluna not in existentes:
                    await self.conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {ddl}")
        # Os registros antigos de zerados foram lançados automaticamente; preserva-os
        # como aprovados e marca a data histórica para o limite diário.
        await self.conn.execute(
            "UPDATE zerados SET approved_at=created_at WHERE status='approved' AND approved_at IS NULL"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_zer_status_user ON zerados(status, user_id)"
        )
        # Antes de impor unicidade, mantém só o pedido ativo mais recente de cada chave.
        await self.conn.execute(
            """UPDATE catalog_import_jobs SET dedupe_key=''
               WHERE dedupe_key <> '' AND status NOT IN ('published','rejected','resolved')
                 AND id NOT IN (SELECT MAX(id) FROM catalog_import_jobs
                                WHERE dedupe_key <> '' AND status NOT IN ('published','rejected','resolved')
                                GROUP BY dedupe_key)"""
        )
        # Vincula registros históricos ao catálogo central por nome/alias exato.
        # Não usa similaridade para evitar associar jogos diferentes.
        session = DatabaseSession(self.conn)
        for tabela, coluna, origem in (
            ("platinas", "game", "historico_platina"),
            ("zerados", "game", "historico_zerado"),
            ("sl_games", "name", "historico_runs"),
        ):
            async with self.conn.execute(
                f"SELECT id, {coluna} AS nome FROM {tabela} WHERE {coluna} IS NOT NULL AND TRIM({coluna})<>''"
            ) as cur:
                registros = await cur.fetchall()
            coluna_ref = "catalog_game_id"
            for registro in registros:
                game_id = await self._resolver_jogo_catalogo_tx(session, registro["nome"], origem)
                await self.conn.execute(
                    f"UPDATE {tabela} SET {coluna_ref}=? WHERE id=? AND {coluna_ref} IS NULL",
                    (game_id, int(registro["id"])),
                )
        await self.conn.executescript(INDICES_POS_MIGRACAO)
        await self.conn.commit()

    @asynccontextmanager
    async def transaction(self):
        """Transação isolada; serializa o modo :memory: que compartilha uma conexão."""
        # Não criar silenciosamente um banco vazio caso a inicialização falhe.
        if self.conn is None:
            raise RuntimeError("Database.connect() precisa ser chamado antes de transaction().")
        memory_db = self.path == ":memory:"
        if memory_db:
            # Não abrir uma segunda conexão para :memory_: ela apontaria para outro
            # banco. O lock impede BEGIN/COMMIT concorrentes na conexão compartilhada.
            await self._memory_lock.acquire()
            conn = self.conn
            owned = False
        else:
            conn = await aiosqlite.connect(self.path, timeout=10)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA busy_timeout = 10000")
            owned = True
        try:
            if conn is None:
                raise RuntimeError("Database.connect() precisa ser chamado antes de transaction().")
            await conn.execute("BEGIN IMMEDIATE")
            yield DatabaseSession(conn)
            await conn.commit()
        except BaseException:
            if conn is not None:
                await conn.rollback()
            raise
        finally:
            if owned:
                await conn.close()
            if memory_db:
                self._memory_lock.release()

    async def close(self):
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

    async def _one(self, sql, args=()):
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchone()

    async def _all(self, sql, args=()):
        async with self.conn.execute(sql, args) as cur:
            return await cur.fetchall()

    async def log(self, actor_id: int, action: str, details: str = ""):
        await self.conn.execute(
            "INSERT INTO logs(actor_id, action, details) VALUES (?,?,?)",
            (actor_id, action, details),
        )
        await self.conn.commit()

    # ---------- identidade central de jogos ----------
    @staticmethod
    def normalizar_nome_jogo(nome: str) -> str:
        """Normalização conservadora: remove acentos/pontuação, preserva palavras e números."""
        valor = unicodedata.normalize("NFKD", str(nome or "").strip().casefold())
        valor = "".join(ch for ch in valor if not unicodedata.combining(ch))
        valor = re.sub(r"[^a-z0-9]+", " ", valor)
        return re.sub(r"\\s+", " ", valor).strip()

    async def _resolver_jogo_catalogo_tx(self, tx, nome: str, source: str = "registro"):
        """Resolve apenas nome/alias exato. Similaridade nunca associa automaticamente."""
        original = str(nome or "").strip()[:160]
        norm = self.normalizar_nome_jogo(original)
        if not norm:
            return None
        alias = await tx._one(
            "SELECT game_id FROM game_aliases WHERE alias_norm=? COLLATE NOCASE LIMIT 1",
            (norm,),
        )
        if alias:
            game = await tx._one("SELECT id FROM games_catalog WHERE id=?", (int(alias["game_id"]),))
            if game:
                await tx.conn.execute(
                    "INSERT OR IGNORE INTO game_aliases(game_id,alias,alias_norm,source) VALUES (?,?,?,?)",
                    (int(game["id"]), original, norm, str(source)[:40]),
                )
                return int(game["id"])
        slug = norm.replace(" ", "-")
        game = await tx._one("SELECT id FROM games_catalog WHERE slug=? COLLATE NOCASE", (slug,))
        if game:
            game_id = int(game["id"])
        else:
            cur = await tx.conn.execute(
                """INSERT INTO games_catalog(slug,name,name_original,status)
                   VALUES (?,?,?,'review')""",
                (slug[:180], original[:120], original),
            )
            game_id = int(cur.lastrowid)
        await tx.conn.execute(
            "INSERT OR IGNORE INTO game_aliases(game_id,alias,alias_norm,source) VALUES (?,?,?,?)",
            (game_id, original, norm, str(source)[:40]),
        )
        return game_id

    async def resolver_jogo_catalogo(self, nome: str, source: str = "registro"):
        """Resolve nome exato/alias e cria registro em revisão quando ainda não existe."""
        async with self.transaction() as tx:
            return await self._resolver_jogo_catalogo_tx(tx, nome, source)

    async def adicionar_alias_jogo(self, game_id: int, alias: str, source: str = "admin"):
        original = str(alias or "").strip()[:160]
        norm = self.normalizar_nome_jogo(original)
        if not norm:
            raise ValueError("O alias não pode ficar vazio.")
        async with self.transaction() as tx:
            conflito = await tx._one(
                "SELECT game_id FROM game_aliases WHERE alias_norm=? COLLATE NOCASE",
                (norm,),
            )
            if conflito and int(conflito["game_id"]) != int(game_id):
                raise ValueError("Esse nome alternativo já pertence a outro jogo. Confirme a identidade antes de associar.")
            await tx.conn.execute(
                "INSERT OR IGNORE INTO game_aliases(game_id,alias,alias_norm,source) VALUES (?,?,?,?)",
                (int(game_id), original, norm, str(source)[:40]),
            )
            await tx.conn.execute(
                "UPDATE games_catalog SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (int(game_id),),
            )

    async def atualizar_capa_jogo(self, game_id: int, cover_url: str, source: str = ""):
        url = str(cover_url or "").strip()[:1000]
        if url and not url.startswith(("https://", "http://")):
            raise ValueError("A capa precisa usar uma URL HTTP(S).")
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE games_catalog SET cover_url=?, sources_json=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (url, str(source or "")[:1000], int(game_id)),
            )
            return cur.rowcount == 1

    async def buscar_jogos_catalogo(self, termo: str, limite: int = 8):
        norm = self.normalizar_nome_jogo(termo)
        if not norm:
            return []
        # Sugestões são apenas informativas; não fazem associação automática.
        rows = await self._all(
            """SELECT DISTINCT g.id,g.name,g.cover_url,g.status
               FROM games_catalog g LEFT JOIN game_aliases a ON a.game_id=g.id
               WHERE lower(g.name) LIKE ? OR a.alias_norm LIKE ?
               ORDER BY g.name LIMIT ?""",
            (f"%{norm}%", f"%{norm}%", max(1, min(int(limite), 20))),
        )
        return rows

    # ---------- usuários ----------
    async def get_user(self, user_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        return await self._one("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def add_reward(self, user_id: int, xp: int, denarios: int):
        """Aplica XP/Denários atomicamente; devolve nível antigo, novo e XP total."""
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            user = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            antigo = nivel_por_xp(int(user["xp"]))
            await tx.conn.execute(
                "UPDATE users SET xp=MAX(0,xp+?), denarios=MAX(0,denarios+?) WHERE user_id=?",
                (int(xp), int(denarios), user_id),
            )
            atualizado = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            novo_xp = int(atualizado["xp"])
            return antigo, nivel_por_xp(novo_xp), novo_xp

    async def aprovar_run_com_recompensa(self, run_id: int, reviewer_id: int):
        """Aprova uma run e credita XP base/bônus na mesma transação indivisível.

        A regra de recorde é calculada sob BEGIN IMMEDIATE para que dois moderadores
        não concedam bônus duplicado ao aprovar runs simultaneamente.
        """
        async with self.transaction() as tx:
            run = await tx._one(
                "SELECT * FROM sl_runs WHERE id=? AND status='pending'", (int(run_id),)
            )
            if run is None:
                return None
            global_best = await tx._one(
                "SELECT MIN(seconds) AS best FROM sl_runs WHERE status='approved' AND game_id=? AND challenge_id=?",
                (run["game_id"], run["challenge_id"]),
            )
            personal_best = await tx._one(
                "SELECT MIN(seconds) AS best FROM sl_runs WHERE status='approved' AND user_id=? AND game_id=? AND challenge_id=?",
                (run["user_id"], run["game_id"], run["challenge_id"]),
            )
            approved_count = await tx._one(
                "SELECT COUNT(*) AS total FROM sl_runs WHERE status='approved' AND user_id=? AND game_id=? AND challenge_id=?",
                (run["user_id"], run["game_id"], run["challenge_id"]),
            )
            antes_global = global_best["best"] if global_best else None
            antes_pessoal = personal_best["best"] if personal_best else None
            is_record = antes_global is None or int(run["seconds"]) < int(antes_global)
            improved_personal = antes_pessoal is None or int(run["seconds"]) < int(antes_pessoal)
            cur = await tx.conn.execute(
                "UPDATE sl_runs SET status='approved', reviewer_id=? WHERE id=? AND status='pending'",
                (int(reviewer_id), int(run_id)),
            )
            if cur.rowcount != 1:
                return None

            xp_awarded = 100 + (100 if is_record else 0)
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (run["user_id"],))
            user_before = await tx._one("SELECT xp FROM users WHERE user_id=?", (run["user_id"],))
            xp_before = int(user_before["xp"] or 0)
            await tx.conn.execute(
                "UPDATE users SET xp=MAX(0,xp+?) WHERE user_id=?", (xp_awarded, run["user_id"])
            )
            user_after = await tx._one("SELECT xp FROM users WHERE user_id=?", (run["user_id"],))
            xp_after = int(user_after["xp"] or 0)
            return {
                "run": dict(run),
                "is_record": bool(is_record),
                "improved_personal": bool(improved_personal),
                "previous_personal_best": antes_pessoal,
                "approved_count_before": int(approved_count["total"] or 0),
                "xp_awarded": xp_awarded,
                "xp_before": xp_before,
                "xp_after": xp_after,
                "old_level": nivel_por_xp(xp_before),
                "new_level": nivel_por_xp(xp_after),
            }

    # ---------- loja cosmética ----------
    async def inventario_do_usuario(self, user_id: int):
        """Lista os itens comprados pelo usuário, incluindo seu estado de equipamento."""
        return await self._all(
            "SELECT item, tipo, equipado FROM inventario WHERE user_id=? ORDER BY tipo, item",
            (user_id,),
        )

    async def comprar_item(self, user_id: int, item: str, tipo: str, preco: int) -> str:
        """Compra única com débito/inserção indivisíveis, inclusive sob cliques simultâneos."""
        preco = int(preco)
        if preco < 0:
            raise ValueError("Preço não pode ser negativo.")
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            existente = await tx._one(
                "SELECT 1 FROM inventario WHERE user_id=? AND item=?", (user_id, item)
            )
            if existente:
                return "ja_tem"
            cur = await tx.conn.execute(
                "UPDATE users SET denarios=denarios-? WHERE user_id=? AND denarios>=?",
                (preco, user_id, preco),
            )
            if cur.rowcount != 1:
                return "sem_saldo"
            await tx.conn.execute(
                "INSERT INTO inventario(user_id,item,tipo,equipado) VALUES (?,?,?,0)",
                (user_id, item, tipo),
            )
            return "ok"

    async def equipar_item(self, user_id: int, item: str, tipo: str) -> bool:
        """Equipa item próprio e desativa itens do mesmo tipo na mesma transação."""
        async with self.transaction() as tx:
            existente = await tx._one(
                "SELECT 1 FROM inventario WHERE user_id=? AND item=? AND tipo=?",
                (user_id, item, tipo),
            )
            if not existente:
                return False
            await tx.conn.execute(
                "UPDATE inventario SET equipado=0 WHERE user_id=? AND tipo=?", (user_id, tipo)
            )
            cur = await tx.conn.execute(
                "UPDATE inventario SET equipado=1 WHERE user_id=? AND item=? AND tipo=?",
                (user_id, item, tipo),
            )
            return cur.rowcount == 1

    async def desequipar_tipo(self, user_id: int, tipo: str):
        await self.conn.execute(
            "UPDATE inventario SET equipado=0 WHERE user_id=? AND tipo=?", (user_id, tipo)
        )
        await self.conn.commit()

    async def posicao_xp(self, xp: int) -> int:
        row = await self._one("SELECT COUNT(*)+1 AS p FROM users WHERE xp > ?", (xp,))
        return row["p"]

    # ---------- platinas ----------
    async def platina_duplicada(self, user_id: int, game: str, platform: str) -> bool:
        row = await self._one(
            """SELECT 1 FROM platinas WHERE user_id=? AND lower(game)=lower(?)
               AND lower(platform)=lower(?) AND status IN ('pending','approved')""",
            (user_id, game, platform),
        )
        return row is not None

    async def criar_platina(self, user_id, game, platform, earned_at, proof_url, proof_msg_id=None) -> int:
        async with self.transaction() as tx:
            catalog_id = await self._resolver_jogo_catalogo_tx(tx, game, "platina")
            cur = await tx.conn.execute(
                "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url, proof_msg_id, catalog_game_id) VALUES (?,?,?,?,?,?,?)",
                (user_id, game, platform, earned_at, proof_url, proof_msg_id, catalog_id),
            )
        return cur.lastrowid

    async def criar_platina_unica(self, user_id, game, platform, earned_at, proof_url, proof_msg_id=None):
        """Cria registro sob BEGIN IMMEDIATE para impedir duplicata em cliques simultâneos."""
        async with self.transaction() as tx:
            existente = await tx._one(
                """SELECT id FROM platinas WHERE user_id=? AND lower(game)=lower(?)
                   AND lower(platform)=lower(?) AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if existente:
                return None
            catalog_id = await self._resolver_jogo_catalogo_tx(tx, game, "platina")
            cur = await tx.conn.execute(
                "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url, proof_msg_id, catalog_game_id) VALUES (?,?,?,?,?,?,?)",
                (user_id, game, platform, earned_at, proof_url, proof_msg_id, catalog_id),
            )
            return cur.lastrowid

    async def excluir_platina_pendente(self, platina_id: int):
        async with self.transaction() as tx:
            await tx.conn.execute("DELETE FROM platinas WHERE id=? AND status='pending'", (platina_id,))

    async def adicionar_comprovantes(self, platina_id: int, comprovantes):
        """Armazena URLs de todos os comprovantes associados à platina."""
        for url, media_type in comprovantes:
            await self.conn.execute(
                "INSERT INTO platina_proofs(platina_id, proof_url, media_type) VALUES (?,?,?)",
                (platina_id, url, media_type),
            )
        await self.conn.commit()

    async def comprovantes_da_platina(self, platina_id: int):
        return await self._all(
            "SELECT proof_url, media_type FROM platina_proofs WHERE platina_id=? ORDER BY id",
            (platina_id,),
        )

    async def get_platina(self, platina_id: int):
        return await self._one("SELECT * FROM platinas WHERE id=?", (platina_id,))

    async def set_status(self, platina_id: int, status: str, reviewer_id: int):
        await self.conn.execute(
            "UPDATE platinas SET status=?, reviewer_id=? WHERE id=?",
            (status, reviewer_id, platina_id),
        )
        await self.conn.commit()

    async def decidir_platina(self, platina_id: int, status: str, reviewer_id: int) -> bool:
        """Registra a decisão somente se a platina ainda estiver pendente."""
        if status not in ("approved", "rejected"):
            return False
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                "UPDATE platinas SET status=?, reviewer_id=? WHERE id=? AND status='pending'",
                (status, reviewer_id, platina_id),
            )
            return cur.rowcount == 1

    async def aprovar_platina_com_recompensa(
        self, platina_id: int, reviewer_id: int, xp: int, denarios: int,
        xp_zerado: int = 0, denarios_zerado: int = 0, limite_zerados: int = 0,
    ):
        """Aprova a platina e sincroniza o zerado, com recompensas numa única transação."""
        async with self.transaction() as tx:
            platina = await tx._one("SELECT * FROM platinas WHERE id=?", (platina_id,))
            if platina is None or platina["status"] != "pending":
                return None
            cur = await tx.conn.execute(
                "UPDATE platinas SET status='approved', reviewer_id=? WHERE id=? AND status='pending'",
                (reviewer_id, platina_id),
            )
            if cur.rowcount != 1:
                return None

            user_id = int(platina["user_id"])
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            before = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            old_xp = int(before["xp"] or 0)
            await tx.conn.execute(
                "UPDATE users SET xp=MAX(0,xp+?), denarios=MAX(0,denarios+?) WHERE user_id=?",
                (max(0, int(xp)), max(0, int(denarios)), user_id),
            )

            # Uma platina aprovada também comprova a conclusão do jogo.
            # Reaproveita um zerado pendente do mesmo jogo/plataforma; não duplica
            # registros já aprovados e não credita recompensa duas vezes.
            existing = await tx._one(
                """SELECT * FROM zerados
                   WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                     AND status IN ('pending','approved')
                   ORDER BY CASE status WHEN 'approved' THEN 0 ELSE 1 END, id DESC LIMIT 1""",
                (user_id, platina["game"], platina["platform"]),
            )
            zerado = None
            if existing is None:
                catalog_id = await self._resolver_jogo_catalogo_tx(tx, platina["game"], "platina_aprovada")
                cur_z = await tx.conn.execute(
                    """INSERT INTO zerados(
                           user_id, game, platform, finished_at, comment, status,
                           reviewer_id, approved_at, source_platina_id, catalog_game_id
                       ) VALUES (?,?,?,?,?,'approved',?,CURRENT_TIMESTAMP,?,?)""",
                    (user_id, platina["game"], platina["platform"], platina["earned_at"],
                     "Registro automático pela aprovação da platina.", reviewer_id, platina_id, catalog_id),
                )
                zerado_id = int(cur_z.lastrowid)
                deve_premiar_zerado = True
                zerado_status_anterior = None
                proof_msg_id = None
            elif existing["status"] == "approved":
                # Já existe conclusão validada. Apenas vincula a origem se ainda não houver.
                zerado_id = int(existing["id"])
                await tx.conn.execute(
                    "UPDATE zerados SET source_platina_id=COALESCE(source_platina_id, ?) WHERE id=?",
                    (platina_id, zerado_id),
                )
                deve_premiar_zerado = False
                zerado_status_anterior = "approved"
                proof_msg_id = existing["proof_msg_id"]
            else:
                # Se havia um pedido manual pendente, a platina aprovada o valida.
                zerado_id = int(existing["id"])
                proof_msg_id = existing["proof_msg_id"]
                zerado_status_anterior = "pending"
                cur_z = await tx.conn.execute(
                    """UPDATE zerados SET status='approved', reviewer_id=?, approved_at=CURRENT_TIMESTAMP,
                           finished_at=?, source_platina_id=? WHERE id=? AND status='pending'""",
                    (reviewer_id, platina["earned_at"], platina_id, zerado_id),
                )
                deve_premiar_zerado = cur_z.rowcount == 1

            xp_z = den_z = 0
            limite_atingido = False
            zerado_old_xp = None
            zerado_new_xp = None
            if deve_premiar_zerado:
                recent = await tx._one(
                    """SELECT COUNT(*) AS total FROM zerados
                       WHERE user_id=? AND status='approved'
                         AND id<>? AND COALESCE(approved_at, created_at) >= datetime('now','-1 day')""",
                    (user_id, zerado_id),
                )
                limite = max(0, int(limite_zerados or 0))
                limite_atingido = bool(limite > 0 and int(recent["total"] or 0) >= limite)
                if not limite_atingido:
                    xp_z = max(0, int(xp_zerado or 0))
                    den_z = max(0, int(denarios_zerado or 0))
                before_z = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
                zerado_old_xp = int(before_z["xp"] or 0)
                await tx.conn.execute(
                    "UPDATE users SET xp=MAX(0,xp+?), denarios=MAX(0,denarios+?) WHERE user_id=?",
                    (xp_z, den_z, user_id),
                )
                after_z = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
                zerado_new_xp = int(after_z["xp"] or 0)
                await tx.conn.execute(
                    "UPDATE zerados SET xp_awarded=?, denarios_awarded=? WHERE id=?",
                    (xp_z, den_z, zerado_id),
                )

            after = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            new_xp = int(after["xp"] or 0)
            return {
                "old_level": nivel_por_xp(old_xp), "new_level": nivel_por_xp(new_xp),
                "new_xp": new_xp, "user_id": user_id, "zerado_id": zerado_id,
                "zerado_created": zerado_status_anterior is None,
                "zerado_converted": zerado_status_anterior == "pending",
                "zerado_preexisting": zerado_status_anterior == "approved",
                "zerado_proof_msg_id": proof_msg_id,
                "zerado_xp": xp_z, "zerado_denarios": den_z,
                "zerado_daily_limit_reached": limite_atingido,
                "zerado_old_xp": zerado_old_xp, "zerado_new_xp": zerado_new_xp,
            }

    async def platinas_do_usuario(self, user_id: int):
        return await self._all(
            "SELECT * FROM platinas WHERE user_id=? AND status='approved' ORDER BY earned_at DESC",
            (user_id,),
        )

    async def contar_platinas(self, user_id: int) -> int:
        row = await self._one(
            "SELECT COUNT(*) AS c FROM platinas WHERE user_id=? AND status='approved'", (user_id,)
        )
        return row["c"]

    async def posicao_platinas(self, quantidade: int) -> int:
        row = await self._one(
            """SELECT COUNT(*)+1 AS p FROM (
                 SELECT user_id, COUNT(*) AS c FROM platinas WHERE status='approved'
                 GROUP BY user_id HAVING c > ?)""",
            (quantidade,),
        )
        return row["p"]

    # ---------- rankings ----------
    async def ranking_platinas(self, limite=10):
        return await self._all(
            """SELECT user_id, COUNT(*) AS valor FROM platinas WHERE status='approved'
               GROUP BY user_id ORDER BY valor DESC LIMIT ?""",
            (limite,),
        )

    async def ranking_xp(self, limite=10):
        return await self._all(
            "SELECT user_id, xp AS valor FROM users WHERE xp > 0 ORDER BY xp DESC LIMIT ?",
            (limite,),
        )

    async def ranking_mensal(self, mes: str, limite=10):
        """mes no formato AAAA-MM, baseado na data da conquista."""
        return await self._all(
            """SELECT user_id, COUNT(*) AS valor FROM platinas
               WHERE status='approved' AND substr(earned_at,1,7)=?
               GROUP BY user_id ORDER BY valor DESC LIMIT ?""",
            (mes, limite),
        )

    # ---------- zerados ----------
    async def zerado_duplicado(self, user_id: int, game: str, platform: str) -> bool:
        row = await self._one(
            """SELECT 1 FROM zerados
               WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                 AND status IN ('pending','approved') LIMIT 1""",
            (user_id, game, platform),
        )
        return row is not None

    async def criar_zerado_pendente(self, user_id, game, platform, finished_at, comment=""):
        """Cria uma solicitação pendente sem creditar XP/Denários antes da revisão."""
        async with self.transaction() as tx:
            dup = await tx._one(
                """SELECT id FROM zerados
                   WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                     AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if dup:
                return None
            catalog_id = await self._resolver_jogo_catalogo_tx(tx, game, "zerado")
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, status, catalog_game_id)
                   VALUES (?,?,?,?,?,'pending',?)""",
                (user_id, game, platform, finished_at, comment, catalog_id),
            )
            return int(cur.lastrowid)

    async def definir_mensagem_revisao_zerado(self, zerado_id: int, message_id: int) -> bool:
        cur = await self.conn.execute(
            "UPDATE zerados SET proof_msg_id=? WHERE id=? AND status='pending'",
            (message_id, zerado_id),
        )
        await self.conn.commit()
        return cur.rowcount == 1

    async def aprovar_zerado_com_recompensa(
        self, zerado_id: int, reviewer_id: int, xp_configurado: int,
        denarios_configurados: int, limite_diario: int,
    ):
        """Aprova uma única vez e credita recompensa atomicamente após a decisão."""
        async with self.transaction() as tx:
            row = await tx._one("SELECT * FROM zerados WHERE id=?", (zerado_id,))
            if row is None or row["status"] != "pending":
                return None
            recent = await tx._one(
                """SELECT COUNT(*) AS total FROM zerados
                   WHERE user_id=? AND status='approved'
                     AND COALESCE(approved_at, created_at) >= datetime('now','-1 day')""",
                (row["user_id"],),
            )
            total_recent = int(recent["total"] or 0)
            xp = max(0, int(xp_configurado or 0))
            denarios = max(0, int(denarios_configurados or 0))
            limite = max(0, int(limite_diario or 0))
            limite_atingido = bool(limite > 0 and total_recent >= limite)
            if limite_atingido:
                xp = denarios = 0

            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (row["user_id"],))
            before = await tx._one("SELECT xp FROM users WHERE user_id=?", (row["user_id"],))
            old_xp = int(before["xp"] or 0)
            old_level = nivel_por_xp(old_xp)
            await tx.conn.execute(
                "UPDATE users SET xp=MAX(0,xp+?), denarios=MAX(0,denarios+?) WHERE user_id=?",
                (xp, denarios, row["user_id"]),
            )
            after = await tx._one("SELECT xp FROM users WHERE user_id=?", (row["user_id"],))
            new_xp = int(after["xp"] or 0)
            new_level = nivel_por_xp(new_xp)
            cur = await tx.conn.execute(
                """UPDATE zerados SET status='approved', reviewer_id=?, approved_at=CURRENT_TIMESTAMP,
                       xp_awarded=?, denarios_awarded=? WHERE id=? AND status='pending'""",
                (reviewer_id, xp, denarios, zerado_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("O registro de zerado mudou durante a aprovação.")
            return {
                "id": zerado_id, "user_id": int(row["user_id"]), "game": row["game"],
                "platform": row["platform"], "finished_at": row["finished_at"],
                "comment": row["comment"], "proof_msg_id": row["proof_msg_id"],
                "xp": xp, "denarios": denarios, "old_xp": old_xp, "new_xp": new_xp,
                "old_level": old_level, "new_level": new_level,
                "daily_limit_reached": limite_atingido,
            }

    async def rejeitar_zerado(self, zerado_id: int, reviewer_id: int) -> bool:
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE zerados SET status='rejected', reviewer_id=?
                   WHERE id=? AND status='pending'""",
                (reviewer_id, zerado_id),
            )
            return cur.rowcount == 1

    async def criar_zerado(self, user_id, game, platform, finished_at, comment="", xp=0, denarios=0) -> int:
        async with self.transaction() as tx:
            catalog_id = await self._resolver_jogo_catalogo_tx(tx, game, "zerado")
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded, catalog_game_id)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (user_id, game, platform, finished_at, comment, xp, denarios, catalog_id),
            )
            return cur.lastrowid

    async def registrar_zerado_com_recompensa(
        self, user_id, game, platform, finished_at, comment="",
        xp_configurado=0, denarios_configurados=0, limite_diario=0,
    ):
        """Deduplica, aplica limite diário, grava e credita recompensa numa única transação."""
        async with self.transaction() as tx:
            dup = await tx._one(
                """SELECT id FROM zerados WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                   AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if dup:
                return None
            recent = await tx._one(
                """SELECT COUNT(*) AS total FROM zerados WHERE user_id=? AND status='approved'
                   AND COALESCE(approved_at, created_at) >= datetime('now','-1 day')""",
                (user_id,),
            )
            total_recent = int(recent["total"] or 0)
            xp = max(0, int(xp_configurado or 0))
            denarios = max(0, int(denarios_configurados or 0))
            limite = max(0, int(limite_diario or 0))
            if limite > 0 and total_recent >= limite:
                xp = denarios = 0
            catalog_id = await self._resolver_jogo_catalogo_tx(tx, game, "zerado")
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded, status, approved_at, catalog_game_id)
                   VALUES (?,?,?,?,?,?,?,'approved',CURRENT_TIMESTAMP,?)""",
                (user_id, game, platform, finished_at, comment, xp, denarios, catalog_id),
            )
            old_level = new_level = None
            new_xp = None
            if xp or denarios:
                await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
                before = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
                old_xp = int(before["xp"])
                old_level = nivel_por_xp(old_xp)
                await tx.conn.execute(
                    "UPDATE users SET xp=MAX(0,xp+?), denarios=MAX(0,denarios+?) WHERE user_id=?",
                    (xp, denarios, user_id),
                )
                after = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
                new_xp = int(after["xp"])
                new_level = nivel_por_xp(new_xp)
            return {
                "id": cur.lastrowid, "xp": xp, "denarios": denarios,
                "old_level": old_level, "new_level": new_level, "new_xp": new_xp,
                "daily_limit_reached": bool(limite > 0 and total_recent >= limite),
            }

    async def criar_zerado_unico(self, user_id, game, platform, finished_at, comment="", xp=0, denarios=0):
        """Cria zerado sem corrida entre a checagem de duplicidade e o INSERT."""
        async with self.transaction() as tx:
            dup = await tx._one(
                """SELECT id FROM zerados WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                   AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if dup:
                return None
            catalog_id = await self._resolver_jogo_catalogo_tx(tx, game, "zerado")
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded, status, approved_at, catalog_game_id)
                   VALUES (?,?,?,?,?,?,?,'approved',CURRENT_TIMESTAMP,?)""",
                (user_id, game, platform, finished_at, comment, xp, denarios, catalog_id),
            )
            return cur.lastrowid

    async def remover_zerado_com_recompensa(self, zerado_id: int):
        """Remove o registro e reverte o que ele concedeu, atomicamente."""
        async with self.transaction() as tx:
            row = await tx._one("SELECT * FROM zerados WHERE id=?", (zerado_id,))
            if not row:
                return None
            await tx.conn.execute("DELETE FROM zerados WHERE id=?", (zerado_id,))
            xp = int(row["xp_awarded"] or 0)
            denarios = int(row["denarios_awarded"] or 0)
            if xp or denarios:
                await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (row["user_id"],))
                await tx.conn.execute(
                    "UPDATE users SET xp=MAX(0,xp-?), denarios=MAX(0,denarios-?) WHERE user_id=?",
                    (xp, denarios, row["user_id"]),
                )
                xp_row = await tx._one("SELECT xp FROM users WHERE user_id=?", (row["user_id"],))
                row = dict(row)
                row["new_xp"] = int(xp_row["xp"])
            else:
                row = dict(row)
                row["new_xp"] = None
            return row

    async def get_zerado(self, zerado_id: int):
        return await self._one("SELECT * FROM zerados WHERE id=?", (zerado_id,))

    async def apagar_zerado(self, zerado_id: int):
        await self.conn.execute("DELETE FROM zerados WHERE id=?", (zerado_id,))
        await self.conn.commit()

    async def zerados_do_usuario(self, user_id: int):
        return await self._all(
            "SELECT * FROM zerados WHERE user_id=? AND status='approved' ORDER BY finished_at DESC, id DESC", (user_id,)
        )

    async def contar_zerados(self, user_id: int) -> int:
        row = await self._one("SELECT COUNT(*) AS c FROM zerados WHERE user_id=? AND status='approved'", (user_id,))
        return row["c"]

    async def contar_zerados_recentes(self, user_id: int) -> int:
        """Registros das últimas 24h (usado no limite diário de XP)."""
        row = await self._one(
            "SELECT COUNT(*) AS c FROM zerados WHERE user_id=? AND status='approved' AND COALESCE(approved_at, created_at) >= datetime('now','-1 day')",
            (user_id,),
        )
        return row["c"]

    async def posicao_zerados(self, quantidade: int) -> int:
        row = await self._one(
            """SELECT COUNT(*)+1 AS p FROM (
                 SELECT user_id, COUNT(*) AS c FROM zerados WHERE status='approved' GROUP BY user_id HAVING c > ?)""",
            (quantidade,),
        )
        return row["p"]

    async def ranking_zerados(self, limite=10):
        return await self._all(
            "SELECT user_id, COUNT(*) AS valor FROM zerados WHERE status='approved' GROUP BY user_id ORDER BY valor DESC LIMIT ?",
            (limite,),
        )

    async def ranking_zerados_mensal(self, mes: str, limite=10):
        """mes no formato AAAA-MM, baseado na data em que o jogo foi zerado."""
        return await self._all(
            """SELECT user_id, COUNT(*) AS valor FROM zerados
               WHERE status='approved' AND substr(finished_at,1,7)=? GROUP BY user_id ORDER BY valor DESC LIMIT ?""",
            (mes, limite),
        )

    # ---------- painel do canal #colizeu ----------
    async def stats_runs(self, user_id: int):
        """Retorna quantas runs aprovadas e quantos recordes de categoria o usuário possui."""
        runs = await self._one(
            "SELECT COUNT(*) AS total FROM sl_runs WHERE user_id=? AND status='approved'",
            (user_id,),
        )
        recordes = await self._one(
            """WITH classificados AS (
                   SELECT user_id,
                          ROW_NUMBER() OVER (
                              PARTITION BY game_id, challenge_id
                              ORDER BY seconds ASC, created_at ASC, id ASC
                          ) AS posicao
                   FROM sl_runs WHERE status='approved'
               )
               SELECT COUNT(*) AS total FROM classificados
               WHERE user_id=? AND posicao=1""",
            (user_id,),
        )
        return {"runs": int(runs["total"]), "recordes": int(recordes["total"])}

    async def recordes_recentes(self, limite: int = 10):
        """Retorna o melhor tempo aprovado por jogo/desafio, com nomes legíveis."""
        return await self._all(
            """WITH classificados AS (
                   SELECT r.user_id, r.game_id, r.challenge_id, r.seconds, r.created_at, r.id,
                          ROW_NUMBER() OVER (
                              PARTITION BY r.game_id, r.challenge_id
                              ORDER BY r.seconds ASC, r.created_at ASC, r.id ASC
                          ) AS posicao
                   FROM sl_runs r WHERE r.status='approved'
               )
               SELECT g.name AS jogo, c.name AS desafio, r.user_id, r.seconds
               FROM classificados r
               JOIN sl_games g ON g.id=r.game_id
               JOIN sl_challenges c ON c.id=r.challenge_id
               WHERE r.posicao=1
               ORDER BY r.created_at DESC, r.id DESC LIMIT ?""",
            (limite,),
        )

    async def ranking_completo(self, limite=10):
        return await self._all(
            """SELECT p.user_id, COUNT(*) AS platinas, COALESCE(u.xp, 0) AS xp
               FROM platinas p LEFT JOIN users u ON u.user_id = p.user_id
               WHERE p.status='approved'
               GROUP BY p.user_id ORDER BY platinas DESC, xp DESC LIMIT ?""",
            (limite,),
        )

    async def ultimas_platinas(self, user_id: int, n: int = 3):
        return await self._all(
            """SELECT * FROM platinas WHERE user_id=? AND status='approved'
               ORDER BY earned_at DESC, id DESC LIMIT ?""",
            (user_id, n),
        )

    async def get_kv(self, key: str):
        row = await self._one("SELECT value FROM kv WHERE key=?", (key,))
        return row["value"] if row else None

    async def set_kv(self, key: str, value: str):
        await self.conn.execute(
            "INSERT INTO kv(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await self.conn.commit()

    async def ranking_runs(self, limite: int = 10):
        return await self._all(
            "SELECT user_id,COUNT(*) AS valor FROM sl_runs WHERE status='approved' GROUP BY user_id ORDER BY valor DESC,user_id LIMIT ?",
            (max(1, min(int(limite), 100)),),
        )

    async def ranking_recordes_runs(self, limite: int = 10):
        return await self._all(
            """WITH classificados AS (
                   SELECT user_id, ROW_NUMBER() OVER (
                       PARTITION BY game_id,challenge_id ORDER BY seconds ASC,created_at ASC,id ASC
                   ) AS posicao
                   FROM sl_runs WHERE status='approved'
               )
               SELECT user_id,COUNT(*) AS valor FROM classificados WHERE posicao=1
               GROUP BY user_id ORDER BY valor DESC,user_id LIMIT ?""",
            (max(1, min(int(limite), 100)),),
        )

    async def listar_gladiadores_comparacao(self, limite: int = 25):
        return await self._all(
            """WITH ids AS (
                   SELECT user_id FROM users WHERE xp>0
                   UNION SELECT user_id FROM platinas WHERE status='approved'
                   UNION SELECT user_id FROM zerados WHERE status='approved'
                   UNION SELECT user_id FROM sl_runs WHERE status='approved'
               )
               SELECT ids.user_id,
                      (SELECT COUNT(*) FROM platinas p WHERE p.user_id=ids.user_id AND p.status='approved') AS platinas,
                      COALESCE(u.xp,0) AS xp
               FROM ids LEFT JOIN users u ON u.user_id=ids.user_id
               ORDER BY xp DESC,platinas DESC,ids.user_id LIMIT ?""",
            (max(1, min(int(limite), 100)),),
        )

    # ---------- santuários (perfil em thread privada) ----------
    async def get_perfil(self, user_id: int):
        return await self._one("SELECT * FROM perfis WHERE user_id=?", (user_id,))

    async def get_perfil_por_thread(self, thread_id: int):
        return await self._one("SELECT * FROM perfis WHERE thread_id=?", (thread_id,))

    async def criar_perfil(self, user_id: int, thread_id: int):
        await self.conn.execute(
            "INSERT OR REPLACE INTO perfis(user_id, thread_id) VALUES (?,?)", (user_id, thread_id)
        )
        await self.conn.commit()

    async def atualizar_perfil(self, user_id: int, **campos):
        permitidos = {"card_msg_id", "tagline", "bio", "fav_game", "theme", "links", "thread_id"}
        campos = {k: v for k, v in campos.items() if k in permitidos}
        if not campos:
            return
        sets = ", ".join(f"{k}=?" for k in campos)
        await self.conn.execute(f"UPDATE perfis SET {sets} WHERE user_id=?", (*campos.values(), user_id))
        await self.conn.commit()

    async def apagar_perfil(self, user_id: int):
        await self.conn.execute("DELETE FROM perfis WHERE user_id=?", (user_id,))
        await self.conn.commit()

    # ---------- contribuições e interações comunitárias ----------
    async def criar_contribuicao(self, *, guild_id: int, user_id: int, kind: str,
                                 game_name: str, title: str, summary: str,
                                 content: str, sources: str = "",
                                 spoiler_level: str = "none", challenge_mode: str = "individual",
                                 challenge_goal: int = 0, origin_sector: str = "",
                                 origin_channel_id: int | None = None) -> int:
        mode = str(challenge_mode or "individual").lower()
        goal = max(0, min(int(challenge_goal or 0), 500))
        if str(kind) == "challenge" and mode not in {"individual", "collective"}:
            raise ValueError("Modalidade de desafio inválida.")
        if str(kind) == "challenge" and mode == "collective" and goal < 2:
            raise ValueError("Desafios coletivos precisam de uma meta mínima de 2 conclusões.")
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """INSERT INTO community_contributions
                   (guild_id,user_id,kind,game_name,title,summary,content,sources,spoiler_level,challenge_mode,challenge_goal,origin_sector,origin_channel_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(guild_id), int(user_id), str(kind), str(game_name or ""),
                 str(title), str(summary or ""), str(content), str(sources or ""),
                 str(spoiler_level or "none"),
                 mode if str(kind) == "challenge" else "individual",
                 goal if str(kind) == "challenge" else 0,
                 str(origin_sector or "")[:40], int(origin_channel_id) if origin_channel_id else None),
            )
            return int(cur.lastrowid)

    async def get_contribuicao(self, contribution_id: int):
        return await self._one(
            "SELECT * FROM community_contributions WHERE id=?", (int(contribution_id),)
        )

    async def listar_contribuicoes(self, *, guild_id: int, status: str | None = None,
                                   user_id: int | None = None, limit: int = 20, offset: int = 0):
        where = ["guild_id=?"]
        args: list = [int(guild_id)]
        if status:
            where.append("status=?")
            args.append(str(status))
        if user_id is not None:
            where.append("user_id=?")
            args.append(int(user_id))
        args.extend([max(1, min(int(limit), 50)), max(0, int(offset))])
        return await self._all(
            "SELECT * FROM community_contributions WHERE " + " AND ".join(where) +
            " ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'changes_requested' THEN 1 ELSE 2 END, created_at DESC, id DESC LIMIT ? OFFSET ?",
            tuple(args),
        )

    async def decidir_contribuicao(self, contribution_id: int, reviewer_id: int,
                                   status: str, note: str = "", xp_base: int = 0,
                                   xp_weekly_cap: int = 50):
        """Decisão idempotente. Aprovação e XP são gravados na mesma transação."""
        if status not in {"approved", "rejected", "changes_requested"}:
            raise ValueError("Status de decisão inválido.")
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT * FROM community_contributions WHERE id=? AND status IN ('pending','changes_requested')",
                (int(contribution_id),),
            )
            if row is None:
                return None
            cur = await tx.conn.execute(
                """UPDATE community_contributions
                   SET status=?, reviewer_id=?, review_note=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status IN ('pending','changes_requested')""",
                (status, int(reviewer_id), str(note or "")[:1000], int(contribution_id)),
            )
            if cur.rowcount != 1:
                return None
            awarded = 0
            old_level = new_level = None
            total_xp = None
            if status == "approved":
                exists = await tx._one(
                    "SELECT id FROM community_xp_awards WHERE contribution_id=?",
                    (int(contribution_id),),
                )
                if exists is None:
                    weekly = await tx._one(
                        """SELECT COALESCE(SUM(xp),0) AS total FROM community_xp_awards
                           WHERE guild_id=? AND user_id=? AND awarded_at >= datetime('now','-7 days')""",
                        (int(row["guild_id"]), int(row["user_id"])),
                    )
                    already = int(weekly["total"] or 0) if weekly else 0
                    awarded = max(0, min(int(xp_base), max(0, int(xp_weekly_cap) - already)))
                    await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(row["user_id"]),))
                    user_before = await tx._one("SELECT xp FROM users WHERE user_id=?", (int(row["user_id"]),))
                    from levels import nivel_por_xp
                    old_level = nivel_por_xp(int(user_before["xp"] or 0))
                    if awarded:
                        await tx.conn.execute("UPDATE users SET xp=xp+? WHERE user_id=?", (awarded, int(row["user_id"])))
                    user_after = await tx._one("SELECT xp FROM users WHERE user_id=?", (int(row["user_id"]),))
                    total_xp = int(user_after["xp"] or 0)
                    new_level = nivel_por_xp(total_xp)
                    await tx.conn.execute(
                        "INSERT OR IGNORE INTO community_xp_awards(contribution_id,guild_id,user_id,xp) VALUES (?,?,?,?)",
                        (int(contribution_id), int(row["guild_id"]), int(row["user_id"]), awarded),
                    )
                    await tx.conn.execute(
                        "UPDATE community_contributions SET xp_awarded=? WHERE id=?",
                        (awarded, int(contribution_id)),
                    )
            updated = await tx._one("SELECT * FROM community_contributions WHERE id=?", (int(contribution_id),))
            return {
                "contribution": dict(updated), "status": status, "xp_awarded": awarded,
                "old_level": old_level, "new_level": new_level, "total_xp": total_xp,
            }

    async def marcar_publicacao_contribuicao(self, contribution_id: int, channel_id: int,
                                              message_id: int, thread_id: int | None = None) -> bool:
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE community_contributions SET published_channel_id=?, published_message_id=?,
                   published_thread_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='approved'""",
                (int(channel_id), int(message_id), int(thread_id) if thread_id else None, int(contribution_id)),
            )
            return cur.rowcount == 1

    async def registrar_post_comunitario(self, guild_id: int, target_type: str, target_id: int,
                                         channel_id: int, message_id: int, thread_id: int | None = None):
        async with self.transaction() as tx:
            await tx.conn.execute(
                """INSERT INTO community_posts(guild_id,target_type,target_id,channel_id,message_id,thread_id)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(guild_id,target_type,target_id) DO UPDATE SET
                   channel_id=excluded.channel_id,message_id=excluded.message_id,
                   thread_id=COALESCE(excluded.thread_id,community_posts.thread_id),updated_at=CURRENT_TIMESTAMP""",
                (int(guild_id), str(target_type), int(target_id), int(channel_id), int(message_id),
                 int(thread_id) if thread_id else None),
            )

    async def listar_posts_comunitarios(self, limit: int = 500):
        return await self._all(
            "SELECT * FROM community_posts WHERE is_hidden=0 ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 2000)),)
        )

    async def get_post_comunitario(self, guild_id: int, target_type: str, target_id: int):
        return await self._one(
            "SELECT * FROM community_posts WHERE guild_id=? AND target_type=? AND target_id=?",
            (int(guild_id), str(target_type), int(target_id)),
        )

    async def definir_thread_comunitaria(self, guild_id: int, target_type: str,
                                         target_id: int, thread_id: int):
        await self.conn.execute(
            """UPDATE community_posts SET thread_id=?,updated_at=CURRENT_TIMESTAMP
               WHERE guild_id=? AND target_type=? AND target_id=?""",
            (int(thread_id), int(guild_id), str(target_type), int(target_id)),
        )
        await self.conn.commit()

    async def alternar_interacao(self, guild_id: int, target_type: str, target_id: int,
                                 user_id: int, reaction_key: str) -> bool:
        """Alterna uma reação. Retorna True quando adicionou, False quando removeu."""
        async with self.transaction() as tx:
            existente = await tx._one(
                """SELECT id FROM community_interactions WHERE guild_id=? AND target_type=?
                   AND target_id=? AND user_id=? AND reaction_key=?""",
                (int(guild_id), str(target_type), int(target_id), int(user_id), str(reaction_key)),
            )
            if existente:
                await tx.conn.execute("DELETE FROM community_interactions WHERE id=?", (existente["id"],))
                return False
            await tx.conn.execute(
                """INSERT OR IGNORE INTO community_interactions
                   (guild_id,target_type,target_id,user_id,reaction_key) VALUES (?,?,?,?,?)""",
                (int(guild_id), str(target_type), int(target_id), int(user_id), str(reaction_key)),
            )
            return True

    async def contar_interacoes(self, guild_id: int, target_type: str, target_id: int) -> dict:
        rows = await self._all(
            """SELECT reaction_key,COUNT(*) AS total FROM community_interactions
               WHERE guild_id=? AND target_type=? AND target_id=? GROUP BY reaction_key""",
            (int(guild_id), str(target_type), int(target_id)),
        )
        return {str(r["reaction_key"]): int(r["total"]) for r in rows}

    async def possui_interacao(self, guild_id: int, target_type: str, target_id: int,
                               user_id: int, reaction_key: str) -> bool:
        row = await self._one(
            """SELECT 1 FROM community_interactions WHERE guild_id=? AND target_type=?
               AND target_id=? AND user_id=? AND reaction_key=?""",
            (int(guild_id), str(target_type), int(target_id), int(user_id), str(reaction_key)),
        )
        return row is not None

    async def alternar_favorito(self, guild_id: int, user_id: int,
                                target_type: str, target_id: int) -> bool:
        async with self.transaction() as tx:
            row = await tx._one(
                """SELECT 1 FROM community_bookmarks WHERE guild_id=? AND user_id=?
                   AND target_type=? AND target_id=?""",
                (int(guild_id), int(user_id), str(target_type), int(target_id)),
            )
            if row:
                await tx.conn.execute(
                    "DELETE FROM community_bookmarks WHERE guild_id=? AND user_id=? AND target_type=? AND target_id=?",
                    (int(guild_id), int(user_id), str(target_type), int(target_id)),
                )
                return False
            await tx.conn.execute(
                "INSERT OR IGNORE INTO community_bookmarks(guild_id,user_id,target_type,target_id) VALUES (?,?,?,?)",
                (int(guild_id), int(user_id), str(target_type), int(target_id)),
            )
            return True

    async def listar_favoritos(self, guild_id: int, user_id: int, limit: int = 20):
        return await self._all(
            """SELECT * FROM community_bookmarks WHERE guild_id=? AND user_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (int(guild_id), int(user_id), max(1, min(int(limit), 50))),
        )

    async def alternar_seguir(self, guild_id: int, follower_id: int, followed_id: int) -> bool:
        if int(follower_id) == int(followed_id):
            raise ValueError("Não é possível acompanhar a si mesmo.")
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT 1 FROM community_follows WHERE guild_id=? AND follower_id=? AND followed_id=?",
                (int(guild_id), int(follower_id), int(followed_id)),
            )
            if row:
                await tx.conn.execute(
                    "DELETE FROM community_follows WHERE guild_id=? AND follower_id=? AND followed_id=?",
                    (int(guild_id), int(follower_id), int(followed_id)),
                )
                return False
            await tx.conn.execute(
                "INSERT OR IGNORE INTO community_follows(guild_id,follower_id,followed_id) VALUES (?,?,?)",
                (int(guild_id), int(follower_id), int(followed_id)),
            )
            return True

    async def definir_preferencias_atividade(self, guild_id: int, user_id: int, **flags):
        permitidos = {"platinas", "zerados", "runs", "lore", "guides", "challenges"}
        valores = {k: int(bool(v)) for k, v in flags.items() if k in permitidos}
        if not valores:
            return
        atual = await self._one(
            "SELECT 1 FROM community_activity_preferences WHERE guild_id=? AND user_id=?",
            (int(guild_id), int(user_id)),
        )
        if atual:
            sets = ",".join(f"{k}=?" for k in valores)
            await self.conn.execute(
                f"UPDATE community_activity_preferences SET {sets},updated_at=CURRENT_TIMESTAMP WHERE guild_id=? AND user_id=?",
                (*valores.values(), int(guild_id), int(user_id)),
            )
        else:
            colunas = ["guild_id", "user_id", *valores.keys()]
            placeholders = ",".join("?" for _ in colunas)
            await self.conn.execute(
                f"INSERT INTO community_activity_preferences({','.join(colunas)}) VALUES ({placeholders})",
                (int(guild_id), int(user_id), *valores.values()),
            )
        await self.conn.commit()

    async def registrar_honra(self, guild_id: int, from_user_id: int, to_user_id: int,
                              honor_key: str, week_key: str) -> str:
        if int(from_user_id) == int(to_user_id):
            raise ValueError("Não é possível honrar a si mesmo.")
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT id,honor_key FROM community_honors WHERE guild_id=? AND from_user_id=? AND week_key=?",
                (int(guild_id), int(from_user_id), str(week_key)),
            )
            if row:
                if row["honor_key"] == str(honor_key):
                    return "already"
                await tx.conn.execute(
                    "UPDATE community_honors SET honor_key=?,to_user_id=?,created_at=CURRENT_TIMESTAMP WHERE id=?",
                    (str(honor_key), int(to_user_id), int(row["id"])),
                )
                return "changed"
            await tx.conn.execute(
                "INSERT INTO community_honors(guild_id,from_user_id,to_user_id,honor_key,week_key) VALUES (?,?,?,?,?)",
                (int(guild_id), int(from_user_id), int(to_user_id), str(honor_key), str(week_key)),
            )
            return "created"

    async def contar_honras(self, guild_id: int, user_id: int) -> dict:
        rows = await self._all(
            "SELECT honor_key,COUNT(*) AS total FROM community_honors WHERE guild_id=? AND to_user_id=? GROUP BY honor_key",
            (int(guild_id), int(user_id)),
        )
        return {str(r["honor_key"]): int(r["total"]) for r in rows}

    async def contar_seguidores(self, guild_id: int, user_id: int) -> int:
        row = await self._one(
            "SELECT COUNT(*) AS n FROM community_follows WHERE guild_id=? AND followed_id=?",
            (int(guild_id), int(user_id)),
        )
        return int(row["n"] or 0) if row else 0

    async def editar_contribuicao(self, contribution_id: int, user_id: int, *, game_name: str,
                                  title: str, summary: str, content: str, sources: str = "",
                                  spoiler_level: str = "none", challenge_mode: str = "individual",
                                  challenge_goal: int = 0) -> bool:
        """Permite ao autor responder a um pedido de ajustes, sem apagar o histórico da decisão."""
        async with self.transaction() as tx:
            existing = await tx._one(
                "SELECT kind FROM community_contributions WHERE id=? AND user_id=? AND status='changes_requested'",
                (int(contribution_id), int(user_id)),
            )
            if existing is None:
                return False
            is_challenge = str(existing["kind"]) == "challenge"
            mode = str(challenge_mode or "individual").lower() if is_challenge else "individual"
            goal = max(0, min(int(challenge_goal or 0), 500)) if is_challenge else 0
            if is_challenge and (mode not in {"individual", "collective"} or (mode == "collective" and goal < 2)):
                raise ValueError("Modalidade ou meta coletiva inválida.")
            cur = await tx.conn.execute(
                """UPDATE community_contributions
                   SET game_name=?,title=?,summary=?,content=?,sources=?,spoiler_level=?,challenge_mode=?,challenge_goal=?,
                       status='pending',reviewer_id=NULL,review_note='',updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND user_id=? AND status='changes_requested'""",
                (str(game_name or "")[:80], str(title)[:90], str(summary)[:350], str(content)[:1500],
                 str(sources or "")[:700], str(spoiler_level or "none"), mode, goal,
                 int(contribution_id), int(user_id)),
            )
            return cur.rowcount == 1

    async def aplicar_contribuicao_soulslike(self, contribution_id: int):
        """Materializa uma sugestão aprovada no catálogo de Runs, sem duplicar registros."""
        async with self.transaction() as tx:
            contrib = await tx._one(
                "SELECT * FROM community_contributions WHERE id=? AND status='approved'",
                (int(contribution_id),),
            )
            if contrib is None:
                raise ValueError("A contribuição não está aprovada.")
            if contrib["applied_target_type"] and contrib["applied_target_id"]:
                return {"type": contrib["applied_target_type"], "id": int(contrib["applied_target_id"]), "created": False}

            kind = str(contrib["kind"])
            if kind == "game_suggestion":
                name = str(contrib["title"]).strip()[:80]
                if not name:
                    raise ValueError("O nome do jogo está vazio.")
                existing = await tx._one("SELECT id FROM sl_games WHERE name=? COLLATE NOCASE", (name,))
                created = existing is None
                catalog_id = await self._resolver_jogo_catalogo_tx(tx, name, "runs")
                await tx.conn.execute(
                    "INSERT OR IGNORE INTO sl_games(name,catalog_game_id) VALUES (?,?)",
                    (name, catalog_id),
                )
                row = await tx._one("SELECT id FROM sl_games WHERE name=? COLLATE NOCASE", (name,))
                target_type = "sl_game"
            elif kind == "challenge":
                game_name = str(contrib["game_name"] or "").strip()
                name = str(contrib["title"]).strip()[:80]
                if not game_name:
                    raise ValueError("O desafio precisa estar vinculado a um jogo.")
                game = await tx._one("SELECT id FROM sl_games WHERE name=? COLLATE NOCASE", (game_name,))
                if game is None:
                    raise ValueError(f"O jogo **{game_name}** ainda não está no catálogo Soulslike. Aprove primeiro a sugestão do jogo ou cadastre-o no painel de Runs.")
                existing = await tx._one("SELECT id,game_id FROM sl_challenges WHERE name=? COLLATE NOCASE", (name,))
                if existing is not None:
                    raise ValueError(f"Já existe um desafio chamado **{name}**. Verifique o Livro dos Desafios antes de aprovar.")
                created = True
                await tx.conn.execute(
                    "INSERT INTO sl_challenges(name,rules,game_id) VALUES (?,?,?)",
                    (name, str(contrib["content"])[:1000], int(game["id"])),
                )
                row = await tx._one("SELECT id FROM sl_challenges WHERE name=? COLLATE NOCASE", (name,))
                target_type = "sl_challenge"
            else:
                return None

            if row is None:
                raise RuntimeError("Não foi possível localizar o registro criado no catálogo Soulslike.")
            target_id = int(row["id"])
            await tx.conn.execute(
                "UPDATE community_contributions SET applied_target_type=?,applied_target_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (target_type, target_id, int(contribution_id)),
            )
            return {"type": target_type, "id": target_id, "created": created}

    async def alternar_participacao_desafio(self, guild_id: int, contribution_id: int, user_id: int) -> bool:
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT status FROM community_challenge_participants WHERE guild_id=? AND contribution_id=? AND user_id=?",
                (int(guild_id), int(contribution_id), int(user_id)),
            )
            if row:
                if row["status"] == "completed":
                    raise ValueError("Sua participação já foi marcada como concluída e não pode ser removida pelo botão de inscrição.")
                await tx.conn.execute(
                    "DELETE FROM community_challenge_participants WHERE guild_id=? AND contribution_id=? AND user_id=?",
                    (int(guild_id), int(contribution_id), int(user_id)),
                )
                return False
            await tx.conn.execute(
                "INSERT INTO community_challenge_participants(guild_id,contribution_id,user_id,status) VALUES (?,?,?,'joined')",
                (int(guild_id), int(contribution_id), int(user_id)),
            )
            return True

    async def atualizar_progresso_desafio(self, guild_id: int, contribution_id: int, user_id: int,
                                          status: str, progress_note: str, evidence: str = "") -> bool:
        if status not in {"in_progress", "completed"}:
            raise ValueError("Status de participação inválido.")
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE community_challenge_participants
                   SET status=?,progress_note=?,evidence=?,updated_at=CURRENT_TIMESTAMP
                   WHERE guild_id=? AND contribution_id=? AND user_id=?""",
                (status, str(progress_note)[:700], str(evidence)[:500], int(guild_id), int(contribution_id), int(user_id)),
            )
            return cur.rowcount == 1

    async def contar_participantes_desafio(self, guild_id: int, contribution_id: int) -> dict:
        rows = await self._all(
            "SELECT status,COUNT(*) AS total FROM community_challenge_participants WHERE guild_id=? AND contribution_id=? GROUP BY status",
            (int(guild_id), int(contribution_id)),
        )
        return {str(row["status"]): int(row["total"]) for row in rows}

    async def listar_participantes_desafio(self, guild_id: int, contribution_id: int, limit: int = 25):
        return await self._all(
            """SELECT user_id,status,progress_note,evidence,created_at,updated_at
               FROM community_challenge_participants WHERE guild_id=? AND contribution_id=?
               ORDER BY CASE status WHEN 'completed' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END,
                        updated_at DESC,user_id LIMIT ?""",
            (int(guild_id), int(contribution_id), max(1, min(int(limit), 25))),
        )

    async def get_preferencias_atividade(self, guild_id: int, user_id: int) -> dict:
        row = await self._one(
            "SELECT * FROM community_activity_preferences WHERE guild_id=? AND user_id=?",
            (int(guild_id), int(user_id)),
        )
        keys = ("platinas", "zerados", "runs", "lore", "guides", "challenges")
        return {key: bool(row[key]) if row else True for key in keys}


    async def ativar_faq_comunitaria(self, contribution_id: int) -> int | None:
        """Materializa FAQ aprovada em base comunitária consultável pela NARA."""
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT * FROM community_contributions WHERE id=? AND kind='faq' AND status='approved'",
                (int(contribution_id),),
            )
            if row is None:
                return None
            await tx.conn.execute(
                """INSERT INTO community_faq_entries(contribution_id,guild_id,question,answer,status)
                   VALUES (?,?,?,?, 'active')
                   ON CONFLICT(contribution_id) DO UPDATE SET question=excluded.question,
                     answer=excluded.answer,status='active',updated_at=CURRENT_TIMESTAMP""",
                (int(row['id']), int(row['guild_id']), str(row['title'])[:200], str(row['content'])[:1500]),
            )
            entry = await tx._one("SELECT id FROM community_faq_entries WHERE contribution_id=?", (int(contribution_id),))
            return int(entry['id']) if entry else None

    async def buscar_faq_comunitaria(self, guild_id: int, question: str, min_score: float = 0.68):
        """Busca conservadora por pergunta, retornando apenas correspondência inequívoca."""
        import re
        import unicodedata
        from difflib import SequenceMatcher

        def normalizar(value: str) -> str:
            value = unicodedata.normalize('NFKD', str(value or '').casefold())
            value = ''.join(ch for ch in value if not unicodedata.combining(ch))
            value = re.sub(r'[^a-z0-9 ]', ' ', value)
            return re.sub(r'\s+', ' ', value).strip()

        tokens_stop = {'como','qual','quais','onde','quando','porque','para','com','sem','uma','uns','das','dos','que','por','me','minha','meu','eu','voce','tem','faz','fazer','a','o','e','de','da','do','em','no','na'}
        query = normalizar(question)
        qtokens = {t for t in query.split() if len(t) > 2 and t not in tokens_stop}
        if len(qtokens) < 2:
            return None
        rows = await self._all(
            "SELECT * FROM community_faq_entries WHERE guild_id=? AND status='active' ORDER BY created_at DESC LIMIT 300",
            (int(guild_id),),
        )
        ranked = []
        for row in rows:
            candidate = normalizar(row['question'])
            ctokens = {t for t in candidate.split() if len(t) > 2 and t not in tokens_stop}
            shared = qtokens & ctokens
            if len(shared) < 2:
                continue
            coverage = len(shared) / max(1, min(len(qtokens), len(ctokens)))
            sequence = SequenceMatcher(None, query, candidate).ratio()
            score = 0.62 * coverage + 0.38 * sequence
            ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked or ranked[0][0] < float(min_score):
            return None
        second = ranked[1][0] if len(ranked) > 1 else 0.0
        if ranked[0][0] - second < 0.10:
            return None
        return ranked[0][1]

    async def obter_faq_comunitaria(self, entry_id: int):
        return await self._one(
            "SELECT * FROM community_faq_entries WHERE id=? AND status='active'",
            (int(entry_id),),
        )

    async def arquivar_faq_contribuicao(self, contribution_id: int):
        await self.conn.execute(
            "UPDATE community_faq_entries SET status='archived',updated_at=CURRENT_TIMESTAMP WHERE contribution_id=?",
            (int(contribution_id),),
        )
        await self.conn.commit()

    async def criar_mensagem_santuario(self, guild_id: int, owner_id: int, visitor_id: int,
                                       message: str) -> int | None:
        if int(owner_id) == int(visitor_id):
            raise ValueError("Você não pode deixar mensagem no próprio livro de visitas.")
        async with self.transaction() as tx:
            recent = await tx._one(
                """SELECT COUNT(*) AS n FROM community_guestbook WHERE guild_id=? AND owner_id=?
                   AND visitor_id=? AND created_at>=datetime('now','-1 day')""",
                (int(guild_id), int(owner_id), int(visitor_id)),
            )
            if int(recent["n"] or 0) >= 1:
                return None
            cur = await tx.conn.execute(
                "INSERT INTO community_guestbook(guild_id,owner_id,visitor_id,message) VALUES (?,?,?,?)",
                (int(guild_id), int(owner_id), int(visitor_id), str(message).strip()[:300]),
            )
            return int(cur.lastrowid)

    async def listar_mensagens_santuario(self, guild_id: int, owner_id: int, limit: int = 10):
        return await self._all(
            """SELECT * FROM community_guestbook WHERE guild_id=? AND owner_id=?
               ORDER BY created_at DESC,id DESC LIMIT ?""",
            (int(guild_id), int(owner_id), max(1, min(int(limit), 25))),
        )

    async def apagar_mensagem_santuario(self, guild_id: int, owner_id: int, message_id: int) -> bool:
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                "DELETE FROM community_guestbook WHERE guild_id=? AND owner_id=? AND id=?",
                (int(guild_id), int(owner_id), int(message_id)),
            )
            return cur.rowcount == 1

    async def criar_denuncia_comunitaria(self, guild_id: int, reporter_id: int, target_type: str,
                                         target_id: int, reason: str, details: str = "") -> int | None:
        """Cria denúncia única pendente por autor/publicação, evitando spam duplicado."""
        async with self.transaction() as tx:
            duplicate = await tx._one(
                """SELECT id FROM community_reports WHERE guild_id=? AND reporter_id=?
                   AND target_type=? AND target_id=? AND status='pending'""",
                (int(guild_id), int(reporter_id), str(target_type), int(target_id)),
            )
            if duplicate:
                return None
            cur = await tx.conn.execute(
                """INSERT INTO community_reports(guild_id,reporter_id,target_type,target_id,reason,details)
                   VALUES (?,?,?,?,?,?)""",
                (int(guild_id), int(reporter_id), str(target_type), int(target_id),
                 str(reason)[:90], str(details)[:700]),
            )
            return int(cur.lastrowid)

    async def get_denuncia_comunitaria(self, report_id: int):
        return await self._one("SELECT * FROM community_reports WHERE id=?", (int(report_id),))

    async def listar_denuncias_comunitarias(self, guild_id: int, status: str = "pending", limit: int = 50):
        return await self._all(
            """SELECT * FROM community_reports WHERE guild_id=? AND status=?
               ORDER BY created_at ASC,id ASC LIMIT ?""",
            (int(guild_id), str(status), max(1, min(int(limit), 100))),
        )

    async def decidir_denuncia_comunitaria(self, report_id: int, reviewer_id: int,
                                           action: str, note: str = ""):
        if action not in {"hidden", "dismissed"}:
            raise ValueError("Decisão de denúncia inválida.")
        async with self.transaction() as tx:
            report = await tx._one(
                "SELECT * FROM community_reports WHERE id=? AND status='pending'", (int(report_id),)
            )
            if report is None:
                return None
            cur = await tx.conn.execute(
                """UPDATE community_reports SET status=?,reviewer_id=?,review_note=?,updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status='pending'""",
                (action, int(reviewer_id), str(note or "")[:700], int(report_id)),
            )
            if cur.rowcount != 1:
                return None
            if action == "hidden":
                await tx.conn.execute(
                    """UPDATE community_posts SET is_hidden=1,updated_at=CURRENT_TIMESTAMP
                       WHERE guild_id=? AND target_type=? AND target_id=?""",
                    (int(report["guild_id"]), str(report["target_type"]), int(report["target_id"])),
                )
                if str(report["target_type"]).startswith("contrib_"):
                    kind = str(report["target_type"]).removeprefix("contrib_")
                    if kind == "faq":
                        await tx.conn.execute(
                            "UPDATE community_faq_entries SET status='archived',updated_at=CURRENT_TIMESTAMP WHERE contribution_id=?",
                            (int(report["target_id"]),),
                        )
                    await tx.conn.execute(
                        """UPDATE community_contributions SET status='archived',reviewer_id=?,review_note=?,
                           updated_at=CURRENT_TIMESTAMP WHERE id=? AND guild_id=? AND kind=? AND status='approved'""",
                        (int(reviewer_id), str(note or "")[:700], int(report["target_id"]), int(report["guild_id"]), kind),
                    )
            updated = await tx._one("SELECT * FROM community_reports WHERE id=?", (int(report_id),))
            return dict(updated)

