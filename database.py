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
    rating      INTEGER,
    difficulty  INTEGER,
    comment     TEXT NOT NULL DEFAULT '',
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
    rating        INTEGER,
    difficulty    INTEGER,
    comment       TEXT NOT NULL DEFAULT '',
    proof_msg_id  INTEGER,
    proof_url     TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'pending',
    reviewer_id   INTEGER,
    reject_reason TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sl_cat ON sl_runs(game_id, challenge_id, status);
CREATE INDEX IF NOT EXISTS idx_sl_user_status ON sl_runs(user_id, status);
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
    rating           INTEGER,
    difficulty       INTEGER,
    xp_awarded       INTEGER NOT NULL DEFAULT 0,
    denarios_awarded INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'approved', -- pending | approved | rejected
    reviewer_id      INTEGER,
    proof_msg_id     INTEGER,
    approved_at      TEXT,
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

-- Preferências úteis do membro, sem depender do estado volátil das Views do Discord.
CREATE TABLE IF NOT EXISTS user_game_preferences (
    user_id INTEGER PRIMARY KEY,
    last_platform TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_notification_preferences (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    approvals INTEGER NOT NULL DEFAULT 1,
    rejections INTEGER NOT NULL DEFAULT 1,
    levels INTEGER NOT NULL DEFAULT 1,
    replies INTEGER NOT NULL DEFAULT 1,
    challenges INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(guild_id, user_id)
);

-- Caixa de entrada persistente para avisos cuja DM não pôde ser entregue.
CREATE TABLE IF NOT EXISTS user_notification_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    dedupe_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_notification_inbox_user
    ON user_notification_inbox(guild_id, user_id, read_at, id DESC);

-- Evita premiar mensagens repetidas e limita XP por atividade textual diária.
CREATE TABLE IF NOT EXISTS xp_message_awards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_xp_message_user_time
    ON xp_message_awards(guild_id, user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_xp_message_hash_time
    ON xp_message_awards(guild_id, user_id, content_hash, created_at);

"""


# Colunas adicionadas depois da primeira versão: aplicadas em bancos já existentes.
SCHEMA_CARTAS = """
CREATE TABLE IF NOT EXISTS cartas_colecao (
    user_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'pack',
    game_name TEXT NOT NULL DEFAULT '',
    obtained_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, card_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cartas_colecao_user ON cartas_colecao(user_id, obtained_at);
CREATE TABLE IF NOT EXISTS cartas_primordiais_resgatadas (
    card_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    obtained_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS cartas_kit_inicial (
    user_id INTEGER PRIMARY KEY,
    delivered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_almas (
    user_id INTEGER PRIMARY KEY,
    quantidade INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_pity (
    user_id INTEGER PRIMARY KEY,
    comuns_seguidas INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_decks (
    user_id INTEGER PRIMARY KEY,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_deck_itens (
    user_id INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    PRIMARY KEY(user_id, slot),
    UNIQUE(user_id, card_id),
    FOREIGN KEY(user_id) REFERENCES cartas_decks(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_duelos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER,
    creator_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    aposta INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'invited',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    current_round INTEGER NOT NULL DEFAULT 1,
    round_deadline TEXT,
    winner_id INTEGER,
    payout INTEGER NOT NULL DEFAULT 0,
    burned INTEGER NOT NULL DEFAULT 0,
    end_reason TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(creator_id) REFERENCES users(user_id),
    FOREIGN KEY(opponent_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_cartas_duelos_status_deadline ON cartas_duelos(status, expires_at, round_deadline);
CREATE INDEX IF NOT EXISTS idx_cartas_duelos_players_created ON cartas_duelos(creator_id, opponent_id, created_at);
CREATE TABLE IF NOT EXISTS cartas_duelo_deck (
    duel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    PRIMARY KEY(duel_id, user_id, slot),
    UNIQUE(duel_id, user_id, card_id),
    FOREIGN KEY(duel_id) REFERENCES cartas_duelos(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_duelo_jogadas (
    duel_id INTEGER NOT NULL,
    round_no INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    power_final INTEGER,
    type_bonus INTEGER NOT NULL DEFAULT 0,
    skill_bonus INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(duel_id, round_no, user_id),
    FOREIGN KEY(duel_id) REFERENCES cartas_duelos(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_duelo_rounds (
    duel_id INTEGER NOT NULL,
    round_no INTEGER NOT NULL,
    card_a_id TEXT NOT NULL,
    card_b_id TEXT NOT NULL,
    card_a_name TEXT NOT NULL,
    card_b_name TEXT NOT NULL,
    power_a INTEGER NOT NULL,
    power_b INTEGER NOT NULL,
    type_bonus_a INTEGER NOT NULL DEFAULT 0,
    type_bonus_b INTEGER NOT NULL DEFAULT 0,
    skill_bonus_a INTEGER NOT NULL DEFAULT 0,
    skill_bonus_b INTEGER NOT NULL DEFAULT 0,
    combo_bonus_a INTEGER NOT NULL DEFAULT 0,
    combo_bonus_b INTEGER NOT NULL DEFAULT 0,
    combo_name_a TEXT NOT NULL DEFAULT '',
    combo_name_b TEXT NOT NULL DEFAULT '',
    skill_text_a TEXT NOT NULL DEFAULT '',
    skill_text_b TEXT NOT NULL DEFAULT '',
    winner_side TEXT NOT NULL,
    narration TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(duel_id, round_no),
    FOREIGN KEY(duel_id) REFERENCES cartas_duelos(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_key TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    denarios_delta INTEGER NOT NULL DEFAULT 0,
    almas_delta INTEGER NOT NULL DEFAULT 0,
    duel_id INTEGER,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_cartas_transacoes_user_time ON cartas_transacoes(user_id, created_at);
CREATE TABLE IF NOT EXISTS cartas_duelo_participacoes (
    duel_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    won INTEGER NOT NULL DEFAULT 0,
    xp_awarded INTEGER NOT NULL DEFAULT 0,
    week_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(duel_id, user_id),
    FOREIGN KEY(duel_id) REFERENCES cartas_duelos(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(opponent_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_cartas_participacao_user_week
    ON cartas_duelo_participacoes(user_id, week_key, created_at);
CREATE TABLE IF NOT EXISTS cartas_missoes_recompensas (
    user_id INTEGER NOT NULL,
    week_key TEXT NOT NULL,
    mission_code TEXT NOT NULL,
    reward_almas INTEGER NOT NULL,
    trigger_duel_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, week_key, mission_code),
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(trigger_duel_id) REFERENCES cartas_duelos(id)
);
CREATE INDEX IF NOT EXISTS idx_cartas_missoes_duel
    ON cartas_missoes_recompensas(trigger_duel_id, user_id);
CREATE TABLE IF NOT EXISTS cartas_atelie_sessoes (
    user_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    game_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'awaiting_upload',
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_atelie_artes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    game_name TEXT NOT NULL DEFAULT '',
    channel_id INTEGER,
    message_id INTEGER,
    attachment_id INTEGER,
    status TEXT NOT NULL DEFAULT 'uploading',
    reviewed_by INTEGER,
    rejection_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cartas_atelie_user_card_status
    ON cartas_atelie_artes(user_id, card_id, status, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cartas_atelie_pending_unique
    ON cartas_atelie_artes(user_id, card_id)
    WHERE status IN ('uploading','pending');
"""


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
    "zerados": {
        # Registros anteriores continuam aprovados. Os novos entram como pending.
        "status": "TEXT NOT NULL DEFAULT 'approved'",
        "reviewer_id": "INTEGER",
        "proof_msg_id": "INTEGER",
        "approved_at": "TEXT",
        "source_platina_id": "INTEGER",
        "rating": "INTEGER",
        "difficulty": "INTEGER",
        "reject_reason": "TEXT NOT NULL DEFAULT ''",
    },
    "platinas": {
        "rating": "INTEGER",
        "difficulty": "INTEGER",
        "comment": "TEXT NOT NULL DEFAULT ''",
        "reject_reason": "TEXT NOT NULL DEFAULT ''",
    },
    "sl_runs": {
        "rating": "INTEGER",
        "difficulty": "INTEGER",
        "comment": "TEXT NOT NULL DEFAULT ''",
    },
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
    "cartas_duelo_rounds": {
        "combo_bonus_a": "INTEGER NOT NULL DEFAULT 0",
        "combo_bonus_b": "INTEGER NOT NULL DEFAULT 0",
        "combo_name_a": "TEXT NOT NULL DEFAULT ''",
        "combo_name_b": "TEXT NOT NULL DEFAULT ''",
        "skill_text_a": "TEXT NOT NULL DEFAULT ''",
        "skill_text_b": "TEXT NOT NULL DEFAULT ''",
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
CREATE INDEX IF NOT EXISTS idx_zer_user_status ON zerados(user_id, status);
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
        # Conexão de escrita persistente (arquivo): evita abrir/configurar uma conexão
        # SQLite nova a cada transação. O SQLite só permite um escritor por vez, então
        # serializar com um lock não reduz o paralelismo real.
        self._writer: aiosqlite.Connection | None = None
        self._writer_lock = asyncio.Lock()
        self._writer_owner: asyncio.Task | None = None
        # Cache em memória da tabela kv (configurações por servidor). GuildConfig.get() é
        # chamado a cada mensagem e a cada botão; sem cache, cada chamada entra na fila
        # da única conexão SQLite e atrasa as respostas das interações.
        self._kv_cache: dict[str, str | None] = {}

    async def connect(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.conn = await aiosqlite.connect(self.path, timeout=10)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA busy_timeout = 10000")
        if self.path != ":memory:":
            await self.conn.execute("PRAGMA journal_mode = WAL")
            await self.conn.execute("PRAGMA synchronous = NORMAL")
        await self.conn.execute("PRAGMA temp_store = MEMORY")
        await self.conn.execute("PRAGMA cache_size = -20000")  # ~20 MB de cache de páginas
        await self.conn.executescript(SCHEMA)
        await self.conn.executescript(SCHEMA_CARTAS)
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
        await self.conn.executescript(INDICES_POS_MIGRACAO)
        await self.conn.commit()

    @asynccontextmanager
    async def transaction(self):
        """Transação isolada; serializa o modo :memory: que compartilha uma conexão."""
        # Não criar silenciosamente um banco vazio caso a inicialização falhe.
        if self.conn is None:
            raise RuntimeError("Database.connect() precisa ser chamado antes de transaction().")
        memory_db = self.path == ":memory:"
        tarefa = asyncio.current_task()
        if tarefa is not None and self._writer_owner is tarefa:
            # Antes isso falhava após 10s com "database is locked"; agora falha na hora.
            raise RuntimeError("transaction() aninhada: já existe uma transação aberta nesta tarefa.")
        if memory_db:
            await self._memory_lock.acquire()
        else:
            await asyncio.wait_for(self._writer_lock.acquire(), timeout=30)
        self._writer_owner = tarefa
        conn = None
        try:
            if memory_db:
                # Não abrir uma segunda conexão para :memory: ela apontaria para outro banco.
                conn = self.conn
            else:
                if self._writer is None:
                    self._writer = await self._abrir_writer()
                conn = self._writer
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield DatabaseSession(conn)
                await conn.commit()
            except BaseException:
                try:
                    await conn.rollback()
                except Exception:
                    # Conexão em estado ruim: descarta para que a próxima transação reabra.
                    if not memory_db:
                        self._writer = None
                        try:
                            await conn.close()
                        except Exception:
                            pass
                raise
        finally:
            self._writer_owner = None
            if memory_db:
                self._memory_lock.release()
            else:
                self._writer_lock.release()

    async def _abrir_writer(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.path, timeout=10)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA busy_timeout = 10000")
        await conn.execute("PRAGMA synchronous = NORMAL")
        await conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    async def close(self):
        if self._writer is not None:
            try:
                await self._writer.close()
            finally:
                self._writer = None
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

    # ---------- usuários ----------
    async def get_user(self, user_id: int):
        await self.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        return await self._one("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def resumo_painel_nara(self, user_id: int) -> dict:
        """Carrega em uma consulta os indicadores usados pela central /nara.

        Evita executar estatísticas completas de runs e avaliações quando a central
        só precisa de contagens e da média geral do membro.
        """
        user_id = int(user_id)
        await self.conn.execute(
            "INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,)
        )
        await self.conn.commit()
        row = await self._one(
            """WITH avaliacoes AS (
                   SELECT rating FROM platinas
                    WHERE user_id=? AND status='approved'
                   UNION ALL
                   SELECT rating FROM zerados
                    WHERE user_id=? AND status='approved' AND source_platina_id IS NULL
                   UNION ALL
                   SELECT rating FROM sl_runs
                    WHERE user_id=? AND status='approved'
               ), media AS (
                   SELECT AVG(rating) AS media_nota, COUNT(rating) AS qtd_notas
                     FROM avaliacoes
               )
               SELECT u.xp, u.denarios,
                      (SELECT COUNT(*) FROM platinas
                        WHERE user_id=u.user_id AND status='approved') AS platinas,
                      (SELECT COUNT(*) FROM zerados
                        WHERE user_id=u.user_id AND status='approved') AS zerados,
                      (SELECT COUNT(*) FROM sl_runs
                        WHERE user_id=u.user_id AND status='approved') AS runs,
                      ((SELECT COUNT(*) FROM platinas
                          WHERE user_id=u.user_id AND status='pending') +
                       (SELECT COUNT(*) FROM zerados
                          WHERE user_id=u.user_id AND status='pending') +
                       (SELECT COUNT(*) FROM sl_runs
                          WHERE user_id=u.user_id AND status='pending')) AS pendentes,
                      media.media_nota, media.qtd_notas
                 FROM users AS u CROSS JOIN media
                WHERE u.user_id=?""",
            (user_id, user_id, user_id, user_id),
        )
        if row is None:
            return {
                "xp": 0, "denarios": 0, "platinas": 0, "zerados": 0,
                "runs": 0, "pendentes": 0, "media_nota": None, "qtd_notas": 0,
            }
        return {
            "xp": int(row["xp"] or 0),
            "denarios": int(row["denarios"] or 0),
            "platinas": int(row["platinas"] or 0),
            "zerados": int(row["zerados"] or 0),
            "runs": int(row["runs"] or 0),
            "pendentes": int(row["pendentes"] or 0),
            "media_nota": float(row["media_nota"]) if row["media_nota"] is not None else None,
            "qtd_notas": int(row["qtd_notas"] or 0),
        }

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

    async def ajustar_economia_por_admin(
        self, user_id: int, actor_id: int, xp_delta: int = 0,
        denarios_delta: int = 0, motivo: str = "", guild_id: int | None = None,
    ) -> dict:
        """Ajusta XP/Denários atomicamente e registra a auditoria na mesma transação.

        Valores finais nunca ficam negativos. Os deltas retornados representam o que
        realmente foi aplicado (importante quando a remoção supera o saldo disponível).
        """
        user_id = int(user_id)
        actor_id = int(actor_id)
        guild_id = int(guild_id) if guild_id is not None else None
        xp_delta = int(xp_delta)
        denarios_delta = int(denarios_delta)
        motivo = " ".join(str(motivo or "").split())[:200]
        limite = 1_000_000_000
        if user_id <= 0 or actor_id <= 0:
            raise ValueError("Identificadores de usuário inválidos.")
        if abs(xp_delta) > limite or abs(denarios_delta) > limite:
            raise ValueError("O ajuste máximo permitido é de 1.000.000.000 por recurso.")
        if xp_delta == 0 and denarios_delta == 0:
            raise ValueError("Informe uma quantidade de XP ou Denários diferente de zero.")
        if not motivo:
            raise ValueError("Informe o motivo do ajuste administrativo.")

        async with self.transaction() as tx:
            await tx.conn.execute(
                "INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,)
            )
            antes = await tx._one(
                "SELECT xp, denarios FROM users WHERE user_id=?", (user_id,)
            )
            xp_antes = int(antes["xp"] or 0)
            denarios_antes = int(antes["denarios"] or 0)
            xp_depois = max(0, xp_antes + xp_delta)
            denarios_depois = max(0, denarios_antes + denarios_delta)
            xp_aplicado = xp_depois - xp_antes
            denarios_aplicados = denarios_depois - denarios_antes

            await tx.conn.execute(
                "UPDATE users SET xp=?, denarios=? WHERE user_id=?",
                (xp_depois, denarios_depois, user_id),
            )
            detalhes = (
                f"guild={guild_id or 0}; target={user_id}; "
                f"xp={xp_antes}->{xp_depois}; xp_delta={xp_aplicado}; "
                f"denarios={denarios_antes}->{denarios_depois}; "
                f"denarios_delta={denarios_aplicados}; motivo={motivo}"
            )
            await tx.conn.execute(
                "INSERT INTO logs(actor_id, action, details) VALUES (?,?,?)",
                (actor_id, "admin_economia_ajustada", detalhes),
            )

            return {
                "user_id": user_id,
                "actor_id": actor_id,
                "xp_antes": xp_antes,
                "xp_depois": xp_depois,
                "xp_delta": xp_aplicado,
                "denarios_antes": denarios_antes,
                "denarios_depois": denarios_depois,
                "denarios_delta": denarios_aplicados,
                "nivel_antes": nivel_por_xp(xp_antes),
                "nivel_depois": nivel_por_xp(xp_depois),
                "motivo": motivo,
            }

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

    async def criar_platina(self, user_id, game, platform, earned_at, proof_url, proof_msg_id=None,
                            rating=None, comment="", difficulty=None) -> int:
        if difficulty is not None and (type(difficulty) is not int or not 1 <= difficulty <= 5):
            raise ValueError("A dificuldade percebida deve ser um número inteiro entre 1 e 5.")
        cur = await self.conn.execute(
            "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url, proof_msg_id, rating, difficulty, comment) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, game, platform, earned_at, proof_url, proof_msg_id, rating, difficulty, str(comment or "")[:500]),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def criar_platina_unica(self, user_id, game, platform, earned_at, proof_url, proof_msg_id=None,
                                  rating=None, comment="", difficulty=None):
        """Cria registro sob BEGIN IMMEDIATE para impedir duplicata em cliques simultâneos."""
        if rating is not None and (type(rating) is not int or not 1 <= rating <= 10):
            raise ValueError("A nota do jogo deve ser um número inteiro entre 1 e 10.")
        if difficulty is not None and (type(difficulty) is not int or not 1 <= difficulty <= 5):
            raise ValueError("A dificuldade percebida deve ser um número inteiro entre 1 e 5.")
        async with self.transaction() as tx:
            existente = await tx._one(
                """SELECT id FROM platinas WHERE user_id=? AND lower(game)=lower(?)
                   AND lower(platform)=lower(?) AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if existente:
                return None
            cur = await tx.conn.execute(
                "INSERT INTO platinas(user_id, game, platform, earned_at, proof_url, proof_msg_id, rating, difficulty, comment) VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, game, platform, earned_at, proof_url, proof_msg_id, rating, difficulty, str(comment or "")[:500]),
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

    async def decidir_platina(
        self, platina_id: int, status: str, reviewer_id: int, motivo: str = ""
    ) -> bool:
        """Registra a decisão e o motivo, somente se a platina ainda estiver pendente."""
        if status not in ("approved", "rejected"):
            return False
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE platinas SET status=?, reviewer_id=?, reject_reason=?
                   WHERE id=? AND status='pending'""",
                (status, reviewer_id, str(motivo or "")[:300] if status == "rejected" else "", platina_id),
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
                cur_z = await tx.conn.execute(
                    """INSERT INTO zerados(
                           user_id, game, platform, finished_at, comment, rating, status,
                           reviewer_id, approved_at, source_platina_id, difficulty
                       ) VALUES (?,?,?,?,?,?,'approved',?,CURRENT_TIMESTAMP,?,?)""",
                    (user_id, platina["game"], platina["platform"], platina["earned_at"],
                     str(platina["comment"] or "Registro automático pela aprovação da platina."),
                     platina["rating"], reviewer_id, platina_id, platina["difficulty"]),
                )
                zerado_id = int(cur_z.lastrowid)
                deve_premiar_zerado = True
                zerado_status_anterior = None
                proof_msg_id = None
            elif existing["status"] == "approved":
                # Já existe conclusão validada. Apenas vincula a origem se ainda não houver.
                zerado_id = int(existing["id"])
                await tx.conn.execute(
                    """UPDATE zerados
                       SET source_platina_id=COALESCE(source_platina_id, ?),
                           rating=COALESCE(rating, ?),
                           difficulty=COALESCE(difficulty, ?),
                           comment=CASE WHEN trim(comment)='' THEN ? ELSE comment END
                       WHERE id=?""",
                    (platina_id, platina["rating"], platina["difficulty"],
                     str(platina["comment"] or ""), zerado_id),
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
                           finished_at=?, source_platina_id=?, rating=COALESCE(?, rating),
                           difficulty=COALESCE(?, difficulty),
                           comment=CASE WHEN trim(?)<>'' THEN ? ELSE comment END
                       WHERE id=? AND status='pending'""",
                    (reviewer_id, platina["earned_at"], platina_id, platina["rating"],
                     platina["difficulty"], str(platina["comment"] or ""),
                     str(platina["comment"] or ""), zerado_id),
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

            # Cada zerado aprovado e cada platina aprovada rendem cartas próprias.
            # A platina também garante o desbloqueio do marco de zerado, mesmo quando
            # o membro não enviou um registro de zerado separado.
            from sistemas.cartas import carta_jogo
            for marco in ("zerado", "platina"):
                carta = carta_jogo(str(platina["game"]), marco)
                await tx.conn.execute(
                    """INSERT OR IGNORE INTO cartas_colecao(user_id,card_id,quantidade,source,game_name)
                       VALUES (?,?,1,?,?)""",
                    (user_id, carta.id, marco, str(platina["game"])[:120]),
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
                "platina_rating": platina["rating"],
                "platina_difficulty": platina["difficulty"],
                "platina_comment": platina["comment"],
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

    async def criar_zerado_pendente(self, user_id, game, platform, finished_at, comment="", rating=None, difficulty=None):
        """Cria uma solicitação pendente sem creditar XP/Denários antes da revisão."""
        if rating is not None and (type(rating) is not int or not 1 <= rating <= 10):
            raise ValueError("A nota do jogo deve ser um número inteiro entre 1 e 10.")
        if difficulty is not None and (type(difficulty) is not int or not 1 <= difficulty <= 5):
            raise ValueError("A dificuldade percebida deve ser um número inteiro entre 1 e 5.")
        async with self.transaction() as tx:
            dup = await tx._one(
                """SELECT id FROM zerados
                   WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                     AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if dup:
                return None
            cur = await tx.conn.execute(
                """INSERT INTO zerados(
                       user_id, game, platform, finished_at, comment, rating, difficulty, status
                   ) VALUES (?,?,?,?,?,?,?,'pending')""",
                (user_id, game, platform, finished_at, str(comment or "")[:500], rating, difficulty),
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
                       xp_awarded=?, denarios_awarded=?, reject_reason='' WHERE id=? AND status='pending'""",
                (reviewer_id, xp, denarios, zerado_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("O registro de zerado mudou durante a aprovação.")
            from sistemas.cartas import carta_jogo
            carta = carta_jogo(str(row["game"]), "zerado")
            # A recompensa da carta faz parte da mesma transação da aprovação.
            # O UPSERT repara metadados ausentes sem duplicar ou aumentar quantidade.
            carta_existente_antes = await tx._one(
                "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (int(row["user_id"]), carta.id),
            )
            await tx.conn.execute(
                """INSERT INTO cartas_colecao(user_id,card_id,quantidade,source,game_name)
                   VALUES (?,?,1,'zerado',?)
                   ON CONFLICT(user_id,card_id) DO UPDATE SET
                       game_name=CASE WHEN cartas_colecao.game_name='' THEN excluded.game_name
                                      ELSE cartas_colecao.game_name END,
                       source=CASE WHEN cartas_colecao.source='' THEN 'zerado'
                                   ELSE cartas_colecao.source END""",
                (int(row["user_id"]), carta.id, str(row["game"])[:120]),
            )
            carta_salva = await tx._one(
                "SELECT card_id,game_name FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (int(row["user_id"]), carta.id),
            )
            if carta_salva is None:
                raise RuntimeError(
                    f"Falha ao garantir carta de zerado user={row['user_id']} zerado={zerado_id} card={carta.id}"
                )
            carta_adicionada = carta_existente_antes is None
            return {
                "id": zerado_id, "user_id": int(row["user_id"]), "game": row["game"],
                "platform": row["platform"], "finished_at": row["finished_at"],
                "comment": row["comment"], "rating": row["rating"], "difficulty": row["difficulty"], "proof_msg_id": row["proof_msg_id"],
                "xp": xp, "denarios": denarios, "old_xp": old_xp, "new_xp": new_xp,
                "old_level": old_level, "new_level": new_level,
                "daily_limit_reached": limite_atingido,
                "card_id": carta.id, "card_name": carta.nome,
                "card_rarity": carta.raridade, "card_added": carta_adicionada,
                "card_already_owned": not carta_adicionada,
            }

    async def rejeitar_zerado(self, zerado_id: int, reviewer_id: int, motivo: str = "") -> bool:
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE zerados SET status='rejected', reviewer_id=?, reject_reason=?
                   WHERE id=? AND status='pending'""",
                (reviewer_id, str(motivo or "")[:300], zerado_id),
            )
            return cur.rowcount == 1

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
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded, status, approved_at)
                   VALUES (?,?,?,?,?,?,?,'approved',CURRENT_TIMESTAMP)""",
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
                """SELECT id FROM zerados WHERE user_id=? AND lower(game)=lower(?) AND lower(platform)=lower(?)
                   AND status IN ('pending','approved') LIMIT 1""",
                (user_id, game, platform),
            )
            if dup:
                return None
            cur = await tx.conn.execute(
                """INSERT INTO zerados(user_id, game, platform, finished_at, comment, xp_awarded, denarios_awarded, status, approved_at)
                   VALUES (?,?,?,?,?,?,?,'approved',CURRENT_TIMESTAMP)""",
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
        if key in self._kv_cache:
            return self._kv_cache[key]
        row = await self._one("SELECT value FROM kv WHERE key=?", (key,))
        valor = row["value"] if row else None
        self._kv_cache[key] = valor
        return valor

    async def set_kv(self, key: str, value: str):
        await self.conn.execute(
            "INSERT INTO kv(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await self.conn.commit()
        self._kv_cache[key] = value

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
                await tx.conn.execute("INSERT OR IGNORE INTO sl_games(name) VALUES (?)", (name,))
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

    async def get_ultima_plataforma(self, user_id: int) -> str | None:
        row = await self._one(
            "SELECT last_platform FROM user_game_preferences WHERE user_id=?", (int(user_id),)
        )
        valor = str(row["last_platform"] or "").strip() if row else ""
        return valor or None

    async def set_ultima_plataforma(self, user_id: int, platform: str) -> None:
        platform = str(platform or "").strip()[:30]
        if not platform:
            return
        await self.conn.execute(
            """INSERT INTO user_game_preferences(user_id,last_platform) VALUES (?,?)
               ON CONFLICT(user_id) DO UPDATE SET last_platform=excluded.last_platform,
               updated_at=CURRENT_TIMESTAMP""",
            (int(user_id), platform),
        )
        await self.conn.commit()

    async def titulos_semelhantes(self, nome: str, limite: int = 3) -> list[str]:
        """Sugere títulos existentes para ajudar a evitar variações/duplicatas de nomes."""
        from difflib import SequenceMatcher
        import unicodedata

        def normalizar(valor: str) -> str:
            valor = unicodedata.normalize("NFKD", str(valor or ""))
            valor = "".join(ch for ch in valor if not unicodedata.combining(ch))
            return " ".join(valor.lower().strip().split())

        alvo = normalizar(nome)
        if len(alvo) < 4:
            return []
        rows = await self._all(
            """SELECT name AS titulo FROM games_catalog WHERE status IN ('ready','review')
               UNION SELECT game FROM platinas WHERE status='approved'
               UNION SELECT game FROM zerados WHERE status='approved'
               UNION SELECT name FROM sl_games"""
        )
        candidatos = {}
        for row in rows:
            titulo = str(row["titulo"] if "titulo" in row.keys() else row[0]).strip()
            chave = normalizar(titulo)
            if chave and chave != alvo:
                razao = SequenceMatcher(None, alvo, chave).ratio()
                if razao >= 0.78 or (min(len(alvo), len(chave)) >= 5 and (alvo in chave or chave in alvo)):
                    candidatos[titulo] = max(razao, candidatos.get(titulo, 0))
        return [titulo for titulo, _ in sorted(candidatos.items(), key=lambda item: (-item[1], item[0].lower()))[:max(1, min(int(limite), 5))]]

    async def get_preferencias_notificacao(self, guild_id: int, user_id: int) -> dict:
        row = await self._one(
            "SELECT * FROM user_notification_preferences WHERE guild_id=? AND user_id=?",
            (int(guild_id), int(user_id)),
        )
        keys = ("approvals", "rejections", "levels", "replies", "challenges")
        return {key: bool(row[key]) if row else True for key in keys}

    async def registrar_notificacao_pendente(
        self, guild_id: int, user_id: int, categoria: str, mensagem: str, dedupe_hash: str,
    ) -> bool:
        cur = await self.conn.execute(
            """INSERT OR IGNORE INTO user_notification_inbox
               (guild_id,user_id,category,message,dedupe_hash)
               VALUES (?,?,?,?,?)""",
            (int(guild_id), int(user_id), str(categoria)[:40], str(mensagem)[:1800], str(dedupe_hash)),
        )
        await self.conn.commit()
        return cur.rowcount == 1

    async def listar_notificacoes_pendentes(
        self, guild_id: int, user_id: int, limite: int = 10,
    ) -> list:
        cur = await self.conn.execute(
            """SELECT id,category,message,created_at FROM user_notification_inbox
               WHERE guild_id=? AND user_id=? AND read_at IS NULL
               ORDER BY id DESC LIMIT ?""",
            (int(guild_id), int(user_id), max(1, min(int(limite), 25))),
        )
        return await cur.fetchall()

    async def marcar_notificacoes_lidas(self, guild_id: int, user_id: int) -> int:
        cur = await self.conn.execute(
            """UPDATE user_notification_inbox SET read_at=CURRENT_TIMESTAMP
               WHERE guild_id=? AND user_id=? AND read_at IS NULL""",
            (int(guild_id), int(user_id)),
        )
        await self.conn.commit()
        return int(cur.rowcount)

    async def definir_preferencia_notificacao(
        self, guild_id: int, user_id: int, key: str, enabled: bool
    ) -> None:
        permitidos = {"approvals", "rejections", "levels", "replies", "challenges"}
        if key not in permitidos:
            raise ValueError("Tipo de notificação desconhecido.")
        await self.conn.execute(
            """INSERT INTO user_notification_preferences(guild_id,user_id) VALUES (?,?)
               ON CONFLICT(guild_id,user_id) DO NOTHING""",
            (int(guild_id), int(user_id)),
        )
        await self.conn.execute(
            f"UPDATE user_notification_preferences SET {key}=?,updated_at=CURRENT_TIMESTAMP WHERE guild_id=? AND user_id=?",
            (int(bool(enabled)), int(guild_id), int(user_id)),
        )
        await self.conn.commit()

    async def registrar_xp_mensagem(
        self, guild_id: int, user_id: int, content_hash: str, limite_diario: int = 20
    ) -> bool:
        """Registra uma mensagem elegível sem duplicar texto recente nem exceder a cota diária."""
        import time as _time
        async with self.transaction() as tx:
            # A limpeza de registros antigos não precisa rodar a cada mensagem.
            agora = _time.monotonic()
            if agora - getattr(self, "_xp_purga_em", 0.0) > 3600:
                await tx.conn.execute(
                    "DELETE FROM xp_message_awards WHERE created_at < datetime('now','-30 days')"
                )
                self._xp_purga_em = agora
            duplicada = await tx._one(
                """SELECT 1 FROM xp_message_awards
                   WHERE guild_id=? AND user_id=? AND content_hash=?
                     AND created_at >= datetime('now','-7 days') LIMIT 1""",
                (int(guild_id), int(user_id), str(content_hash)),
            )
            if duplicada:
                return False
            total = await tx._one(
                """SELECT COUNT(*) AS total FROM xp_message_awards
                   WHERE guild_id=? AND user_id=? AND created_at >= datetime('now','-1 day')""",
                (int(guild_id), int(user_id)),
            )
            if int(total["total"] or 0) >= max(1, int(limite_diario)):
                return False
            await tx.conn.execute(
                "INSERT INTO xp_message_awards(guild_id,user_id,content_hash) VALUES (?,?,?)",
                (int(guild_id), int(user_id), str(content_hash)),
            )
            return True

    async def registros_do_usuario(self, user_id: int, limite: int = 30):
        """Lista platinas, zerados e runs em uma linha do tempo com estado e motivo."""
        limite = max(1, min(int(limite), 100))
        return await self._all(
            """SELECT * FROM (
                SELECT 'Platina' AS tipo, p.id, p.game AS titulo, p.platform AS detalhe,
                       p.earned_at AS data, p.status, COALESCE(p.reject_reason,'') AS motivo,
                       p.rating, p.difficulty, COALESCE(p.comment,'') AS comentario,
                       p.created_at AS criado
                  FROM platinas p WHERE p.user_id=?
                UNION ALL
                SELECT 'Zerado' AS tipo, z.id, z.game AS titulo, z.platform AS detalhe,
                       z.finished_at AS data, z.status, COALESCE(z.reject_reason,'') AS motivo,
                       z.rating, z.difficulty, COALESCE(z.comment,'') AS comentario,
                       z.created_at AS criado
                  FROM zerados z WHERE z.user_id=? AND (z.source_platina_id IS NULL OR z.status='rejected')
                UNION ALL
                SELECT 'Run' AS tipo, r.id, g.name AS titulo, c.name AS detalhe,
                       substr(r.created_at,1,10) AS data, r.status, COALESCE(r.reject_reason,'') AS motivo,
                       r.rating, r.difficulty, COALESCE(r.comment,'') AS comentario,
                       r.created_at AS criado
                  FROM sl_runs r JOIN sl_games g ON g.id=r.game_id
                  JOIN sl_challenges c ON c.id=r.challenge_id WHERE r.user_id=?
            ) ORDER BY criado DESC, id DESC LIMIT ?""",
            (int(user_id), int(user_id), int(user_id), limite),
        )

    async def estatisticas_gamer(self, user_id: int) -> dict:
        """Indicadores do perfil sem contar duas vezes o zerado gerado por uma platina."""
        user_id = int(user_id)
        row = await self._one(
            """SELECT COUNT(*) AS total,
                      AVG(rating) AS media_nota, COUNT(rating) AS notas,
                      AVG(difficulty) AS media_dificuldade, COUNT(difficulty) AS dificuldades
               FROM (
                   SELECT rating,difficulty FROM platinas WHERE user_id=? AND status='approved'
                   UNION ALL
                   SELECT rating,difficulty FROM zerados
                     WHERE user_id=? AND status='approved' AND source_platina_id IS NULL
                   UNION ALL
                   SELECT rating,difficulty FROM sl_runs WHERE user_id=? AND status='approved'
               )""",
            (user_id, user_id, user_id),
        )
        plataformas = await self._all(
            """SELECT platform,COUNT(*) AS total FROM (
                   SELECT platform FROM platinas WHERE user_id=? AND status='approved'
                   UNION ALL
                   SELECT platform FROM zerados WHERE user_id=? AND status='approved'
                     AND source_platina_id IS NULL
               ) GROUP BY platform ORDER BY total DESC,platform COLLATE NOCASE LIMIT 3""",
            (user_id, user_id),
        )
        melhores = await self._all(
            """SELECT * FROM (
                   SELECT game AS titulo, platform AS detalhe, rating, difficulty, earned_at AS data, 'Platina' AS tipo
                     FROM platinas WHERE user_id=? AND status='approved' AND rating IS NOT NULL
                   UNION ALL
                   SELECT game AS titulo, platform AS detalhe, rating, difficulty, finished_at AS data, 'Zerado' AS tipo
                     FROM zerados WHERE user_id=? AND status='approved' AND source_platina_id IS NULL AND rating IS NOT NULL
                   UNION ALL
                   SELECT g.name AS titulo,c.name AS detalhe,r.rating,r.difficulty,substr(r.created_at,1,10) AS data,'Run' AS tipo
                     FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id
                    WHERE r.user_id=? AND r.status='approved' AND r.rating IS NOT NULL
               ) ORDER BY rating DESC, data DESC LIMIT 3""",
            (user_id, user_id, user_id),
        )
        recentes = await self._all(
            """SELECT * FROM (
                   SELECT game AS titulo,platform AS detalhe,earned_at AS data,'Platina' AS tipo
                     FROM platinas WHERE user_id=? AND status='approved'
                   UNION ALL
                   SELECT game AS titulo,platform AS detalhe,finished_at AS data,'Zerado' AS tipo
                     FROM zerados WHERE user_id=? AND status='approved' AND source_platina_id IS NULL
                   UNION ALL
                   SELECT g.name AS titulo,c.name AS detalhe,substr(r.created_at,1,10) AS data,'Run' AS tipo
                     FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id
                    WHERE r.user_id=? AND r.status='approved'
               ) ORDER BY data DESC LIMIT 3""",
            (user_id, user_id, user_id),
        )
        return {
            "total_avaliacoes": int(row["total"] or 0),
            "media_nota": float(row["media_nota"]) if row["media_nota"] is not None else None,
            "qtd_notas": int(row["notas"] or 0),
            "media_dificuldade": float(row["media_dificuldade"]) if row["media_dificuldade"] is not None else None,
            "qtd_dificuldades": int(row["dificuldades"] or 0),
            "plataformas": plataformas,
            "melhores": melhores,
            "recentes": recentes,
        }

    async def ranking_jogos_avaliacao(self, minimo: int = 3, limite: int = 10):
        """Classifica jogos pela média das notas aprovadas, com amostra mínima."""
        return await self._all(
            """SELECT titulo,AVG(rating) AS valor,COUNT(rating) AS quantidade FROM (
                   SELECT game AS titulo,rating FROM platinas
                     WHERE status='approved' AND rating IS NOT NULL
                   UNION ALL
                   SELECT game AS titulo,rating FROM zerados
                     WHERE status='approved' AND source_platina_id IS NULL AND rating IS NOT NULL
                   UNION ALL
                   SELECT g.name AS titulo,r.rating FROM sl_runs r
                     JOIN sl_games g ON g.id=r.game_id
                    WHERE r.status='approved' AND r.rating IS NOT NULL
               ) GROUP BY titulo COLLATE NOCASE HAVING COUNT(rating)>=?
               ORDER BY valor DESC,quantidade DESC,titulo COLLATE NOCASE LIMIT ?""",
            (max(1, int(minimo)), max(1, min(int(limite), 50))),
        )

    async def ranking_jogos_dificuldade(self, minimo: int = 3, limite: int = 10):
        """Classifica jogos pela dificuldade percebida média, com amostra mínima."""
        return await self._all(
            """SELECT titulo,AVG(difficulty) AS valor,COUNT(difficulty) AS quantidade FROM (
                   SELECT game AS titulo,difficulty FROM platinas
                     WHERE status='approved' AND difficulty IS NOT NULL
                   UNION ALL
                   SELECT game AS titulo,difficulty FROM zerados
                     WHERE status='approved' AND source_platina_id IS NULL AND difficulty IS NOT NULL
                   UNION ALL
                   SELECT g.name AS titulo,r.difficulty FROM sl_runs r
                     JOIN sl_games g ON g.id=r.game_id
                    WHERE r.status='approved' AND r.difficulty IS NOT NULL
               ) GROUP BY titulo COLLATE NOCASE HAVING COUNT(difficulty)>=?
               ORDER BY valor DESC,quantidade DESC,titulo COLLATE NOCASE LIMIT ?""",
            (max(1, int(minimo)), max(1, min(int(limite), 50))),
        )

    async def ranking_media_avaliacoes(self, minimo: int = 3, limite: int = 10):
        return await self._all(
            """SELECT user_id,AVG(rating) AS valor,COUNT(rating) AS quantidade FROM (
                   SELECT user_id,rating FROM platinas WHERE status='approved' AND rating IS NOT NULL
                   UNION ALL
                   SELECT user_id,rating FROM zerados WHERE status='approved'
                     AND source_platina_id IS NULL AND rating IS NOT NULL
                   UNION ALL
                   SELECT user_id,rating FROM sl_runs WHERE status='approved' AND rating IS NOT NULL
               ) GROUP BY user_id HAVING COUNT(rating)>=?
               ORDER BY valor DESC,quantidade DESC,user_id LIMIT ?""",
            (max(1, int(minimo)), max(1, min(int(limite), 50))),
        )

    async def ranking_media_dificuldade(self, minimo: int = 3, limite: int = 10):
        return await self._all(
            """SELECT user_id,AVG(difficulty) AS valor,COUNT(difficulty) AS quantidade FROM (
                   SELECT user_id,difficulty FROM platinas WHERE status='approved' AND difficulty IS NOT NULL
                   UNION ALL
                   SELECT user_id,difficulty FROM zerados WHERE status='approved'
                     AND source_platina_id IS NULL AND difficulty IS NOT NULL
                   UNION ALL
                   SELECT user_id,difficulty FROM sl_runs WHERE status='approved' AND difficulty IS NOT NULL
               ) GROUP BY user_id HAVING COUNT(difficulty)>=?
               ORDER BY valor DESC,quantidade DESC,user_id LIMIT ?""",
            (max(1, int(minimo)), max(1, min(int(limite), 50))),
        )

    async def resumo_registros_usuario(self, user_id: int) -> dict:
        """Contagens completas por status, sem limitar a linha do tempo recente."""
        rows = await self._all(
            """SELECT status,COUNT(*) AS total FROM (
                   SELECT status FROM platinas WHERE user_id=?
                   UNION ALL
                   SELECT status FROM zerados WHERE user_id=? AND (source_platina_id IS NULL OR status='rejected')
                   UNION ALL
                   SELECT status FROM sl_runs WHERE user_id=?
               ) GROUP BY status""",
            (int(user_id), int(user_id), int(user_id)),
        )
        return {str(row["status"]): int(row["total"] or 0) for row in rows}

    async def registros_pendentes_usuario(self, user_id: int) -> int:
        row = await self._one(
            """SELECT
               (SELECT COUNT(*) FROM platinas WHERE user_id=? AND status='pending') +
               (SELECT COUNT(*) FROM zerados WHERE user_id=? AND status='pending') +
               (SELECT COUNT(*) FROM sl_runs WHERE user_id=? AND status='pending') AS total""",
            (int(user_id), int(user_id), int(user_id)),
        )
        return int(row["total"] or 0)


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



    # ---------- Cartas do Coliseu ----------
    async def coliseu_desbloquear_carta(self, user_id: int, card_id: str, source: str,
                                         game_name: str = "") -> bool:
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            cur = await tx.conn.execute(
                """INSERT OR IGNORE INTO cartas_colecao(user_id,card_id,quantidade,source,game_name)
                   VALUES (?,?,1,?,?)""",
                (int(user_id), str(card_id), str(source)[:30], str(game_name or "")[:120]),
            )
            return cur.rowcount == 1

    async def coliseu_sincronizar_conquistas(self, user_id: int) -> int:
        """Garante cartas retroativas de todos os zerados/platinas já aprovados."""
        from sistemas.cartas import carta_jogo
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            registros = await tx._all(
                """SELECT game,'zerado' AS marco FROM zerados WHERE user_id=? AND status='approved'
                   UNION SELECT game,'platina' AS marco FROM platinas WHERE user_id=? AND status='approved'""",
                (int(user_id), int(user_id)),
            )
            adicionadas = 0
            for row in registros:
                # Uma platina histórica também representa o marco de zerado,
                # mesmo quando não existe um registro separado na tabela zerados.
                marcos = ("zerado", "platina") if str(row["marco"]) == "platina" else ("zerado",)
                for marco in marcos:
                    carta = carta_jogo(str(row["game"]), marco)
                    existente = await tx._one(
                        "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                        (int(user_id), carta.id),
                    )
                    await tx.conn.execute(
                        """INSERT INTO cartas_colecao(user_id,card_id,quantidade,source,game_name)
                           VALUES (?,?,1,?,?)
                           ON CONFLICT(user_id,card_id) DO UPDATE SET
                               source=excluded.source, game_name=excluded.game_name""",
                        (int(user_id), carta.id, marco, str(row["game"])[:120]),
                    )
                    # Contabiliza apenas novas cartas; o UPSERT também repara metadados
                    # de entradas antigas que existiam, mas não podiam ser reconstruídas.
                    if existente is None:
                        adicionadas += 1
            return adicionadas

    async def coliseu_reivindicar_patentes(self, user_id: int, card_ids: list[str]) -> int:
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            novas = 0
            for card_id in card_ids:
                cur = await tx.conn.execute(
                    """INSERT OR IGNORE INTO cartas_colecao(user_id,card_id,quantidade,source)
                       VALUES (?,?,1,'patente')""",
                    (int(user_id), str(card_id)),
                )
                novas += max(0, cur.rowcount)
            return novas

    async def coliseu_entregar_kit_inicial(self, user_id: int, card_ids: list[str]) -> int:
        """Entrega um deck inicial gratuito uma única vez, removendo a barreira de entrada."""
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            cur = await tx.conn.execute(
                "INSERT OR IGNORE INTO cartas_kit_inicial(user_id) VALUES (?)", (int(user_id),)
            )
            if cur.rowcount != 1:
                return 0
            novas = 0
            for card_id in card_ids:
                added = await tx.conn.execute(
                    """INSERT OR IGNORE INTO cartas_colecao(user_id,card_id,quantidade,source)
                       VALUES (?,?,1,'kit_inicial')""",
                    (int(user_id), str(card_id)),
                )
                novas += max(0, added.rowcount)
            return novas

    async def coliseu_estado_usuario(self, user_id: int):
        user_id = int(user_id)
        await self.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await self.conn.execute("INSERT OR IGNORE INTO cartas_almas(user_id) VALUES (?)", (user_id,))
        await self.conn.execute("INSERT OR IGNORE INTO cartas_pity(user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        row = await self._one(
            """SELECT u.xp, u.denarios,
                      COALESCE((SELECT quantidade FROM cartas_almas WHERE user_id=u.user_id), 0) AS almas,
                      COALESCE((SELECT comuns_seguidas FROM cartas_pity WHERE user_id=u.user_id), 0) AS pity,
                      (SELECT COUNT(*) FROM cartas_colecao WHERE user_id=u.user_id) AS cartas,
                      (SELECT COUNT(*) FROM cartas_deck_itens WHERE user_id=u.user_id) AS deck
                 FROM users AS u WHERE u.user_id=?""",
            (user_id,),
        )
        return {
            "xp": int(row["xp"] or 0), "denarios": int(row["denarios"] or 0),
            "almas": int(row["almas"] or 0), "pity": int(row["pity"] or 0),
            "cartas": int(row["cartas"] or 0), "deck": int(row["deck"] or 0),
        }

    async def coliseu_listar_colecao(self, user_id: int):
        return await self._all(
            """SELECT card_id,quantidade,source,game_name,obtained_at FROM cartas_colecao
               WHERE user_id=? ORDER BY obtained_at,card_id""",
            (int(user_id),),
        )

    # ---------- Ateliê de artes do Coliseu ----------
    async def coliseu_atelie_criar_sessao(self, user_id: int, guild_id: int, card_id: str, game_name: str = ""):
        """Abre uma sessão de upload por DM, válida por 30 minutos."""
        async with self.transaction() as tx:
            owned = await tx._one(
                "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (int(user_id), str(card_id)),
            )
            if not owned:
                return {"status": "not_owned"}
            pending = await tx._one(
                """SELECT id FROM cartas_atelie_artes
                   WHERE user_id=? AND card_id=? AND status IN ('uploading','pending') LIMIT 1""",
                (int(user_id), str(card_id)),
            )
            if pending:
                return {"status": "pending", "art_id": int(pending["id"])}
            total_pending = await tx._one(
                """SELECT COUNT(*) AS total FROM cartas_atelie_artes
                   WHERE user_id=? AND status IN ('uploading','pending')""",
                (int(user_id),),
            )
            if int(total_pending["total"] or 0) >= 3:
                return {"status": "pending_limit"}
            await tx.conn.execute(
                """INSERT INTO cartas_atelie_sessoes(user_id,guild_id,card_id,game_name,status,expires_at)
                   VALUES (?,?,?,?, 'awaiting_upload', datetime('now','+30 minutes'))
                   ON CONFLICT(user_id) DO UPDATE SET guild_id=excluded.guild_id,
                     card_id=excluded.card_id,game_name=excluded.game_name,status='awaiting_upload',
                     expires_at=excluded.expires_at,created_at=CURRENT_TIMESTAMP""",
                (int(user_id), int(guild_id), str(card_id), str(game_name or "")),
            )
            return {"status": "ok"}

    async def coliseu_atelie_obter_sessao(self, user_id: int):
        row = await self._one(
            """SELECT * FROM cartas_atelie_sessoes WHERE user_id=? AND status='awaiting_upload'
               AND expires_at>CURRENT_TIMESTAMP""",
            (int(user_id),),
        )
        return row

    async def coliseu_atelie_reservar_sessao(self, user_id: int):
        """Reserva o upload para impedir que duas DMs criem pedidos duplicados."""
        async with self.transaction() as tx:
            row = await tx._one(
                """SELECT * FROM cartas_atelie_sessoes WHERE user_id=? AND status='awaiting_upload'
                   AND expires_at>CURRENT_TIMESTAMP""",
                (int(user_id),),
            )
            if not row:
                return None
            await tx.conn.execute(
                "UPDATE cartas_atelie_sessoes SET status='processing' WHERE user_id=? AND status='awaiting_upload'",
                (int(user_id),),
            )
            return dict(row)

    async def coliseu_atelie_reabrir_sessao(self, user_id: int):
        await self.conn.execute(
            "UPDATE cartas_atelie_sessoes SET status='awaiting_upload' WHERE user_id=? AND expires_at>CURRENT_TIMESTAMP",
            (int(user_id),),
        )
        await self.conn.commit()

    async def coliseu_atelie_encerrar_sessao(self, user_id: int):
        await self.conn.execute("DELETE FROM cartas_atelie_sessoes WHERE user_id=?", (int(user_id),))
        await self.conn.commit()

    async def coliseu_atelie_criar_pedido(self, user_id: int, guild_id: int, card_id: str, game_name: str = ""):
        async with self.transaction() as tx:
            owned = await tx._one(
                "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (int(user_id), str(card_id)),
            )
            if not owned:
                return {"status": "not_owned"}
            pending = await tx._one(
                """SELECT id FROM cartas_atelie_artes
                   WHERE user_id=? AND card_id=? AND status IN ('uploading','pending') LIMIT 1""",
                (int(user_id), str(card_id)),
            )
            if pending:
                return {"status": "pending", "art_id": int(pending["id"])}
            total_pending = await tx._one(
                """SELECT COUNT(*) AS total FROM cartas_atelie_artes
                   WHERE user_id=? AND status IN ('uploading','pending')""",
                (int(user_id),),
            )
            if int(total_pending["total"] or 0) >= 3:
                return {"status": "pending_limit"}
            cur = await tx.conn.execute(
                """INSERT INTO cartas_atelie_artes(user_id,guild_id,card_id,game_name,status)
                   VALUES (?,?,?,?,'uploading')""",
                (int(user_id), int(guild_id), str(card_id), str(game_name or "")),
            )
            return {"status": "ok", "art_id": int(cur.lastrowid)}

    async def coliseu_atelie_publicar_pedido(self, art_id: int, channel_id: int, message_id: int, attachment_id: int):
        cur = await self.conn.execute(
            """UPDATE cartas_atelie_artes SET channel_id=?,message_id=?,attachment_id=?,status='pending'
               WHERE id=? AND status='uploading'""",
            (int(channel_id), int(message_id), int(attachment_id), int(art_id)),
        )
        await self.conn.commit()
        return cur.rowcount == 1

    async def coliseu_atelie_cancelar_pedido(self, art_id: int):
        await self.conn.execute(
            "UPDATE cartas_atelie_artes SET status='failed' WHERE id=? AND status='uploading'",
            (int(art_id),),
        )
        await self.conn.commit()

    async def coliseu_atelie_obter_pedido(self, art_id: int):
        return await self._one("SELECT * FROM cartas_atelie_artes WHERE id=?", (int(art_id),))

    async def coliseu_atelie_decidir_pedido(self, art_id: int, reviewer_id: int, aprovado: bool, motivo: str = ""):
        """Aprova uma arte e arquiva a anterior; nunca altera atributos da carta."""
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT * FROM cartas_atelie_artes WHERE id=? AND status='pending'",
                (int(art_id),),
            )
            if not row:
                return {"status": "processed"}
            novo_status = "approved" if aprovado else "rejected"
            if aprovado:
                await tx.conn.execute(
                    """UPDATE cartas_atelie_artes SET status='archived'
                       WHERE user_id=? AND card_id=? AND status='approved'""",
                    (int(row["user_id"]), str(row["card_id"])),
                )
            await tx.conn.execute(
                """UPDATE cartas_atelie_artes SET status=?,reviewed_by=?,rejection_reason=?,
                   reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'""",
                (novo_status, int(reviewer_id), str(motivo or "")[:500], int(art_id)),
            )
            return {"status": "ok", "pedido": dict(row), "new_status": novo_status}

    async def coliseu_atelie_arte_ativa(self, user_id: int, card_id: str):
        return await self._one(
            """SELECT * FROM cartas_atelie_artes WHERE user_id=? AND card_id=? AND status='approved'
               ORDER BY reviewed_at DESC,id DESC LIMIT 1""",
            (int(user_id), str(card_id)),
        )

    async def coliseu_atelie_remover_arte_ativa(self, user_id: int, card_id: str):
        """Volta à arte-base sem apagar o histórico de aprovações anteriores."""
        async with self.transaction() as tx:
            cur = await tx.conn.execute(
                """UPDATE cartas_atelie_artes SET status='archived'
                   WHERE user_id=? AND card_id=? AND status='approved'""",
                (int(user_id), str(card_id)),
            )
            return cur.rowcount > 0

    @staticmethod
    def _coliseu_semana_atual() -> str:
        """Semana ISO no fuso do servidor/comunidade (São Paulo)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%G-W%V")

    async def _coliseu_registrar_participacoes_tx(self, tx, duel, winner_id: int | None):
        """Credita XP de participação e missões semanais sem duplicar recompensas."""
        week_key = self._coliseu_semana_atual()
        participants = (
            (int(duel["creator_id"]), int(duel["opponent_id"])),
            (int(duel["opponent_id"]), int(duel["creator_id"])),
        )
        rewards = {uid: {"xp": 0, "almas": 0} for uid, _ in participants}

        for user_id, opponent_id in participants:
            recent_xp = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_duelo_participacoes
                   WHERE user_id=? AND xp_awarded>0 AND created_at>=datetime('now','-1 day')""",
                (user_id,),
            )
            xp_awarded = 8 if int(recent_xp["n"] or 0) < 3 else 0
            xp_row = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
            xp_before = int(xp_row["xp"] or 0) if xp_row else 0
            cur = await tx.conn.execute(
                """INSERT OR IGNORE INTO cartas_duelo_participacoes
                   (duel_id,user_id,opponent_id,won,xp_awarded,week_key)
                   VALUES (?,?,?,?,?,?)""",
                (int(duel["id"]), user_id, opponent_id, int(winner_id == user_id), xp_awarded, week_key),
            )
            if cur.rowcount == 1 and xp_awarded:
                await tx.conn.execute("UPDATE users SET xp=xp+? WHERE user_id=?", (xp_awarded, user_id))
                rewards[user_id]["xp"] = xp_awarded
                rewards[user_id]["old_level"] = nivel_por_xp(xp_before)
                rewards[user_id]["new_level"] = nivel_por_xp(xp_before + xp_awarded)

        missoes = (
            ("primeiro_duelo", "Primeiro combate", 1, "duelos", 2),
            ("tres_duelos", "Presença na arena", 3, "duelos", 4),
            ("duas_vitorias", "Duas vitórias", 2, "vitorias", 6),
        )
        for user_id, _ in participants:
            stats = await tx._one(
                """SELECT COUNT(*) AS duelos, COALESCE(SUM(won),0) AS vitorias
                   FROM cartas_duelo_participacoes WHERE user_id=? AND week_key=?""",
                (user_id, week_key),
            )
            valores = {"duelos": int(stats["duelos"] or 0), "vitorias": int(stats["vitorias"] or 0)}
            for code, _titulo, goal, metric, reward_almas in missoes:
                if valores[metric] < goal:
                    continue
                cur = await tx.conn.execute(
                    """INSERT OR IGNORE INTO cartas_missoes_recompensas
                       (user_id,week_key,mission_code,reward_almas,trigger_duel_id)
                       VALUES (?,?,?,?,?)""",
                    (user_id, week_key, code, reward_almas, int(duel["id"])),
                )
                if cur.rowcount != 1:
                    continue
                await tx.conn.execute("INSERT OR IGNORE INTO cartas_almas(user_id) VALUES (?)", (user_id,))
                await tx.conn.execute(
                    "UPDATE cartas_almas SET quantidade=quantidade+?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                    (reward_almas, user_id),
                )
                await tx.conn.execute(
                    """INSERT OR IGNORE INTO cartas_transacoes
                       (tx_key,user_id,kind,almas_delta,duel_id,details_json)
                       VALUES (?,?, 'missao_semanal', ?, ?, ?)""",
                    (f"mission:{week_key}:{code}:{user_id}", user_id, reward_almas, int(duel["id"]),
                     f'{{"mission":"{code}","week":"{week_key}"}}'),
                )
                rewards[user_id]["almas"] += reward_almas
        return rewards

    async def coliseu_missoes_semanais(self, user_id: int):
        week_key = self._coliseu_semana_atual()
        stats = await self._one(
            """SELECT COUNT(*) AS duelos, COALESCE(SUM(won),0) AS vitorias
               FROM cartas_duelo_participacoes WHERE user_id=? AND week_key=?""",
            (int(user_id), week_key),
        )
        claims = await self._all(
            "SELECT mission_code,reward_almas FROM cartas_missoes_recompensas WHERE user_id=? AND week_key=?",
            (int(user_id), week_key),
        )
        claimed = {str(row["mission_code"]): int(row["reward_almas"] or 0) for row in claims}
        valores = {"duelos": int(stats["duelos"] or 0), "vitorias": int(stats["vitorias"] or 0)}
        definicoes = (
            ("primeiro_duelo", "Primeiro combate", "Conclua seu primeiro duelo nesta semana.", 1, "duelos", 2),
            ("tres_duelos", "Presença na arena", "Conclua três duelos nesta semana.", 3, "duelos", 4),
            ("duas_vitorias", "Duas vitórias", "Vença dois duelos nesta semana.", 2, "vitorias", 6),
        )
        return {
            "week_key": week_key,
            "missions": [
                {
                    "code": code, "title": title, "description": description,
                    "progress": min(valores[metric], goal), "goal": goal,
                    "reward_almas": reward, "claimed": code in claimed,
                }
                for code, title, description, goal, metric, reward in definicoes
            ],
        }

    async def coliseu_rivalidade(self, user_id: int, opponent_id: int, limite: int = 5):
        where = "((creator_id=? AND opponent_id=?) OR (creator_id=? AND opponent_id=?))"
        args = (int(user_id), int(opponent_id), int(opponent_id), int(user_id))
        stats = await self._one(
            f"""SELECT COUNT(*) AS duelos,
                       SUM(CASE WHEN winner_id=? THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN winner_id=? THEN 1 ELSE 0 END) AS losses,
                       SUM(CASE WHEN winner_id IS NULL THEN 1 ELSE 0 END) AS draws
                FROM cartas_duelos WHERE status='finished' AND {where}""",
            (int(user_id), int(opponent_id), *args),
        )
        recent = await self._all(
            f"""SELECT id,creator_id,opponent_id,winner_id,aposta,created_at
                FROM cartas_duelos WHERE status='finished' AND {where}
                ORDER BY id DESC LIMIT ?""",
            (*args, max(1, min(int(limite), 10))),
        )
        return {
            "duels": int(stats["duelos"] or 0),
            "wins": int(stats["wins"] or 0),
            "losses": int(stats["losses"] or 0),
            "draws": int(stats["draws"] or 0),
            "recent": [dict(row) for row in recent],
        }

    async def coliseu_recompensas_duelo(self, duel_id: int):
        return await self._all(
            """SELECT p.user_id,p.opponent_id,p.won,p.xp_awarded,
                      COALESCE(SUM(m.reward_almas),0) AS almas_awarded
               FROM cartas_duelo_participacoes p
               LEFT JOIN cartas_missoes_recompensas m
                 ON m.trigger_duel_id=p.duel_id AND m.user_id=p.user_id
               WHERE p.duel_id=? GROUP BY p.user_id,p.opponent_id,p.won,p.xp_awarded
               ORDER BY p.user_id""",
            (int(duel_id),),
        )

    async def coliseu_abrir_pacote(self, user_id: int, catalogo_por_raridade: dict,
                                   almas_por_raridade: dict, preco: int = 120, quantidade: int = 3,
                                   limite_pacotes_dia: int = 3):
        """Compra e abre pacote na mesma transação; sorteio, pity e duplicatas são atômicos."""
        import secrets
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            await tx.conn.execute("INSERT OR IGNORE INTO cartas_almas(user_id) VALUES (?)", (int(user_id),))
            await tx.conn.execute("INSERT OR IGNORE INTO cartas_pity(user_id) VALUES (?)", (int(user_id),))
            user = await tx._one("SELECT denarios FROM users WHERE user_id=?", (int(user_id),))
            abertos = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_transacoes
                   WHERE user_id=? AND kind='pacote_fogueira' AND created_at>=datetime('now','-1 day')""",
                (int(user_id),),
            )
            pacotes_24h = int(abertos["n"] or 0)
            if pacotes_24h >= int(limite_pacotes_dia):
                return {"status": "limite_pacotes_dia", "limite": int(limite_pacotes_dia), "abertos": pacotes_24h}
            if int(user["denarios"] or 0) < int(preco):
                return {"status": "sem_saldo", "saldo": int(user["denarios"] or 0)}
            pity_row = await tx._one("SELECT comuns_seguidas FROM cartas_pity WHERE user_id=?", (int(user_id),))
            streak = int(pity_row["comuns_seguidas"] or 0)
            aberturas = []
            almas_ganhas = 0
            for _ in range(int(quantidade)):
                # Cada uma das cinco Primordiais só pode existir uma vez em todo o servidor.
                primordiais_disponiveis = [
                    c for c in (catalogo_por_raridade.get("Primordial") or [])
                    if not await tx._one("SELECT 1 FROM cartas_primordiais_resgatadas WHERE card_id=?", (str(c["id"]),))
                ]
                rolagem_primordial = secrets.randbelow(1000)
                primordial = bool(primordiais_disponiveis) and rolagem_primordial == 0
                pity_ativado = streak >= 10
                if primordial:
                    carta = dict(secrets.choice(primordiais_disponiveis))
                    try:
                        await tx.conn.execute(
                            "INSERT INTO cartas_primordiais_resgatadas(card_id,user_id) VALUES (?,?)",
                            (str(carta["id"]), int(user_id)),
                        )
                    except Exception:
                        # Uma colisão concorrente nunca concede cópia nem cobra o pacote.
                        raise
                    await tx.conn.execute(
                        "INSERT INTO cartas_colecao(user_id,card_id,quantidade,source) VALUES (?,?,1,'primordial')",
                        (int(user_id), str(carta["id"])),
                    )
                    aberturas.append({"carta": carta, "duplicata": False, "almas": 0,
                                      "pity_ativado": False, "primordial": True})
                    continue
                if pity_ativado:
                    raridade = secrets.choice(["Rara"] * 22 + ["Épica"] * 7 + ["Lendária"])
                else:
                    # A chance de 0,1% reservada às Primordiais migra para Lendária
                    # quando as cinco únicas já foram resgatadas.
                    rolagem = rolagem_primordial
                    if primordiais_disponiveis:
                        if rolagem < 700:
                            raridade = "Comum"
                        elif rolagem < 920:
                            raridade = "Rara"
                        elif rolagem < 990:
                            raridade = "Épica"
                        else:
                            raridade = "Lendária"
                    else:
                        if rolagem < 699:
                            raridade = "Comum"
                        elif rolagem < 919:
                            raridade = "Rara"
                        elif rolagem < 989:
                            raridade = "Épica"
                        else:
                            raridade = "Lendária"
                candidatos = catalogo_por_raridade.get(raridade) or catalogo_por_raridade.get("Comum") or []
                if not candidatos:
                    return {"status": "catalogo_invalido"}
                carta = dict(secrets.choice(candidatos))
                existente = await tx._one(
                    "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                    (int(user_id), str(carta["id"])),
                )
                if existente:
                    almas = int(almas_por_raridade.get(raridade, 0))
                    almas_ganhas += almas
                    duplicata = True
                else:
                    await tx.conn.execute(
                        """INSERT INTO cartas_colecao(user_id,card_id,quantidade,source)
                           VALUES (?,?,1,'pacote')""",
                        (int(user_id), str(carta["id"])),
                    )
                    almas = 0
                    duplicata = False
                if raridade == "Comum" and not pity_ativado:
                    streak += 1
                else:
                    streak = 0
                aberturas.append({"carta": carta, "duplicata": duplicata, "almas": almas,
                                  "pity_ativado": pity_ativado, "primordial": False})
            cur = await tx.conn.execute(
                "UPDATE users SET denarios=denarios-? WHERE user_id=? AND denarios>=?",
                (int(preco), int(user_id), int(preco)),
            )
            if cur.rowcount != 1:
                return {"status": "sem_saldo"}
            if almas_ganhas:
                await tx.conn.execute(
                    "UPDATE cartas_almas SET quantidade=quantidade+?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                    (almas_ganhas, int(user_id)),
                )
            await tx.conn.execute(
                "UPDATE cartas_pity SET comuns_seguidas=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (streak, int(user_id)),
            )
            import json, uuid
            await tx.conn.execute(
                """INSERT INTO cartas_transacoes(tx_key,user_id,kind,denarios_delta,almas_delta,details_json)
                   VALUES (?,?,?,?,?,?)""",
                (f"pack:{uuid.uuid4().hex}", int(user_id), "pacote_fogueira", -int(preco), int(almas_ganhas),
                 json.dumps({"cards": [x["carta"]["id"] for x in aberturas]}, ensure_ascii=False)),
            )
            saldo = await tx._one("SELECT denarios FROM users WHERE user_id=?", (int(user_id),))
            return {"status": "ok", "cards": aberturas, "almas_ganhas": almas_ganhas,
                    "pity": streak, "saldo": int(saldo["denarios"] or 0),
                    "pacotes_restantes": max(0, int(limite_pacotes_dia) - pacotes_24h - 1)}

    async def coliseu_forjar_carta(self, user_id: int, carta: dict, custo_almas: int):
        import json, uuid
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            await tx.conn.execute("INSERT OR IGNORE INTO cartas_almas(user_id) VALUES (?)", (int(user_id),))
            existente = await tx._one(
                "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (int(user_id), str(carta["id"])),
            )
            if existente:
                return "ja_tem"
            saldo = await tx._one("SELECT quantidade FROM cartas_almas WHERE user_id=?", (int(user_id),))
            if int(saldo["quantidade"] or 0) < int(custo_almas):
                return "sem_almas"
            await tx.conn.execute(
                "UPDATE cartas_almas SET quantidade=quantidade-?,updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND quantidade>=?",
                (int(custo_almas), int(user_id), int(custo_almas)),
            )
            await tx.conn.execute(
                "INSERT INTO cartas_colecao(user_id,card_id,quantidade,source) VALUES (?,?,1,'forja')",
                (int(user_id), str(carta["id"])),
            )
            await tx.conn.execute(
                """INSERT INTO cartas_transacoes(tx_key,user_id,kind,almas_delta,details_json)
                   VALUES (?,?, 'forja', ?, ?)""",
                (f"craft:{uuid.uuid4().hex}", int(user_id), -int(custo_almas),
                 json.dumps({"card_id": carta["id"]}, ensure_ascii=False)),
            )
            return "ok"

    async def coliseu_salvar_deck(self, user_id: int, card_snapshots: list[dict]):
        """Salva somente atributos canônicos de cartas que o jogador realmente possui."""
        import json
        from sistemas.cartas import cards_em_deck_validos, get_carta, carta_de_jogo_por_id
        async with self.transaction() as tx:
            rows = await tx._all(
                "SELECT card_id,game_name FROM cartas_colecao WHERE user_id=?", (int(user_id),)
            )
            owned = {str(r["card_id"]): str(r["game_name"] or "") for r in rows}
            cards = []
            for submitted in card_snapshots:
                card_id = str(submitted.get("id", ""))
                if card_id not in owned:
                    return {"status": "nao_possui"}
                canonical = get_carta(card_id)
                if canonical is None and card_id.startswith("jogo_") and owned[card_id]:
                    try:
                        canonical = carta_de_jogo_por_id(card_id, owned[card_id])
                    except ValueError:
                        canonical = None
                if canonical is None:
                    return {"status": "carta_indisponivel", "card_id": card_id}
                cards.append(canonical.para_dict())
            valido, motivo = cards_em_deck_validos(cards)
            if not valido:
                return {"status": "invalido", "motivo": motivo}
            await tx.conn.execute("INSERT OR IGNORE INTO cartas_decks(user_id) VALUES (?)", (int(user_id),))
            await tx.conn.execute("DELETE FROM cartas_deck_itens WHERE user_id=?", (int(user_id),))
            for slot, carta in enumerate(cards, 1):
                await tx.conn.execute(
                    "INSERT INTO cartas_deck_itens(user_id,slot,card_id,snapshot_json) VALUES (?,?,?,?)",
                    (int(user_id), slot, str(carta["id"]), json.dumps(carta, ensure_ascii=False)),
                )
            await tx.conn.execute("UPDATE cartas_decks SET updated_at=CURRENT_TIMESTAMP WHERE user_id=?", (int(user_id),))
            return {"status": "ok", "custo": sum(int(c["custo"]) for c in cards)}

    async def coliseu_obter_deck(self, user_id: int):
        """Carrega o deck e migra apenas o ID da habilidade para o catálogo atual."""
        import json
        from sistemas.cartas import carta_dict

        rows = await self._all(
            "SELECT slot,snapshot_json FROM cartas_deck_itens WHERE user_id=? ORDER BY slot",
            (int(user_id),),
        )
        result = []
        atualizacoes = []
        for row in rows:
            try:
                carta = json.loads(row["snapshot_json"])
            except (TypeError, ValueError):
                continue
            canonica = carta_dict(str(carta.get("id", "")), str(carta.get("jogo_origem", "")))
            # Não alteramos poder, custo, tipo ou raridade de cartas já salvas; somente
            # sincronizamos a habilidade para que decks antigos recebam o novo catálogo.
            if canonica and carta.get("habilidade") != canonica.get("habilidade"):
                carta["habilidade"] = canonica["habilidade"]
                atualizacoes.append((json.dumps(carta, ensure_ascii=False), int(row["slot"])))
            result.append(carta)
        for snapshot, slot in atualizacoes:
            await self.conn.execute(
                "UPDATE cartas_deck_itens SET snapshot_json=? WHERE user_id=? AND slot=?",
                (snapshot, int(user_id), int(slot)),
            )
        if atualizacoes:
            await self.conn.commit()
        return result

    async def coliseu_criar_convite(self, guild_id: int, channel_id: int, creator_id: int,
                                    opponent_id: int, aposta: int, *, nivel_minimo: int = 5,
                                    limite_diario: int = 5, limite_par: int = 2,
                                    max_aposta_dia: int = 1500, cooldown_segundos: int = 60,
                                    diferenca_maxima_poder: int = 4):
        import json
        aposta = int(aposta)
        # Defesa em profundidade: não confiar somente na validação do modal do Discord.
        if aposta < 0 or aposta > 500:
            return {"status": "aposta_invalida", "minimo": 0, "maximo": 500}
        if creator_id == opponent_id:
            return {"status": "self"}
        async with self.transaction() as tx:
            for uid in (int(creator_id), int(opponent_id)):
                await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
            users = {}
            deck_power = {}
            for uid in (int(creator_id), int(opponent_id)):
                users[uid] = await tx._one("SELECT xp,denarios FROM users WHERE user_id=?", (uid,))
                if aposta > 0 and int(users[uid]["denarios"] or 0) < aposta:
                    return {"status": "saldo", "user_id": uid}
                deck_rows = await tx._all(
                    "SELECT snapshot_json FROM cartas_deck_itens WHERE user_id=? ORDER BY slot", (uid,)
                )
                if len(deck_rows) != 5:
                    return {"status": "sem_deck", "user_id": uid}
                try:
                    deck_power[uid] = sum(int(json.loads(r["snapshot_json"]).get("poder", 0)) for r in deck_rows)
                except (TypeError, ValueError, AttributeError):
                    return {"status": "deck_invalido", "user_id": uid}
            diferenca_poder = abs(deck_power[int(creator_id)] - deck_power[int(opponent_id)])
            ativo = await tx._one(
                """SELECT id FROM cartas_duelos WHERE status IN ('invited','active')
                   AND (creator_id IN (?,?) OR opponent_id IN (?,?) OR creator_id=? OR opponent_id=?) LIMIT 1""",
                (int(creator_id), int(opponent_id), int(creator_id), int(opponent_id), int(creator_id), int(opponent_id)),
            )
            if ativo:
                return {"status": "ocupado"}
            contagem = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_duelos WHERE accepted_at>=datetime('now','-1 day')
                   AND status IN ('active','finished','cancelled') AND
                   (creator_id IN (?,?) OR opponent_id IN (?,?))""",
                (int(creator_id), int(opponent_id), int(creator_id), int(opponent_id)),
            )
            if int(contagem["n"] or 0) >= int(limite_diario):
                return {"status": "limite_diario"}
            par = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_duelos WHERE accepted_at>=datetime('now','-1 day')
                   AND status IN ('active','finished','cancelled') AND
                   ((creator_id=? AND opponent_id=?) OR (creator_id=? AND opponent_id=?))""",
                (int(creator_id), int(opponent_id), int(opponent_id), int(creator_id)),
            )
            if int(par["n"] or 0) >= int(limite_par):
                return {"status": "limite_par"}
            if int(cooldown_segundos) > 0:
                recent = await tx._one(
                    """SELECT COUNT(*) AS n FROM cartas_duelos WHERE created_at>=datetime('now',?)
                       AND (creator_id IN (?,?) OR opponent_id IN (?,?))
                       AND status IN ('invited','active','finished','cancelled')""",
                    (f"-{int(cooldown_segundos)} seconds", int(creator_id), int(opponent_id), int(creator_id), int(opponent_id)),
                )
                if int(recent["n"] or 0):
                    return {"status": "cooldown"}
            for uid in (int(creator_id), int(opponent_id)):
                aposta_dia = await tx._one(
                    """SELECT COALESCE(SUM(aposta),0) AS n FROM cartas_duelos WHERE accepted_at>=datetime('now','-1 day')
                       AND status IN ('active','finished','cancelled') AND (creator_id=? OR opponent_id=?)""",
                    (uid, uid),
                )
                if int(aposta_dia["n"] or 0) + aposta > int(max_aposta_dia):
                    return {"status": "limite_aposta_dia", "user_id": uid}
            cur = await tx.conn.execute(
                """INSERT INTO cartas_duelos(guild_id,channel_id,creator_id,opponent_id,aposta,status,expires_at)
                   VALUES (?,?,?,?,?,'invited',datetime('now','+2 minutes'))""",
                (int(guild_id), int(channel_id), int(creator_id), int(opponent_id), aposta),
            )
            return {"status": "ok", "duel_id": int(cur.lastrowid), "expires_seconds": 120,
                    "deck_power": deck_power, "power_gap": diferenca_poder}

    async def coliseu_definir_mensagem_convite(self, duel_id: int, message_id: int):
        await self.conn.execute("UPDATE cartas_duelos SET message_id=? WHERE id=? AND status='invited'",
                                (int(message_id), int(duel_id)))
        await self.conn.commit()

    async def coliseu_decidir_convite(self, duel_id: int, user_id: int, aceitar: bool,
                                     *, diferenca_maxima_poder: int = 4):
        async with self.transaction() as tx:
            row = await tx._one("SELECT * FROM cartas_duelos WHERE id=?", (int(duel_id),))
            if row is None or row["status"] != "invited":
                return {"status": "indisponivel"}
            if int(row["opponent_id"]) != int(user_id) and not (not aceitar and int(row["creator_id"]) == int(user_id)):
                return {"status": "nao_autorizado"}
            if not aceitar:
                cur = await tx.conn.execute(
                    "UPDATE cartas_duelos SET status='cancelled',end_reason='convite recusado/cancelado' WHERE id=? AND status='invited'",
                    (int(duel_id),),
                )
                return {"status": "cancelled" if cur.rowcount == 1 else "indisponivel"}
            exp = await tx._one("SELECT expires_at<=CURRENT_TIMESTAMP AS expired FROM cartas_duelos WHERE id=?", (int(duel_id),))
            if exp and int(exp["expired"] or 0):
                await tx.conn.execute("UPDATE cartas_duelos SET status='expired',end_reason='convite expirado' WHERE id=?", (int(duel_id),))
                return {"status": "expired"}
            creator_id, opponent_id, aposta = int(row["creator_id"]), int(row["opponent_id"]), int(row["aposta"])
            decks = {}
            deck_power = {}
            import json
            for uid in (creator_id, opponent_id):
                deck_rows = await tx._all(
                    "SELECT slot,card_id,snapshot_json FROM cartas_deck_itens WHERE user_id=? ORDER BY slot", (uid,)
                )
                if len(deck_rows) != 5:
                    return {"status": "sem_deck", "user_id": uid}
                decks[uid] = deck_rows
                try:
                    deck_power[uid] = sum(int(json.loads(r["snapshot_json"]).get("poder", 0)) for r in deck_rows)
                except (TypeError, ValueError, AttributeError):
                    return {"status": "deck_invalido", "user_id": uid}
            if aposta > 0:
                for uid in (creator_id, opponent_id):
                    user_row = await tx._one("SELECT denarios FROM users WHERE user_id=?", (uid,))
                    if int(user_row["denarios"] or 0) < aposta:
                        return {"status": "saldo", "user_id": uid}
            # Diferença de poder é apenas informativa nesta fase.
            diferenca_poder = abs(deck_power[creator_id] - deck_power[opponent_id])
            # Revalida limite de duelos antes de travar as duas apostas.
            hoje = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_duelos WHERE accepted_at>=datetime('now','-1 day')
                   AND status IN ('active','finished','cancelled') AND
                   (creator_id IN (?,?) OR opponent_id IN (?,?))""",
                (creator_id, opponent_id, creator_id, opponent_id),
            )
            if int(hoje["n"] or 0) >= 5:
                return {"status": "limite_diario"}
            par = await tx._one(
                """SELECT COUNT(*) AS n FROM cartas_duelos WHERE accepted_at>=datetime('now','-1 day')
                   AND status IN ('active','finished','cancelled')
                   AND ((creator_id=? AND opponent_id=?) OR (creator_id=? AND opponent_id=?))""",
                (creator_id, opponent_id, opponent_id, creator_id),
            )
            if int(par["n"] or 0) >= 2:
                return {"status": "limite_par"}
            for uid in (creator_id, opponent_id):
                gasto = await tx._one(
                    """SELECT COALESCE(SUM(aposta),0) AS n FROM cartas_duelos WHERE accepted_at>=datetime('now','-1 day')
                       AND status IN ('active','finished','cancelled') AND (creator_id=? OR opponent_id=?)""",
                    (uid, uid),
                )
                if int(gasto["n"] or 0) + aposta > 1500:
                    return {"status": "limite_aposta_dia", "user_id": uid}
            for uid in sorted((creator_id, opponent_id)):
                if aposta > 0:
                    cur = await tx.conn.execute(
                        "UPDATE users SET denarios=denarios-? WHERE user_id=? AND denarios>=?",
                        (aposta, uid, aposta),
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError("Saldo mudou durante a aceitação do duelo.")
                    await tx.conn.execute(
                        """INSERT INTO cartas_transacoes(tx_key,user_id,kind,denarios_delta,duel_id)
                           VALUES (?,?, 'aposta_travada', ?, ?)""",
                        (f"duel:{duel_id}:stake:{uid}", uid, -aposta, int(duel_id)),
                    )
                for deck_row in decks[uid]:
                    await tx.conn.execute(
                        """INSERT INTO cartas_duelo_deck(duel_id,user_id,slot,card_id,snapshot_json)
                           VALUES (?,?,?,?,?)""",
                        (int(duel_id), uid, int(deck_row["slot"]), str(deck_row["card_id"]), str(deck_row["snapshot_json"])),
                    )
            cur = await tx.conn.execute(
                """UPDATE cartas_duelos SET status='active',accepted_at=CURRENT_TIMESTAMP,
                       round_deadline=datetime('now','+30 seconds'),current_round=1
                   WHERE id=? AND status='invited'""",
                (int(duel_id),),
            )
            if cur.rowcount != 1:
                raise RuntimeError("O convite mudou durante a aceitação.")
            atualizado = await tx._one("SELECT * FROM cartas_duelos WHERE id=?", (int(duel_id),))
            return {"status": "ok", "duel": dict(atualizado),
                    "deck_power": deck_power, "power_gap": diferenca_poder}

    async def coliseu_obter_duelo(self, duel_id: int):
        row = await self._one("SELECT * FROM cartas_duelos WHERE id=?", (int(duel_id),))
        return dict(row) if row else None

    async def coliseu_listar_duelos_usuario(self, user_id: int, limite: int = 25):
        """Lista cada confronto individual do membro, inclusive convites e partidas canceladas."""
        return await self._all(
            """SELECT * FROM cartas_duelos
               WHERE creator_id=? OR opponent_id=?
               ORDER BY id DESC LIMIT ?""",
            (int(user_id), int(user_id), max(1, min(int(limite), 100))),
        )

    async def coliseu_estatisticas_duelos_usuario(self, user_id: int):
        """Retorna o histórico agregado sem misturar convites ou partidas canceladas."""
        uid = int(user_id)
        row = await self._one(
            """SELECT
                 COUNT(*) AS partidas,
                 SUM(CASE WHEN winner_id=? THEN 1 ELSE 0 END) AS vitorias,
                 SUM(CASE WHEN winner_id IS NOT NULL AND winner_id<>? THEN 1 ELSE 0 END) AS derrotas,
                 SUM(CASE WHEN winner_id IS NULL THEN 1 ELSE 0 END) AS empates,
                 SUM(CASE WHEN winner_id=? THEN payout-aposta
                          WHEN winner_id IS NOT NULL THEN -aposta ELSE 0 END) AS saldo_liquido
               FROM cartas_duelos
               WHERE status='finished' AND (creator_id=? OR opponent_id=?)""",
            (uid, uid, uid, uid, uid),
        )
        return {
            "partidas": int(row["partidas"] or 0),
            "vitorias": int(row["vitorias"] or 0),
            "derrotas": int(row["derrotas"] or 0),
            "empates": int(row["empates"] or 0),
            "saldo_liquido": int(row["saldo_liquido"] or 0),
        }

    async def coliseu_contagem_jogadas_rodada(self, duel_id: int):
        """Conta apenas quantas escolhas secretas chegaram, sem revelar os autores."""
        row = await self._one(
            """SELECT d.current_round, COUNT(j.user_id) AS escolhas
               FROM cartas_duelos d
               LEFT JOIN cartas_duelo_jogadas j
                 ON j.duel_id=d.id AND j.round_no=d.current_round
               WHERE d.id=? GROUP BY d.id""",
            (int(duel_id),),
        )
        return int(row["escolhas"] or 0) if row else 0

    async def coliseu_duelos_publicados(self, statuses: tuple[str, ...] = ("invited", "active")):
        marks = ",".join("?" for _ in statuses)
        return await self._all(f"SELECT * FROM cartas_duelos WHERE status IN ({marks}) AND message_id IS NOT NULL", statuses)

    async def coliseu_deck_da_partida(self, duel_id: int, user_id: int):
        import json
        rows = await self._all(
            "SELECT snapshot_json FROM cartas_duelo_deck WHERE duel_id=? AND user_id=? ORDER BY slot",
            (int(duel_id), int(user_id)),
        )
        cards = []
        for row in rows:
            try:
                cards.append(json.loads(row["snapshot_json"]))
            except (TypeError, ValueError):
                continue
        return cards

    async def coliseu_cartas_disponiveis(self, duel_id: int, user_id: int):
        import json
        rows = await self._all(
            """SELECT d.snapshot_json FROM cartas_duelo_deck d
               WHERE d.duel_id=? AND d.user_id=? AND NOT EXISTS (
                 SELECT 1 FROM cartas_duelo_jogadas j WHERE j.duel_id=d.duel_id
                   AND j.user_id=d.user_id AND j.card_id=d.card_id)
               ORDER BY d.slot""",
            (int(duel_id), int(user_id)),
        )
        out = []
        for row in rows:
            try:
                out.append(json.loads(row["snapshot_json"]))
            except (TypeError, ValueError):
                continue
        return out

    async def coliseu_registrar_jogada(self, duel_id: int, user_id: int, card_id: str):
        import json
        async with self.transaction() as tx:
            duel = await tx._one("SELECT * FROM cartas_duelos WHERE id=? AND status='active'", (int(duel_id),))
            if duel is None:
                return {"status": "inativo"}
            participantes = (int(duel["creator_id"]), int(duel["opponent_id"]))
            if int(user_id) not in participantes:
                return {"status": "nao_autorizado"}
            prazo = await tx._one(
                "SELECT round_deadline IS NOT NULL AND round_deadline<=CURRENT_TIMESTAMP AS expirado FROM cartas_duelos WHERE id=?",
                (int(duel_id),),
            )
            if prazo and int(prazo["expirado"] or 0):
                return {"status": "expirado"}
            existente = await tx._one(
                "SELECT 1 FROM cartas_duelo_jogadas WHERE duel_id=? AND round_no=? AND user_id=?",
                (int(duel_id), int(duel["current_round"]), int(user_id)),
            )
            if existente:
                return {"status": "ja_escolheu"}
            snapshot = await tx._one(
                "SELECT snapshot_json FROM cartas_duelo_deck WHERE duel_id=? AND user_id=? AND card_id=?",
                (int(duel_id), int(user_id), str(card_id)),
            )
            if snapshot is None:
                return {"status": "carta_invalida"}
            used = await tx._one(
                "SELECT 1 FROM cartas_duelo_jogadas WHERE duel_id=? AND user_id=? AND card_id=?",
                (int(duel_id), int(user_id), str(card_id)),
            )
            if used:
                return {"status": "carta_usada"}
            await tx.conn.execute(
                "INSERT INTO cartas_duelo_jogadas(duel_id,round_no,user_id,card_id) VALUES (?,?,?,?)",
                (int(duel_id), int(duel["current_round"]), int(user_id), str(card_id)),
            )
            plays = await tx._all(
                """SELECT j.user_id,j.card_id,d.snapshot_json FROM cartas_duelo_jogadas j
                   JOIN cartas_duelo_deck d ON d.duel_id=j.duel_id AND d.user_id=j.user_id AND d.card_id=j.card_id
                   WHERE j.duel_id=? AND j.round_no=? ORDER BY j.user_id""",
                (int(duel_id), int(duel["current_round"])),
            )
            if len(plays) < 2:
                return {"status": "aguardando", "round_no": int(duel["current_round"])}
            dados = {}
            for play in plays:
                try:
                    dados[int(play["user_id"])] = json.loads(play["snapshot_json"])
                except (TypeError, ValueError):
                    return {"status": "snapshot_invalido"}
            return {"status": "pronto", "duel": dict(duel), "cards": dados,
                    "round_no": int(duel["current_round"])}

    async def coliseu_resolver_rodada(self, duel_id: int, round_no: int, result: dict):
        import uuid
        async with self.transaction() as tx:
            duel = await tx._one("SELECT * FROM cartas_duelos WHERE id=? AND status='active'", (int(duel_id),))
            if duel is None or int(duel["current_round"]) != int(round_no):
                return {"status": "ja_resolvida"}
            a, b = int(duel["creator_id"]), int(duel["opponent_id"])
            plays = await tx._all(
                "SELECT user_id,card_id FROM cartas_duelo_jogadas WHERE duel_id=? AND round_no=?",
                (int(duel_id), int(round_no)),
            )
            by_user = {int(r["user_id"]): str(r["card_id"]) for r in plays}
            if a not in by_user or b not in by_user:
                return {"status": "aguardando"}
            ca, cb = result["card_a"], result["card_b"]
            if by_user[a] != str(ca["id"]) or by_user[b] != str(cb["id"]):
                return {"status": "snapshot_mismatch"}
            await tx.conn.execute(
                """UPDATE cartas_duelo_jogadas SET power_final=?,type_bonus=?,skill_bonus=?
                   WHERE duel_id=? AND round_no=? AND user_id=?""",
                (int(result["power_a"]), int(result["type_bonus_a"]), int(result["skill_bonus_a"]), int(duel_id), int(round_no), a),
            )
            await tx.conn.execute(
                """UPDATE cartas_duelo_jogadas SET power_final=?,type_bonus=?,skill_bonus=?
                   WHERE duel_id=? AND round_no=? AND user_id=?""",
                (int(result["power_b"]), int(result["type_bonus_b"]), int(result["skill_bonus_b"]), int(duel_id), int(round_no), b),
            )
            await tx.conn.execute(
                """INSERT INTO cartas_duelo_rounds(duel_id,round_no,card_a_id,card_b_id,card_a_name,card_b_name,
                       power_a,power_b,type_bonus_a,type_bonus_b,skill_bonus_a,skill_bonus_b,
                       combo_bonus_a,combo_bonus_b,combo_name_a,combo_name_b,skill_text_a,skill_text_b,winner_side,narration)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(duel_id), int(round_no), str(ca["id"]), str(cb["id"]), str(ca["nome"]), str(cb["nome"]),
                 int(result["power_a"]), int(result["power_b"]), int(result["type_bonus_a"]), int(result["type_bonus_b"]),
                 int(result["skill_bonus_a"]), int(result["skill_bonus_b"]),
                 int(result.get("combo_bonus_a", 0)), int(result.get("combo_bonus_b", 0)),
                 str(result.get("combo_name_a", ""))[:80], str(result.get("combo_name_b", ""))[:80],
                 str(result.get("skill_text_a", ""))[:160], str(result.get("skill_text_b", ""))[:160],
                 str(result["winner"]), str(result.get("narration", ""))[:500]),
            )
            rounds = await tx._all("SELECT winner_side,power_a,power_b FROM cartas_duelo_rounds WHERE duel_id=? ORDER BY round_no", (int(duel_id),))
            wins_a = sum(1 for r in rounds if r["winner_side"] == "a")
            wins_b = sum(1 for r in rounds if r["winner_side"] == "b")
            from sistemas.cartas import vencedor_matematicamente_garantido
            vencedor_garantido = vencedor_matematicamente_garantido(wins_a, wins_b, int(round_no), 5)
            encerrado_antecipadamente = bool(int(round_no) < 5 and vencedor_garantido)
            if int(round_no) < 5 and not encerrado_antecipadamente:
                await tx.conn.execute(
                    "UPDATE cartas_duelos SET current_round=?,round_deadline=datetime('now','+30 seconds') WHERE id=?",
                    (int(round_no) + 1, int(duel_id)),
                )
                return {"status": "round_ok", "round_no": int(round_no), "wins_a": wins_a, "wins_b": wins_b}
            total_a = sum(int(r["power_a"]) for r in rounds if r["winner_side"] == "a")
            total_b = sum(int(r["power_b"]) for r in rounds if r["winner_side"] == "b")
            lado_vencedor = "a" if wins_a > wins_b else "b" if wins_b > wins_a else "a" if total_a > total_b else "b" if total_b > total_a else "empate"
            pote = int(duel["aposta"]) * 2
            if lado_vencedor == "empate":
                for uid in (a, b):
                    await tx.conn.execute("UPDATE users SET denarios=denarios+? WHERE user_id=?", (int(duel["aposta"]), uid))
                    await tx.conn.execute(
                        """INSERT INTO cartas_transacoes(tx_key,user_id,kind,denarios_delta,duel_id)
                           VALUES (?,?, 'aposta_devolvida', ?, ?)""",
                        (f"duel:{duel_id}:draw_refund:{uid}", uid, int(duel["aposta"]), int(duel_id)),
                    )
                await tx.conn.execute("UPDATE cartas_duelos SET status='finished',winner_id=NULL,payout=0,burned=0,end_reason='empate; apostas devolvidas' WHERE id=?", (int(duel_id),))
                recompensas = await self._coliseu_registrar_participacoes_tx(tx, duel, None)
                return {"status": "empate", "wins_a": wins_a, "wins_b": wins_b, "total_a": total_a, "total_b": total_b, "pote": pote,
                        "recompensas": recompensas}
            winner_id = a if lado_vencedor == "a" else b
            payout = (pote * 90) // 100
            burned = pote - payout
            await tx.conn.execute("UPDATE users SET denarios=denarios+? WHERE user_id=?", (payout, winner_id))
            await tx.conn.execute(
                """INSERT INTO cartas_transacoes(tx_key,user_id,kind,denarios_delta,duel_id,details_json)
                   VALUES (?,?, 'premio_duelo', ?, ?, ?)""",
                (f"duel:{duel_id}:payout", winner_id, payout, int(duel_id),
                 f'{{"pot":{pote},"burned":{burned}}}'),
            )
            motivo_fim = (
                f"vitória matematicamente garantida após {int(round_no)} rodadas"
                if encerrado_antecipadamente else "duelo concluído após cinco rodadas"
            )
            await tx.conn.execute(
                "UPDATE cartas_duelos SET status='finished',winner_id=?,payout=?,burned=?,end_reason=? WHERE id=?",
                (winner_id, payout, burned, motivo_fim, int(duel_id)),
            )
            recompensas = await self._coliseu_registrar_participacoes_tx(tx, duel, winner_id)
            return {"status": "vitoria", "winner_id": winner_id, "wins_a": wins_a, "wins_b": wins_b,
                    "total_a": total_a, "total_b": total_b, "pote": pote, "payout": payout, "burned": burned,
                    "rodadas_jogadas": int(round_no), "encerrado_antecipadamente": encerrado_antecipadamente,
                    "recompensas": recompensas}

    async def coliseu_historico_rodadas(self, duel_id: int):
        return await self._all("SELECT * FROM cartas_duelo_rounds WHERE duel_id=? ORDER BY round_no", (int(duel_id),))

    async def coliseu_ranking_duelos(self, limite: int = 10):
        """Classifica duelistas por vitórias; lucro líquido é apenas critério secundário."""
        return await self._all(
            """SELECT user_id,SUM(vitoria) AS wins,SUM(participou) AS duels,SUM(lucro) AS lucro
               FROM (
                 SELECT creator_id AS user_id,
                        CASE WHEN winner_id=creator_id THEN 1 ELSE 0 END AS vitoria,
                        CASE WHEN status='finished' AND winner_id IS NOT NULL THEN 1 ELSE 0 END AS participou,
                        CASE WHEN status='finished' AND winner_id=creator_id THEN payout-aposta
                             WHEN status='finished' AND winner_id IS NOT NULL THEN -aposta ELSE 0 END AS lucro
                 FROM cartas_duelos
                 UNION ALL
                 SELECT opponent_id AS user_id,
                        CASE WHEN winner_id=opponent_id THEN 1 ELSE 0 END AS vitoria,
                        CASE WHEN status='finished' AND winner_id IS NOT NULL THEN 1 ELSE 0 END AS participou,
                        CASE WHEN status='finished' AND winner_id=opponent_id THEN payout-aposta
                             WHEN status='finished' AND winner_id IS NOT NULL THEN -aposta ELSE 0 END AS lucro
                 FROM cartas_duelos
               )
               GROUP BY user_id HAVING SUM(participou)>0
               ORDER BY wins DESC,duels DESC,lucro DESC,user_id ASC LIMIT ?""",
            (max(1, min(int(limite), 25)),),
        )

    async def coliseu_expirar_prazos(self):
        """Convites vencidos e partidas inativas devolvem integralmente as duas apostas."""
        # Roda a cada 5s: só abre transação de escrita se houver algo vencido.
        pendente = await self._one(
            """SELECT 1 FROM cartas_duelos
               WHERE (status='invited' AND expires_at<=CURRENT_TIMESTAMP)
                  OR (status='active' AND round_deadline<=CURRENT_TIMESTAMP) LIMIT 1"""
        )
        if not pendente:
            return []
        async with self.transaction() as tx:
            vencidos = await tx._all("SELECT * FROM cartas_duelos WHERE status='invited' AND expires_at<=CURRENT_TIMESTAMP")
            expirados = await tx._all("SELECT * FROM cartas_duelos WHERE status='active' AND round_deadline<=CURRENT_TIMESTAMP")
            resultado = []
            for row in vencidos:
                await tx.conn.execute("UPDATE cartas_duelos SET status='expired',end_reason='convite expirado' WHERE id=? AND status='invited'", (int(row["id"]),))
                resultado.append({"id": int(row["id"]), "status": "expired", "message_id": row["message_id"], "channel_id": row["channel_id"]})
            for row in expirados:
                duel_id = int(row["id"])
                for uid in (int(row["creator_id"]), int(row["opponent_id"])):
                    cur = await tx.conn.execute(
                        "UPDATE users SET denarios=denarios+? WHERE user_id=?", (int(row["aposta"]), uid)
                    )
                    await tx.conn.execute(
                        """INSERT OR IGNORE INTO cartas_transacoes(tx_key,user_id,kind,denarios_delta,duel_id)
                           VALUES (?,?, 'aposta_devolvida_timeout', ?, ?)""",
                        (f"duel:{duel_id}:timeout_refund:{uid}", uid, int(row["aposta"]), duel_id),
                    )
                await tx.conn.execute(
                    "UPDATE cartas_duelos SET status='cancelled',winner_id=NULL,payout=0,burned=0,end_reason='inatividade; apostas devolvidas' WHERE id=? AND status='active'",
                    (duel_id,),
                )
                resultado.append({"id": duel_id, "status": "timeout_refund", "message_id": row["message_id"], "channel_id": row["channel_id"]})
            return resultado
