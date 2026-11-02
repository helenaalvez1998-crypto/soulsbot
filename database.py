import os
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
CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id   INTEGER NOT NULL,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        # migração para bancos criados antes da coluna proof_msg_id
        cols = [r["name"] for r in await self._all("PRAGMA table_info(platinas)")]
        if "proof_msg_id" not in cols:
            await self.conn.execute("ALTER TABLE platinas ADD COLUMN proof_msg_id INTEGER")
        await self.conn.commit()

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

    # ---------- usuários ----------
    async def get_user(self, user_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        return await self._one("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def add_reward(self, user_id: int, xp: int, denarios: int):
        """Aplica XP/Denários sem deixar saldos negativos; devolve níveis antigo/novo e XP total."""
        user = await self.get_user(user_id)
        antigo = nivel_por_xp(user["xp"])
        await self.conn.execute(
            "UPDATE users SET xp = MAX(0, xp + ?), denarios = MAX(0, denarios + ?) WHERE user_id=?",
            (xp, denarios, user_id),
        )
        await self.conn.commit()
        atualizado = await self._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
        novo_xp = int(atualizado["xp"])
        return antigo, nivel_por_xp(novo_xp), novo_xp

    # ---------- loja cosmética ----------
    async def inventario_do_usuario(self, user_id: int):
        """Lista os itens comprados pelo usuário, incluindo seu estado de equipamento."""
        return await self._all(
            "SELECT item, tipo, equipado FROM inventario WHERE user_id=? ORDER BY tipo, item",
            (user_id,),
        )

    async def comprar_item(self, user_id: int, item: str, tipo: str, preco: int) -> str:
        """Compra um item uma única vez e debita Denários apenas quando há saldo."""
        await self.get_user(user_id)
        existente = await self._one(
            "SELECT 1 FROM inventario WHERE user_id=? AND item=?", (user_id, item)
        )
        if existente:
            return "ja_tem"

        cur = await self.conn.execute(
            "UPDATE users SET denarios=denarios-? WHERE user_id=? AND denarios>=?",
            (preco, user_id, preco),
        )
        if cur.rowcount != 1:
            await self.conn.commit()
            return "sem_saldo"

        try:
            await self.conn.execute(
                "INSERT INTO inventario(user_id, item, tipo, equipado) VALUES (?,?,?,0)",
                (user_id, item, tipo),
            )
        except Exception:
            # Se outra interação comprou o mesmo item simultaneamente, devolve o débito.
            await self.conn.execute(
                "UPDATE users SET denarios=denarios+? WHERE user_id=?", (preco, user_id)
            )
            await self.conn.commit()
            existente = await self._one(
                "SELECT 1 FROM inventario WHERE user_id=? AND item=?", (user_id, item)
            )
            if existente:
                return "ja_tem"
            raise

        await self.conn.commit()
        return "ok"

    async def equipar_item(self, user_id: int, item: str, tipo: str) -> bool:
        """Equipa um item que pertence ao usuário e desativa os outros do mesmo tipo."""
        existente = await self._one(
            "SELECT 1 FROM inventario WHERE user_id=? AND item=? AND tipo=?",
            (user_id, item, tipo),
        )
        if not existente:
            return False
        await self.conn.execute(
            "UPDATE inventario SET equipado=0 WHERE user_id=? AND tipo=?", (user_id, tipo)
        )
        await self.conn.execute(
            "UPDATE inventario SET equipado=1 WHERE user_id=? AND item=? AND tipo=?",
            (user_id, item, tipo),
        )
        await self.conn.commit()
        return True

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
        cur = await self.conn.execute(
            "UPDATE platinas SET status=?, reviewer_id=? WHERE id=? AND status='pending'",
            (status, reviewer_id, platina_id),
        )
        await self.conn.commit()
        return cur.rowcount == 1

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
