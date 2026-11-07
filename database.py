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
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
    reviewer_id INTEGER,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_plat_user ON platinas(user_id, status);

-- Sistema de runs Soulslike integrado
CREATE TABLE IF NOT EXISTS sl_games (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TABLE IF NOT EXISTS sl_challenges (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    rules TEXT NOT NULL DEFAULT ''
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
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id   INTEGER NOT NULL,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
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
        await self.conn.commit()

    @asynccontextmanager
    async def transaction(self):
        """Transação isolada, sem expor a conexão compartilhada do bot a interleavings."""
        if self.path == ":memory:":
            # Banco em memória precisa preservar a conexão original. Não há suporte a
            # múltiplas conexões independentes nesse modo de teste/execução.
            conn = self.conn
            owned = False
        else:
            conn = await aiosqlite.connect(self.path, timeout=10)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA busy_timeout = 10000")
            owned = True
        try:
            await conn.execute("BEGIN IMMEDIATE")
            yield DatabaseSession(conn)
            await conn.commit()
        except BaseException:
            await conn.rollback()
            raise
        finally:
            if owned:
                await conn.close()

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

    async def reservar_pesquisa_catalogo(self, user_id: int, limite: int = 3, janela_minutos: int = 10):
        """Rate limit persistente para impedir abuso/custo acidental da busca com IA."""
        limite = max(1, min(20, int(limite)))
        janela_minutos = max(1, min(1440, int(janela_minutos)))
        async with self.transaction() as tx:
            count = await tx._one(
                """SELECT COUNT(*) AS total FROM catalog_search_requests
                   WHERE user_id=? AND created_at >= datetime('now', ?)""",
                (user_id, f"-{janela_minutos} minutes"),
            )
            total = int(count["total"] or 0)
            if total >= limite:
                oldest = await tx._one(
                    """SELECT created_at FROM catalog_search_requests
                       WHERE user_id=? AND created_at >= datetime('now', ?)
                       ORDER BY created_at ASC LIMIT 1""",
                    (user_id, f"-{janela_minutos} minutes"),
                )
                return False, janela_minutos, oldest["created_at"] if oldest else None
            await tx.conn.execute("INSERT INTO catalog_search_requests(user_id) VALUES (?)", (user_id,))
            # Limpeza oportunista para a tabela não crescer indefinidamente.
            await tx.conn.execute("DELETE FROM catalog_search_requests WHERE created_at < datetime('now','-30 days')")
            return True, limite - total - 1, None

    async def log(self, actor_id: int, action: str, details: str = ""):
        await self.conn.execute(
            "INSERT INTO logs(actor_id, action, details) VALUES (?,?,?)",
            (actor_id, action, details),
        )
        await self.conn.commit()

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
        cur = await self.conn.execute(
            "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url, proof_msg_id) VALUES (?,?,?,?,?,?)",
            (user_id, game, platform, earned_at, proof_url, proof_msg_id),
        )
        await self.conn.commit()
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
            cur = await tx.conn.execute(
                "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url, proof_msg_id) VALUES (?,?,?,?,?,?)",
                (user_id, game, platform, earned_at, proof_url, proof_msg_id),
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

    async def aprovar_platina_com_recompensa(self, platina_id: int, reviewer_id: int, xp: int, denarios: int):
        """Aprova e credita recompensa na mesma transação; retorna None se já decidida."""
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                "UPDATE platinas SET status='approved', reviewer_id=? WHERE id=? AND status='pending'",
                (reviewer_id, platina_id),
            )
            if cur.rowcount != 1:
                return None
            row = await tx._one("SELECT user_id FROM platinas WHERE id=?", (platina_id,))
            if not row:
                raise RuntimeError("Platina desapareceu durante a aprovação.")
            user_id = int(row["user_id"])
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            before = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            old_xp = int(before["xp"])
            await tx.conn.execute(
                "UPDATE users SET xp=MAX(0,xp+?), denarios=MAX(0,denarios+?) WHERE user_id=?",
                (int(xp), int(denarios), user_id),
            )
            after = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            new_xp = int(after["xp"])
            return nivel_por_xp(old_xp), nivel_por_xp(new_xp), new_xp, user_id

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
            "SELECT 1 FROM zerados WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)",
            (user_id, game, platform),
        )
        return row is not None

    async def criar_zerado(self, user_id, game, platform, finished_at, comment="", xp=0, denarios=0) -> int:
        cur = await self.conn.execute(
            """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, game, platform, finished_at, comment, xp, denarios),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def registrar_zerado_com_recompensa(
        self, user_id, game, platform, finished_at, comment="",
        xp_configurado=0, denarios_configurados=0, limite_diario=0,
    ):
        """Deduplica, aplica limite diário, grava e credita recompensa numa única transação."""
        async with self.transaction() as tx:
            dup = await tx._one(
                "SELECT id FROM zerados WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?) LIMIT 1",
                (user_id, game, platform),
            )
            if dup:
                return None
            recent = await tx._one(
                "SELECT COUNT(*) AS total FROM zerados WHERE user_id=? AND created_at >= datetime('now','-1 day')",
                (user_id,),
            )
            total_recent = int(recent["total"] or 0)
            xp = max(0, int(xp_configurado or 0))
            denarios = max(0, int(denarios_configurados or 0))
            limite = max(0, int(limite_diario or 0))
            if limite > 0 and total_recent >= limite:
                xp = denarios = 0
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded)
                   VALUES (?,?,?,?,?,?,?)""",
                (user_id, game, platform, finished_at, comment, xp, denarios),
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
                "SELECT id FROM zerados WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?) LIMIT 1",
                (user_id, game, platform),
            )
            if dup:
                return None
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded)
                   VALUES (?,?,?,?,?,?,?)""",
                (user_id, game, platform, finished_at, comment, xp, denarios),
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
            "SELECT * FROM zerados WHERE user_id=? ORDER BY finished_at DESC, id DESC", (user_id,)
        )

    async def contar_zerados(self, user_id: int) -> int:
        row = await self._one("SELECT COUNT(*) AS c FROM zerados WHERE user_id=?", (user_id,))
        return row["c"]

    async def contar_zerados_recentes(self, user_id: int) -> int:
        """Registros das últimas 24h (usado no limite diário de XP)."""
        row = await self._one(
            "SELECT COUNT(*) AS c FROM zerados WHERE user_id=? AND created_at >= datetime('now','-1 day')",
            (user_id,),
        )
        return row["c"]

    async def posicao_zerados(self, quantidade: int) -> int:
        row = await self._one(
            """SELECT COUNT(*)+1 AS p FROM (
                 SELECT user_id, COUNT(*) AS c FROM zerados GROUP BY user_id HAVING c > ?)""",
            (quantidade,),
        )
        return row["p"]

    async def ranking_zerados(self, limite=10):
        return await self._all(
            "SELECT user_id, COUNT(*) AS valor FROM zerados GROUP BY user_id ORDER BY valor DESC LIMIT ?",
            (limite,),
        )

    async def ranking_zerados_mensal(self, mes: str, limite=10):
        """mes no formato AAAA-MM, baseado na data em que o jogo foi zerado."""
        return await self._all(
            """SELECT user_id, COUNT(*) AS valor FROM zerados
               WHERE substr(finished_at,1,7)=? GROUP BY user_id ORDER BY valor DESC LIMIT ?""",
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
