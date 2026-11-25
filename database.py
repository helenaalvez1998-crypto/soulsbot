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
    game_id INTEGER,
    coliseu_primordial_drop INTEGER NOT NULL DEFAULT -1,
    coliseu_singular_card_id TEXT NOT NULL DEFAULT ''
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
CREATE TABLE IF NOT EXISTS cartas_exemplares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    rarity TEXT NOT NULL DEFAULT 'Comum',
    power INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'migracao',
    obtained_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cartas_exemplares_user_card
    ON cartas_exemplares(user_id, card_id, id);
CREATE INDEX IF NOT EXISTS idx_cartas_exemplares_user_rarity
    ON cartas_exemplares(user_id, rarity);
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
CREATE TABLE IF NOT EXISTS cartas_transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_key TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    denarios_delta INTEGER NOT NULL DEFAULT 0,
    almas_delta INTEGER NOT NULL DEFAULT 0,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_cartas_transacoes_user_time ON cartas_transacoes(user_id, created_at);
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
CREATE TABLE IF NOT EXISTS cartas_atelie_submissoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_id TEXT NOT NULL,
    prompt_text TEXT NOT NULL DEFAULT '',
    image_data BLOB NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'image/jpeg',
    artist_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    reviewer_id INTEGER,
    rejection_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_atelie_submissoes_queue
    ON cartas_atelie_submissoes(status, created_at);
CREATE INDEX IF NOT EXISTS idx_atelie_submissoes_card
    ON cartas_atelie_submissoes(card_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_cartas_atelie_user_card_status
    ON cartas_atelie_artes(user_id, card_id, status, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cartas_atelie_pending_unique
    ON cartas_atelie_artes(user_id, card_id)
    WHERE status IN ('uploading','pending');
CREATE TABLE IF NOT EXISTS cartas_gwent_kit_inicial (
    user_id INTEGER PRIMARY KEY,
    delivered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_gwent_especiais_kit (
    user_id INTEGER PRIMARY KEY,
    delivered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_gwent_decks (
    user_id INTEGER PRIMARY KEY,
    card_ids_json TEXT NOT NULL,
    exemplar_ids_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_gwent_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    state_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(creator_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(opponent_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_gwent_match_players ON cartas_gwent_matches(creator_id, opponent_id, status);
CREATE TABLE IF NOT EXISTS cartas_gwent_rankings (
    user_id INTEGER PRIMARY KEY,
    mmr INTEGER NOT NULL DEFAULT 1000,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_gwent_rewards (
    match_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reward_denarios INTEGER NOT NULL DEFAULT 0,
    reward_xp INTEGER NOT NULL DEFAULT 0,
    mmr_delta INTEGER NOT NULL DEFAULT 0,
    drop_event_key TEXT NOT NULL DEFAULT '',
    milestone_drop_event_key TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(match_id, user_id),
    FOREIGN KEY(match_id) REFERENCES cartas_gwent_matches(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS cartas_recompensas (
    event_key TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    card_id TEXT,
    rarity TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL DEFAULT 'card',
    almas_delta INTEGER NOT NULL DEFAULT 0,
    fragmentos_delta INTEGER NOT NULL DEFAULT 0,
    exemplar_id INTEGER,
    power INTEGER,
    origin TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_fragmentos (
    user_id INTEGER PRIMARY KEY,
    quantidade INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cartas_movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    card_id TEXT NOT NULL,
    exemplar_id INTEGER,
    rarity_before TEXT NOT NULL DEFAULT '',
    rarity_after TEXT NOT NULL DEFAULT '',
    power_before INTEGER NOT NULL DEFAULT 0,
    power_after INTEGER NOT NULL DEFAULT 0,
    resource TEXT NOT NULL DEFAULT '',
    amount INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cartas_mov_user_time
    ON cartas_movimentacoes(user_id, created_at DESC, id DESC);

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
        "coliseu_primordial_drop": "INTEGER NOT NULL DEFAULT -1",
        "coliseu_singular_card_id": "TEXT NOT NULL DEFAULT ''",
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
    "cartas_gwent_decks": {
        "faction": "TEXT NOT NULL DEFAULT ''",
        "leader_id": "TEXT NOT NULL DEFAULT ''",
        "exemplar_ids_json": "TEXT NOT NULL DEFAULT '[]'",
    },
    "cartas_gwent_rankings": {
        "xp": "INTEGER NOT NULL DEFAULT 0",
    },
    "cartas_gwent_rewards": {
        "reward_xp": "INTEGER NOT NULL DEFAULT 0",
        "drop_event_key": "TEXT NOT NULL DEFAULT ''",
        "milestone_drop_event_key": "TEXT NOT NULL DEFAULT ''",
    },
    "cartas_recompensas": {
        "exemplar_id": "INTEGER",
        "power": "INTEGER",
        "origin": "TEXT NOT NULL DEFAULT ''",
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
        # Migração segura do inventário agregado para exemplares individuais.
        # O inventário legado permanece como índice de compatibilidade para módulos antigos.
        await self._migrar_cartas_exemplares()
        await self.conn.commit()

    async def _migrar_cartas_exemplares(self):
        """Cria exemplares para cartas antigas sem apagar nem alterar a coleção legada."""
        from sistemas.cartas import get_carta, carta_de_jogo_por_id
        rows = await self._all(
            "SELECT user_id,card_id,quantidade,source,game_name,obtained_at FROM cartas_colecao"
        )
        for row in rows:
            user_id = int(row["user_id"])
            card_id = str(row["card_id"])
            existing = await self._one(
                "SELECT COUNT(*) AS n FROM cartas_exemplares WHERE user_id=? AND card_id=?",
                (user_id, card_id),
            )
            missing = max(0, int(row["quantidade"] or 1) - int(existing["n"] or 0))
            if not missing:
                continue
            card = get_carta(card_id)
            if card is None and card_id.startswith("jogo_") and row["game_name"]:
                try:
                    card = carta_de_jogo_por_id(card_id, str(row["game_name"]))
                except ValueError:
                    card = None
            rarity = str(card.raridade if card else "Comum")
            power = int(card.poder if card else 1)
            for _ in range(missing):
                await self.conn.execute(
                    """INSERT INTO cartas_exemplares(user_id,card_id,rarity,power,source,obtained_at)
                       VALUES (?,?,?,?,?,COALESCE(?,CURRENT_TIMESTAMP))""",
                    (user_id, card_id, rarity, power, str(row["source"] or "migracao"), row["obtained_at"]),
                )

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
            desafio = await tx._one(
                "SELECT name,coliseu_primordial_drop,coliseu_singular_card_id FROM sl_challenges WHERE id=?",
                (int(run["challenge_id"]),),
            )
            desafio_nome = str(desafio["name"] or "").casefold() if desafio else ""
            no_hit = any(chave in desafio_nome for chave in ("no-hit", "no hit", "nohit"))
            feito_sem_dano = "sem tomar dano" in desafio_nome or no_hit
            feito_nivel1 = "nível 1" in desafio_nome or "nivel 1" in desafio_nome
            feito_todos_chefes = "todos os chefes" in desafio_nome
            singular_config = str(desafio["coliseu_singular_card_id"] or "") if desafio else ""
            if singular_config == "none":
                singular_id = ""
            elif singular_config:
                singular_id = singular_config
            elif feito_sem_dano:
                singular_id = "gwent_singular_intocavel"
            elif feito_nivel1:
                singular_id = "gwent_singular_nivel1"
            elif feito_todos_chefes:
                singular_id = "gwent_singular_cacador_chefes"
            else:
                singular_id = ""
            primordial_config = int(desafio["coliseu_primordial_drop"] if desafio and desafio["coliseu_primordial_drop"] is not None else -1)
            primordial_habilitado = (bool(primordial_config) if primordial_config >= 0
                                     else (feito_sem_dano or feito_nivel1 or feito_todos_chefes))
            drop = await self._coliseu_drop_tx(
                tx, int(run["user_id"]), f"run:{int(run_id)}", origem="run",
                permitir_primordial=primordial_habilitado,
            )
            singular_drop = None
            if singular_id:
                singular_drop = await self._coliseu_conceder_singular_tx(
                    tx, int(run["user_id"]), f"singular:run:{int(run_id)}", singular_id
                )
            return {
                "singular_drop": singular_drop,
                "card_id": drop.get("card_id"), "card_name": drop.get("card_name"),
                "card_rarity": drop.get("card_rarity"), "card_outcome": drop.get("outcome"),
                "card_almas": drop.get("card_almas", 0), "card_fragmentos": drop.get("card_fragmentos", 0),
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

    async def get_platina(self, platina_id: int):
        return await self._one("SELECT * FROM platinas WHERE id=?", (platina_id,))

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

            # A platina reconhece também o marco de zerado, mas entrega um único drop.
            drop = await self._coliseu_drop_tx(
                tx, user_id, f"platina:{int(platina_id)}", origem="platina"
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
                "card_id": drop.get("card_id"), "card_name": drop.get("card_name"),
                "card_rarity": drop.get("card_rarity"), "card_outcome": drop.get("outcome"),
                "card_almas": drop.get("card_almas", 0), "card_fragmentos": drop.get("card_fragmentos", 0),
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
            drop = await self._coliseu_drop_tx(
                tx, int(row["user_id"]), f"zerado:{int(zerado_id)}", origem="zerado"
            )
            carta_id = str(drop.get("card_id") or "")
            carta_nome = str(drop.get("card_name") or carta_id)
            carta_raridade = str(drop.get("card_rarity") or "")
            carta_adicionada = drop.get("outcome") == "carta"
            return {
                "id": zerado_id, "user_id": int(row["user_id"]), "game": row["game"],
                "platform": row["platform"], "finished_at": row["finished_at"],
                "comment": row["comment"], "rating": row["rating"], "difficulty": row["difficulty"], "proof_msg_id": row["proof_msg_id"],
                "xp": xp, "denarios": denarios, "old_xp": old_xp, "new_xp": new_xp,
                "old_level": old_level, "new_level": new_level,
                "daily_limit_reached": limite_atingido,
                 "card_id": carta_id, "card_name": carta_nome,
                "card_rarity": carta_raridade, "card_added": carta_adicionada,
                "card_outcome": drop.get("outcome"), "card_almas": drop.get("almas", 0),
                "card_fragmentos": drop.get("fragmentos", 0),
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

    async def remover_zerado_com_recompensa(self, zerado_id: int):
        """Remove o registro e reverte XP, Denários e o drop, quando ainda reversível."""
        import json
        async with self.transaction() as tx:
            row = await tx._one("SELECT * FROM zerados WHERE id=?", (zerado_id,))
            if not row:
                return None
            user_id = int(row["user_id"])
            reward = await tx._one(
                "SELECT * FROM cartas_recompensas WHERE event_key=?",
                (f"zerado:{int(zerado_id)}",),
            )
            if reward and reward["outcome"] not in ("revertido", "legado_preservado"):
                outcome = str(reward["outcome"] or "")
                if outcome == "carta":
                    exemplar_id = int(reward["exemplar_id"] or 0)
                    if not exemplar_id:
                        return {"erro": "Não foi possível identificar o exemplar concedido. Peça à moderação para revisar a recompensa antes de remover o registro."}
                    deck = await tx._one(
                        "SELECT card_ids_json,exemplar_ids_json FROM cartas_gwent_decks WHERE user_id=?",
                        (user_id,),
                    )
                    if deck:
                        exemplar_ids = json.loads(deck["exemplar_ids_json"] or "[]") if deck["exemplar_ids_json"] else []
                        card_ids = json.loads(deck["card_ids_json"] or "[]") if deck["card_ids_json"] else []
                        if exemplar_id in [int(value) for value in exemplar_ids if value]:
                            return {"erro": "A carta recebida por esse zerado está no seu deck salvo. Remova-a do deck antes de apagar o registro."}
                        if not exemplar_ids and str(reward["card_id"]) in card_ids:
                            return {"erro": "Esse modelo está em um deck legado. Atualize/remova a carta do deck antes de apagar o registro."}
                    exemplar = await tx._one(
                        "SELECT id,rarity,power FROM cartas_exemplares WHERE id=? AND user_id=?",
                        (exemplar_id, user_id),
                    )
                    if not exemplar:
                        return {"erro": "O exemplar da recompensa não está mais no inventário. Peça à moderação para revisar a remoção."}
                    if (str(exemplar["rarity"]) != str(reward["rarity"])
                            or int(exemplar["power"] or 0) != int(reward["power"] or 0)):
                        return {"erro": "A carta desse zerado já foi evoluída ou lapidada. A remoção automática foi bloqueada para não apagar progresso nem consumir recursos indevidamente; peça à moderação para revisar."}
                    await tx.conn.execute(
                        "DELETE FROM cartas_exemplares WHERE id=? AND user_id=?", (exemplar_id, user_id)
                    )
                    await tx.conn.execute(
                        "UPDATE cartas_colecao SET quantidade=MAX(0,quantidade-1) WHERE user_id=? AND card_id=?",
                        (user_id, str(reward["card_id"])),
                    )
                    await tx.conn.execute(
                        "DELETE FROM cartas_colecao WHERE user_id=? AND card_id=? AND quantidade<=0",
                        (user_id, str(reward["card_id"])),
                    )
                elif outcome == "almas":
                    delta = int(reward["almas_delta"] or 0)
                    saldo = await tx._one("SELECT quantidade FROM cartas_almas WHERE user_id=?", (user_id,))
                    if not saldo or int(saldo["quantidade"] or 0) < delta:
                        return {"erro": f"As {delta} Almas da duplicata já foram usadas. Recupere esse saldo ou peça à moderação para revisar a remoção."}
                    await tx.conn.execute(
                        "UPDATE cartas_almas SET quantidade=quantidade-?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                        (delta, user_id),
                    )
                elif outcome == "fragmentos":
                    delta = int(reward["fragmentos_delta"] or 0)
                    saldo = await tx._one("SELECT quantidade FROM cartas_fragmentos WHERE user_id=?", (user_id,))
                    if not saldo or int(saldo["quantidade"] or 0) < delta:
                        return {"erro": f"Os {delta} fragmentos da duplicata já foram usados. Recupere esse saldo ou peça à moderação para revisar a remoção."}
                    await tx.conn.execute(
                        "UPDATE cartas_fragmentos SET quantidade=quantidade-?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                        (delta, user_id),
                    )
                await tx.conn.execute(
                    "UPDATE cartas_recompensas SET outcome='revertido',exemplar_id=NULL WHERE event_key=?",
                    (f"zerado:{int(zerado_id)}",),
                )

            await tx.conn.execute("DELETE FROM zerados WHERE id=?", (zerado_id,))
            xp = int(row["xp_awarded"] or 0)
            denarios = int(row["denarios_awarded"] or 0)
            if xp or denarios:
                await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
                await tx.conn.execute(
                    "UPDATE users SET xp=MAX(0,xp-?), denarios=MAX(0,denarios-?) WHERE user_id=?",
                    (xp, denarios, user_id),
                )
                xp_row = await tx._one("SELECT xp FROM users WHERE user_id=?", (user_id,))
                row = dict(row)
                row["new_xp"] = int(xp_row["xp"])
            else:
                row = dict(row)
                row["new_xp"] = None
            row["recompensa_drop_revertida"] = bool(reward and reward["outcome"] not in ("revertido", "legado_preservado"))
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
            drop = None
            if status == "approved":
                drop = await self._coliseu_drop_tx(
                    tx, int(row["user_id"]), f"community:{int(contribution_id)}", origem=str(row["kind"])
                )
            updated = await tx._one("SELECT * FROM community_contributions WHERE id=?", (int(contribution_id),))
            return {
                "card_id": (drop or {}).get("card_id"),
                "card_name": (drop or {}).get("card_name"),
                "card_rarity": (drop or {}).get("card_rarity"),
                "card_outcome": (drop or {}).get("outcome"),
                "card_almas": (drop or {}).get("card_almas", 0),
                "card_fragmentos": (drop or {}).get("card_fragmentos", 0),
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

    async def coliseu_sincronizar_conquistas(self, user_id: int) -> int:
        """Converte marcos antigos sem recompensa em drops, preservando cartas temáticas já entregues."""
        from sistemas.cartas import carta_jogo
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            registros = await tx._all(
                """SELECT id,game,'zerado' AS marco,source_platina_id FROM zerados
                   WHERE user_id=? AND status='approved'
                   UNION ALL
                   SELECT id,game,'platina' AS marco,NULL AS source_platina_id FROM platinas
                   WHERE user_id=? AND status='approved'""",
                (int(user_id), int(user_id)),
            )
            recompensas = 0
            for row in registros:
                if str(row["marco"]) == "platina":
                    evento = f"platina:{int(row['id'])}"
                elif row["source_platina_id"]:
                    evento = f"platina:{int(row['source_platina_id'])}"
                else:
                    evento = f"zerado:{int(row['id'])}"
                ja = await tx._one("SELECT 1 FROM cartas_recompensas WHERE event_key=?", (evento,))
                if ja:
                    continue
                marco_legado = "platina" if evento.startswith("platina:") else "zerado"
                carta_legada = carta_jogo(str(row["game"]), marco_legado)
                ja_tinha_carta_legada = await tx._one(
                    "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                    (int(user_id), carta_legada.id),
                )
                if ja_tinha_carta_legada:
                    # Versões anteriores já entregavam cartas temáticas. Preserva-as e
                    # marca o evento como pago, evitando dar uma segunda carta retroativa.
                    await tx.conn.execute(
                        """INSERT INTO cartas_recompensas(event_key,user_id,card_id,rarity,outcome)
                           VALUES (?,?,?,?, 'legado_preservado')""",
                        (evento, int(user_id), carta_legada.id, carta_legada.raridade),
                    )
                    continue
                resultado = await self._coliseu_drop_tx(
                    tx, int(user_id), evento, origem="retroativo_" + str(row["marco"])
                )
                if resultado.get("status") == "ok":
                    recompensas += 1
            return recompensas

    async def coliseu_reivindicar_patentes(self, user_id: int, card_ids: list[str]) -> int:
        """Marcos de patente liberam drops globais; cartas fixas antigas são preservadas."""
        from sistemas.cartas import CARTAS_POR_ID
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (int(user_id),))
            novas = 0
            for card_id in card_ids:
                card_id = str(card_id)
                evento = f"patente:{int(user_id)}:{card_id[:100]}"
                ja = await tx._one("SELECT 1 FROM cartas_recompensas WHERE event_key=?", (evento,))
                if ja:
                    continue
                carta_legada = CARTAS_POR_ID.get(card_id)
                owned = await tx._one(
                    "SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                    (int(user_id), card_id),
                )
                if owned and carta_legada:
                    await tx.conn.execute(
                        """INSERT INTO cartas_recompensas(event_key,user_id,card_id,rarity,outcome)
                           VALUES (?,?,?,?, 'legado_preservado')""",
                        (evento, int(user_id), card_id, carta_legada.raridade),
                    )
                    continue
                resultado = await self._coliseu_drop_tx(
                    tx, int(user_id), evento, origem="patente"
                )
                novas += int(resultado.get("status") == "ok")
            return novas

    async def coliseu_entregar_drops_iniciais(self, user_id: int, quantidade: int = 12) -> int:
        """Entrega uma única vez um deck inicial de modelos globais aleatórios por drops."""
        import secrets
        from sistemas.cartas import CARTAS_PACOTE
        user_id = int(user_id)
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            # Contas antigas que já receberam qualquer kit conservam seu inventário;
            # não recebem outro kit ao atualizar o bot.
            marcadores = (
                ("cartas_kit_inicial", "user_id"),
                ("cartas_gwent_kit_inicial", "user_id"),
                ("cartas_gwent_especiais_kit", "user_id"),
            )
            ja_recebeu = False
            for tabela, coluna in marcadores:
                row = await tx._one(f"SELECT 1 FROM {tabela} WHERE {coluna}=?", (user_id,))
                ja_recebeu = ja_recebeu or row is not None
            if ja_recebeu:
                # Fecha os três caminhos antigos para que um downgrade/rollback não entregue kits extras.
                for tabela, _ in marcadores:
                    await tx.conn.execute(f"INSERT OR IGNORE INTO {tabela}(user_id) VALUES (?)", (user_id,))
                return 0
            for tabela, _ in marcadores:
                await tx.conn.execute(f"INSERT OR IGNORE INTO {tabela}(user_id) VALUES (?)", (user_id,))
            owned_rows = await tx._all("SELECT card_id FROM cartas_colecao WHERE user_id=?", (user_id,))
            owned = {str(row["card_id"]) for row in owned_rows}
            pool = [c for c in CARTAS_PACOTE if c.raridade != "Singular" and c.categoria != "Especial"
                    and not c.id.startswith("primordial_") and c.id not in owned]
            quantidade = max(0, min(int(quantidade), 12, len(pool)))
            selecionadas = secrets.SystemRandom().sample(pool, quantidade)
            entregues = 0
            for carta in selecionadas:
                resultado = await self._coliseu_drop_tx(
                    tx, user_id, f"starter:{user_id}:{carta.id}", origem="boas_vindas",
                    modelo_forcado=carta,
                )
                entregues += int(resultado.get("outcome") == "carta")
            return entregues

    async def coliseu_entregar_kit_especial_gwent(self, user_id: int, card_ids: list[str]) -> int:
        """Compatibilidade: kits fixos antigos foram substituídos por drops de boas-vindas."""
        return await self.coliseu_entregar_drops_iniciais(user_id, quantidade=12)

    async def coliseu_entregar_kit_gwent(self, user_id: int, card_ids: list[str]) -> int:
        """Compatibilidade: kits fixos antigos foram substituídos por drops de boas-vindas."""
        return await self.coliseu_entregar_drops_iniciais(user_id, quantidade=12)

    async def coliseu_entregar_kit_inicial(self, user_id: int, card_ids: list[str]) -> int:
        """Compatibilidade: kits fixos antigos foram substituídos por drops de boas-vindas."""
        return await self.coliseu_entregar_drops_iniciais(user_id, quantidade=12)

    async def coliseu_estado_usuario(self, user_id: int):
        user_id = int(user_id)
        await self.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await self.conn.execute("INSERT OR IGNORE INTO cartas_almas(user_id) VALUES (?)", (user_id,))
        await self.conn.execute("INSERT OR IGNORE INTO cartas_pity(user_id) VALUES (?)", (user_id,))
        await self.conn.commit()
        row = await self._one(
            """SELECT u.xp, u.denarios,
                      COALESCE((SELECT quantidade FROM cartas_almas WHERE user_id=u.user_id), 0) AS almas,
                      COALESCE((SELECT quantidade FROM cartas_fragmentos WHERE user_id=u.user_id), 0) AS fragmentos,
                      COALESCE((SELECT comuns_seguidas FROM cartas_pity WHERE user_id=u.user_id), 0) AS pity,
                      (SELECT COUNT(*) FROM cartas_colecao WHERE user_id=u.user_id) AS cartas
                 FROM users AS u WHERE u.user_id=?""",
            (user_id,),
        )
        return {
            "xp": int(row["xp"] or 0), "denarios": int(row["denarios"] or 0),
            "almas": int(row["almas"] or 0), "fragmentos": int(row["fragmentos"] or 0),
            "pity": int(row["pity"] or 0),
            "cartas": int(row["cartas"] or 0),
        }

    async def coliseu_listar_colecao(self, user_id: int):
        """Lista modelos possuídos e expõe o melhor exemplar para compatibilidade dos decks."""
        return await self._all(
            """SELECT c.card_id,c.quantidade,c.source,c.game_name,c.obtained_at,
                      e.id AS exemplar_id,e.rarity AS rarity,e.power AS exemplar_power,
                      (SELECT COUNT(*) FROM cartas_exemplares x
                       WHERE x.user_id=c.user_id AND x.card_id=c.card_id) AS exemplares
               FROM cartas_colecao c
               LEFT JOIN cartas_exemplares e ON e.id=(
                   SELECT x.id FROM cartas_exemplares x
                   WHERE x.user_id=c.user_id AND x.card_id=c.card_id
                   ORDER BY CASE x.rarity WHEN 'Singular' THEN 7 WHEN 'Primordial' THEN 6
                     WHEN 'Mítica' THEN 5 WHEN 'Lendária' THEN 4 WHEN 'Épica' THEN 3
                     WHEN 'Rara' THEN 2 ELSE 1 END DESC, x.power DESC, x.id ASC LIMIT 1
               )
               WHERE c.user_id=? ORDER BY c.obtained_at,c.card_id""",
            (int(user_id),),
        )

    async def coliseu_obter_dados_imagem(
        self, user_id: int, card_id: str, exemplar_id: int | None = None,
    ):
        """Busca somente a carta/exemplar da imagem pedida; nunca varre a coleção toda."""
        return await self._one(
            """SELECT c.card_id,c.game_name,c.source,
                      e.id AS exemplar_id,e.rarity,e.power AS exemplar_power
               FROM cartas_colecao c
               LEFT JOIN cartas_exemplares e ON e.id=(
                   SELECT x.id FROM cartas_exemplares x
                   WHERE x.user_id=c.user_id AND x.card_id=c.card_id
                     AND (? IS NULL OR x.id=?)
                   ORDER BY CASE x.rarity WHEN 'Singular' THEN 7 WHEN 'Primordial' THEN 6
                     WHEN 'Mítica' THEN 5 WHEN 'Lendária' THEN 4 WHEN 'Épica' THEN 3
                     WHEN 'Rara' THEN 2 ELSE 1 END DESC, x.power DESC, x.id ASC LIMIT 1
               )
               WHERE c.user_id=? AND c.card_id=? LIMIT 1""",
            (int(exemplar_id) if exemplar_id is not None else None,
             int(exemplar_id) if exemplar_id is not None else None,
             int(user_id), str(card_id)),
        )

    async def coliseu_aprimorar_exemplar(self, user_id: int, exemplar_id: int):
        """Lapida um exemplar em +1 poder usando Almas, sem ultrapassar a faixa da raridade/modelo."""
        from sistemas.cartas import CUSTO_APRIMORAMENTO_ALMAS, get_carta, carta_de_jogo_por_id, faixa_poder_exemplar
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT * FROM cartas_exemplares WHERE id=? AND user_id=?",
                (int(exemplar_id), int(user_id)),
            )
            if not row:
                return {"status": "nao_encontrado"}
            raridade = str(row["rarity"])
            custo = CUSTO_APRIMORAMENTO_ALMAS.get(raridade)
            if custo is None:
                return {"status": "limite_raridade"}
            carta_modelo = get_carta(str(row["card_id"]))
            if carta_modelo is None:
                legado = await tx._one(
                    "SELECT game_name FROM cartas_colecao WHERE user_id=? AND card_id=?",
                    (int(user_id), str(row["card_id"])),
                )
                if legado and legado["game_name"]:
                    try:
                        carta_modelo = carta_de_jogo_por_id(str(row["card_id"]), str(legado["game_name"]))
                    except ValueError:
                        carta_modelo = None
            if carta_modelo is None:
                return {"status": "carta_indisponivel"}
            if str(carta_modelo.categoria).casefold() == "especial":
                return {"status": "carta_especial_nao_aprimora"}
            _, maximo = faixa_poder_exemplar(carta_modelo, raridade)
            poder_atual = int(row["power"])
            if poder_atual >= maximo:
                return {"status": "limite_poder_modelo", "power": poder_atual, "max_power": maximo}
            saldo = await tx._one("SELECT quantidade FROM cartas_almas WHERE user_id=?", (int(user_id),))
            almas = int(saldo["quantidade"] or 0) if saldo else 0
            if almas < custo:
                return {"status": "almas_insuficientes", "necessarias": custo, "saldo": almas}
            novo_poder = poder_atual + 1
            await tx.conn.execute(
                "UPDATE cartas_almas SET quantidade=quantidade-?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (custo, int(user_id)),
            )
            await tx.conn.execute(
                "UPDATE cartas_exemplares SET power=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                (novo_poder, int(exemplar_id), int(user_id)),
            )
            await tx.conn.execute(
                "INSERT INTO cartas_movimentacoes(user_id,action,card_id,exemplar_id,rarity_before,rarity_after,power_before,power_after,resource,amount,source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (int(user_id), "lapidacao", str(row["card_id"]), int(exemplar_id), raridade, raridade,
                 poder_atual, novo_poder, "almas", custo, "colecao"),
            )
            return {"status": "ok", "exemplar_id": int(exemplar_id), "rarity": raridade,
                    "power": novo_poder, "max_power": maximo, "almas_gastas": custo}

    async def coliseu_historico_drops(self, user_id: int, limite: int = 15):
        limite = max(1, min(int(limite), 50))
        return await self._all(
            """SELECT event_key,card_id,rarity,outcome,almas_delta,fragmentos_delta,
                      exemplar_id,power,origin,created_at
               FROM cartas_recompensas WHERE user_id=? AND outcome!='legado_preservado'
               ORDER BY created_at DESC,event_key DESC LIMIT ?""",
            (int(user_id), limite),
        )

    async def coliseu_historico_movimentacoes(self, user_id: int, limite: int = 15):
        limite = max(1, min(int(limite), 50))
        return await self._all(
            """SELECT action,card_id,exemplar_id,rarity_before,rarity_after,power_before,power_after,
                      resource,amount,source,created_at
               FROM cartas_movimentacoes WHERE user_id=?
               ORDER BY created_at DESC,id DESC LIMIT ?""",
            (int(user_id), limite),
        )

    async def coliseu_listar_exemplares(self, user_id: int, card_id: str | None = None):
        if card_id:
            return await self._all(
                """SELECT id,card_id,rarity,power,source,obtained_at FROM cartas_exemplares
                   WHERE user_id=? AND card_id=? ORDER BY id""", (int(user_id), str(card_id)))
        return await self._all(
            """SELECT id,card_id,rarity,power,source,obtained_at FROM cartas_exemplares
               WHERE user_id=? ORDER BY obtained_at,id""", (int(user_id),))

    async def coliseu_evoluir_exemplar(self, user_id: int, exemplar_id: int):
        """Evolui exemplar consumindo fragmentos; Primordiais e Singulares são finais."""
        import secrets
        from sistemas.cartas import RARIDADES, BONUS_EVOLUCAO_FRAGMENTOS, get_carta, carta_de_jogo_por_id, faixa_poder_exemplar
        custos = BONUS_EVOLUCAO_FRAGMENTOS
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT * FROM cartas_exemplares WHERE id=? AND user_id=?",
                (int(exemplar_id), int(user_id)))
            if not row:
                return {"status": "nao_encontrado"}
            raridade = str(row["rarity"])
            if raridade not in custos:
                return {"status": "limite_raridade"}
            proxima = RARIDADES[RARIDADES.index(raridade) + 1]
            if proxima in ("Primordial", "Singular"):
                return {"status": "limite_raridade"}
            ja_tem_destino = await tx._one(
                "SELECT id FROM cartas_exemplares WHERE user_id=? AND card_id=? AND rarity=? AND id<>? LIMIT 1",
                (int(user_id), str(row["card_id"]), proxima, int(exemplar_id)),
            )
            if ja_tem_destino:
                return {"status": "destino_ja_possuido", "rarity": proxima,
                        "exemplar_id": int(ja_tem_destino["id"])}
            custo = custos[raridade]
            carta_modelo = get_carta(str(row["card_id"]))
            if carta_modelo is None:
                # Cartas de jogo são derivadas do título guardado no inventário legado.
                legado = await tx._one("SELECT game_name FROM cartas_colecao WHERE user_id=? AND card_id=?",
                                       (int(user_id), str(row["card_id"])))
                if legado and legado["game_name"]:
                    try:
                        carta_modelo = carta_de_jogo_por_id(str(row["card_id"]), str(legado["game_name"]))
                    except ValueError:
                        carta_modelo = None
            if carta_modelo is None:
                return {"status": "carta_indisponivel"}
            if str(carta_modelo.categoria).casefold() == "especial":
                return {"status": "carta_especial_nao_evolui"}
            minimo, maximo = faixa_poder_exemplar(carta_modelo, proxima)
            if maximo <= int(row["power"]):
                return {"status": "limite_poder_modelo"}
            saldo = await tx._one("SELECT quantidade FROM cartas_fragmentos WHERE user_id=?", (int(user_id),))
            if not saldo or int(saldo["quantidade"] or 0) < custo:
                return {"status": "fragmentos_insuficientes", "necessarios": custo,
                        "saldo": int(saldo["quantidade"] or 0) if saldo else 0}
            # Só debita depois de validar propriedade, modelo, categoria, faixa e saldo.
            novo_poder = min(maximo, max(minimo, int(row["power"]) + 1 + secrets.randbelow(2)))
            await tx.conn.execute(
                "UPDATE cartas_fragmentos SET quantidade=quantidade-?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (custo, int(user_id)))
            await tx.conn.execute(
                "UPDATE cartas_exemplares SET rarity=?,power=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                (proxima, novo_poder, int(exemplar_id), int(user_id)))
            await tx.conn.execute(
                "INSERT INTO cartas_movimentacoes(user_id,action,card_id,exemplar_id,rarity_before,rarity_after,power_before,power_after,resource,amount,source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (int(user_id), "evolucao", str(row["card_id"]), int(exemplar_id), raridade, proxima,
                 int(row["power"]), novo_poder, "fragmentos", custo, "colecao"),
            )
            return {"status": "ok", "exemplar_id": int(exemplar_id), "rarity": proxima,
                    "power": novo_poder, "fragmentos_gastos": custo}

    # ---------- Ateliê de artes do Coliseu ----------
    # ---------- Ateliê web: submissão comunitária e arte oficial por modelo ----------
    async def coliseu_atelie_criar_submissao_web(
        self, user_id: int, card_id: str, prompt_text: str, image_data: bytes,
        mime_type: str = "image/jpeg", artist_name: str = "",
    ):
        """Registra uma arte comunitária pendente; a aprovação define a arte oficial do modelo."""
        async with self.transaction() as tx:
            owned = await tx._one(
                "SELECT 1 FROM cartas_exemplares WHERE user_id=? AND card_id=? LIMIT 1",
                (int(user_id), str(card_id)),
            )
            if not owned:
                return {"status": "not_owned"}
            pending = await tx._one(
                "SELECT id FROM cartas_atelie_submissoes WHERE user_id=? AND card_id=? AND status='pending' LIMIT 1",
                (int(user_id), str(card_id)),
            )
            if pending:
                return {"status": "pending_exists", "submission_id": int(pending["id"])}
            count = await tx._one(
                "SELECT COUNT(*) AS total FROM cartas_atelie_submissoes WHERE user_id=? AND status='pending'",
                (int(user_id),),
            )
            if int(count["total"] or 0) >= 3:
                return {"status": "pending_limit"}
            cur = await tx.conn.execute(
                """INSERT INTO cartas_atelie_submissoes
                   (user_id,card_id,prompt_text,image_data,mime_type,artist_name,status)
                   VALUES (?,?,?,?,?,?,'pending')""",
                (int(user_id), str(card_id), str(prompt_text)[:12000], bytes(image_data),
                 str(mime_type)[:80], str(artist_name)[:100]),
            )
            return {"status": "ok", "submission_id": int(cur.lastrowid)}

    async def coliseu_atelie_listar_pendentes_web(self, limite: int = 50):
        rows = await self._all(
            """SELECT id,user_id,card_id,prompt_text,mime_type,artist_name,created_at
               FROM cartas_atelie_submissoes WHERE status='pending'
               ORDER BY created_at ASC,id ASC LIMIT ?""", (max(1, min(int(limite), 100)),),
        )
        return [dict(row) for row in rows]

    async def coliseu_atelie_decidir_web(self, submission_id: int, reviewer_id: int, aprovado: bool, motivo: str = ""):
        async with self.transaction() as tx:
            row = await tx._one(
                "SELECT * FROM cartas_atelie_submissoes WHERE id=? AND status='pending'",
                (int(submission_id),),
            )
            if not row:
                return {"status": "processed"}
            new_status = "approved" if aprovado else "rejected"
            if aprovado:
                await tx.conn.execute(
                    "UPDATE cartas_atelie_submissoes SET status='archived' WHERE card_id=? AND status='approved'",
                    (str(row["card_id"]),),
                )
            await tx.conn.execute(
                """UPDATE cartas_atelie_submissoes SET status=?,reviewer_id=?,rejection_reason=?,
                   reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'""",
                (new_status, int(reviewer_id), str(motivo or "")[:500], int(submission_id)),
            )
            return {"status": "ok", "submission": dict(row), "new_status": new_status}

    async def coliseu_atelie_obter_arte_oficial_metadata(self, card_id: str):
        """Consulta metadados sem copiar o BLOB da arte em toda requisição de imagem."""
        return await self._one(
            """SELECT id,user_id,card_id,mime_type,artist_name,created_at,
                      length(image_data) AS image_size
               FROM cartas_atelie_submissoes WHERE card_id=? AND status='approved'
               ORDER BY reviewed_at DESC,id DESC LIMIT 1""",
            (str(card_id),),
        )

    async def coliseu_atelie_obter_arte_oficial(self, card_id: str):
        return await self._one(
            """SELECT id,user_id,card_id,image_data,mime_type,artist_name,created_at
               FROM cartas_atelie_submissoes WHERE card_id=? AND status='approved'
               ORDER BY reviewed_at DESC,id DESC LIMIT 1""", (str(card_id),),
        )

    async def coliseu_atelie_historico_web(self, user_id: int, limite: int = 30):
        rows = await self._all(
            """SELECT id,card_id,artist_name,status,rejection_reason,created_at,reviewed_at
               FROM cartas_atelie_submissoes WHERE user_id=?
               ORDER BY id DESC LIMIT ?""", (int(user_id), max(1, min(int(limite), 100))),
        )
        return [dict(row) for row in rows]

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

    async def _coliseu_drop_tx(self, tx, user_id: int, event_key: str, *, origem: str = "atividade",
                               permitir_primordial: bool = False, modelo_forcado=None,
                               raridade_forcada: str | None = None):
        """Drop global idempotente. A raridade pertence ao exemplar, não ao modelo."""
        import secrets
        from sistemas.cartas import (CARTAS_PACOTE, CARTAS_PRIMORDIAIS, faixa_poder_exemplar,
                                     ALMAS_DUPLICATA)
        ja = await tx._one("SELECT * FROM cartas_recompensas WHERE event_key=?", (str(event_key),))
        if ja:
            return {"status": "ja_concedido", "card_id": ja["card_id"], "outcome": ja["outcome"],
                    "card_rarity": ja["rarity"], "exemplar_id": ja["exemplar_id"], "card_power": ja["power"]}

        # O catálogo é global: qualquer modelo elegível pode sair em qualquer atividade.
        modelos = [c for c in CARTAS_PACOTE if c.raridade != "Singular"]
        primordiais = list(CARTAS_PRIMORDIAIS)
        pesos = [("Comum", 6940), ("Rara", 2200), ("Épica", 700),
                 ("Lendária", 100), ("Mítica", 50)]
        if permitir_primordial:
            pesos.append(("Primordial", 10))
        total = sum(p for _, p in pesos)
        if raridade_forcada in {nome for nome, _ in pesos}:
            raridade = str(raridade_forcada)
        else:
            sorteio = secrets.randbelow(total)
            acumulado = 0
            raridade = "Comum"
            for nome, peso in pesos:
                acumulado += peso
                if sorteio < acumulado:
                    raridade = nome
                    break
        carta = (modelo_forcado if modelo_forcado is not None else
                 secrets.choice(primordiais if raridade == "Primordial" else modelos))
        if raridade == "Primordial" and modelo_forcado is not None:
            # Um drop inicial não pode contornar as condições especiais de Primordial.
            raridade = "Mítica"

        user_id = int(user_id)
        await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await tx.conn.execute("INSERT OR IGNORE INTO cartas_almas(user_id) VALUES (?)", (user_id,))
        await tx.conn.execute("INSERT OR IGNORE INTO cartas_fragmentos(user_id) VALUES (?)", (user_id,))
        # Duplicata significa repetir o MESMO modelo na MESMA raridade.
        # O mesmo modelo pode existir em raridades diferentes, cada qual como exemplar próprio.
        owned_same_rarity = await tx._one(
            "SELECT id FROM cartas_exemplares WHERE user_id=? AND card_id=? AND rarity=? LIMIT 1",
            (user_id, carta.id, raridade),
        )
        almas = fragmentos = exemplar_id = 0
        faixa = faixa_poder_exemplar(carta, raridade)
        power = secrets.choice(range(faixa[0], faixa[1] + 1)) if faixa[1] >= faixa[0] else 0
        if owned_same_rarity:
            if secrets.randbelow(2) == 0:
                almas = int(ALMAS_DUPLICATA.get(raridade, 0))
                await tx.conn.execute(
                    "UPDATE cartas_almas SET quantidade=quantidade+?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                    (almas, user_id))
                outcome = "almas"
            else:
                fragmentos = {"Comum": 1, "Rara": 2, "Épica": 4, "Lendária": 8,
                              "Mítica": 10, "Primordial": 12}.get(raridade, 0)
                await tx.conn.execute(
                    "UPDATE cartas_fragmentos SET quantidade=quantidade+?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                    (fragmentos, user_id))
                outcome = "fragmentos"
        else:
            owned_model = await tx._one(
                "SELECT quantidade FROM cartas_colecao WHERE user_id=? AND card_id=?",
                (user_id, carta.id),
            )
            if owned_model:
                await tx.conn.execute(
                    "UPDATE cartas_colecao SET quantidade=quantidade+1 WHERE user_id=? AND card_id=?",
                    (user_id, carta.id),
                )
            else:
                await tx.conn.execute(
                    "INSERT INTO cartas_colecao(user_id,card_id,quantidade,source) VALUES (?,?,1,?)",
                    (user_id, carta.id, f"drop_{str(origem)[:32]}"))
            cur = await tx.conn.execute(
                """INSERT INTO cartas_exemplares(user_id,card_id,rarity,power,source)
                   VALUES (?,?,?,?,?)""",
                (user_id, carta.id, raridade, power, f"drop_{str(origem)[:32]}"))
            exemplar_id = int(cur.lastrowid)
            outcome = "carta"
        await tx.conn.execute(
            """INSERT INTO cartas_recompensas(event_key,user_id,card_id,rarity,outcome,almas_delta,fragmentos_delta,exemplar_id,power,origin)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (str(event_key), user_id, carta.id, raridade, outcome, almas, fragmentos,
             exemplar_id or None, power, str(origem)[:48]))
        resultado = {"status": "ok", "card_id": carta.id, "card_name": carta.nome,
                "card_rarity": raridade, "card_power": power, "exemplar_id": exemplar_id,
                "outcome": outcome, "almas": almas, "fragmentos": fragmentos,
                "card_almas": almas, "card_fragmentos": fragmentos}
        # Fila de anúncios públicos (drena em bot._loop_anuncios_drops)
        org = str(origem).lower()
        if outcome == "carta" and not any(x in org for x in ("pacote", "vitoria", "gwent", "loja", "atividade")):
            if not hasattr(self, "fila_anuncios"):
                self.fila_anuncios = []
            self.fila_anuncios.append({"user_id": int(user_id), "origem": org, "card_name": carta.nome,
                                       "rarity": raridade, "power": power})
        return resultado

    async def _coliseu_conceder_singular_tx(self, tx, user_id: int, event_key: str,
                                             card_id: str = "gwent_singular_primeiro"):
        """Drop especial Singular: cada modelo pode ser conquistado uma vez por jogador."""
        from sistemas.cartas import CARTAS_POR_ID
        card = CARTAS_POR_ID.get(str(card_id))
        if card is None:
            return {"status": "catalogo_invalido"}
        ja = await tx._one("SELECT 1 FROM cartas_recompensas WHERE event_key=?", (str(event_key),))
        if ja:
            return {"status": "ja_concedido"}
        user_id = int(user_id)
        await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        owned = await tx._one("SELECT 1 FROM cartas_colecao WHERE user_id=? AND card_id=?",
                              (user_id, card.id))
        if owned:
            outcome = "singular_ja_possui"
            exemplar_id = None
        else:
            await tx.conn.execute(
                "INSERT INTO cartas_colecao(user_id,card_id,quantidade,source) VALUES (?,?,1,'feito_singular')",
                (user_id, card.id))
            cur = await tx.conn.execute(
                "INSERT INTO cartas_exemplares(user_id,card_id,rarity,power,source) VALUES (?,?,?,?,?)",
                (user_id, card.id, "Singular", card.poder, "feito_singular"))
            exemplar_id = int(cur.lastrowid)
            outcome = "singular"
        await tx.conn.execute(
            """INSERT INTO cartas_recompensas(event_key,user_id,card_id,rarity,outcome,exemplar_id,power,origin)
               VALUES (?,?,?,?,?,?,?,?)""",
            (str(event_key), user_id, card.id, "Singular", outcome, exemplar_id, int(card.poder), "feito_singular"))
        return {"status": "ok", "card_id": card.id, "card_name": card.nome,
                "card_rarity": "Singular", "exemplar_id": exemplar_id, "outcome": outcome}

    async def coliseu_conceder_drop(self, user_id: int, event_key: str, *, origem: str = "atividade"):
        """Concede drop global idempotente para uma aprovação já confirmada."""
        async with self.transaction() as tx:
            return await self._coliseu_drop_tx(tx, user_id, event_key, origem=origem)

    async def coliseu_abrir_pacote(self, user_id: int, catalogo_por_raridade: dict | None = None,
                                   almas_por_raridade: dict | None = None, preco: int = 120, quantidade: int = 3,
                                   limite_pacotes_dia: int = 3):
        """Compra um pacote e concede três exemplares em uma única transação."""
        import json, secrets, uuid
        user_id = int(user_id)
        preco = max(1, int(preco))
        quantidade = max(1, min(int(quantidade), 10))
        limite_pacotes_dia = max(1, int(limite_pacotes_dia))
        async with self.transaction() as tx:
            await tx.conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
            await tx.conn.execute("INSERT OR IGNORE INTO cartas_pity(user_id) VALUES (?)", (user_id,))
            user = await tx._one("SELECT denarios FROM users WHERE user_id=?", (user_id,))
            saldo = int(user["denarios"] or 0) if user else 0
            abertos = await tx._one(
                "SELECT COUNT(*) AS n FROM cartas_transacoes WHERE user_id=? AND kind='pacote_fogueira' AND created_at>=datetime('now','-1 day')",
                (user_id,),
            )
            pacotes_24h = int(abertos["n"] or 0) if abertos else 0
            if pacotes_24h >= limite_pacotes_dia:
                return {"status": "limite_pacotes_dia", "limite": limite_pacotes_dia, "abertos": pacotes_24h}
            if saldo < preco:
                return {"status": "sem_saldo", "saldo": saldo, "preco": preco}

            pity_row = await tx._one("SELECT comuns_seguidas FROM cartas_pity WHERE user_id=?", (user_id,))
            streak = int(pity_row["comuns_seguidas"] or 0) if pity_row else 0
            pack_id = uuid.uuid4().hex
            aberturas = []
            for index in range(quantidade):
                pity_ativado = streak >= 10
                raridade_forcada = None
                if pity_ativado:
                    roll = secrets.randbelow(31)
                    raridade_forcada = ("Rara" if roll < 22 else "Épica" if roll < 29
                                        else "Lendária" if roll == 29 else "Mítica")
                result = await self._coliseu_drop_tx(
                    tx, user_id, f"pack:{pack_id}:{index}", origem="pacote_fogueira",
                    permitir_primordial=not pity_ativado, raridade_forcada=raridade_forcada,
                )
                if result.get("status") not in {"ok", "ja_concedido"}:
                    return {"status": "catalogo_invalido"}
                rarity = str(result.get("card_rarity") or "Comum")
                streak = streak + 1 if rarity == "Comum" else 0
                aberturas.append({
                    "card_id": result.get("card_id"), "card_name": result.get("card_name"),
                    "rarity": rarity, "power": int(result.get("card_power") or 0),
                    "outcome": result.get("outcome"), "almas": int(result.get("almas") or 0),
                    "fragmentos": int(result.get("fragmentos") or 0),
                    "exemplar_id": result.get("exemplar_id"), "pity_ativado": pity_ativado,
                })
            cur = await tx.conn.execute(
                "UPDATE users SET denarios=denarios-? WHERE user_id=? AND denarios>=?",
                (preco, user_id, preco),
            )
            if cur.rowcount != 1:
                return {"status": "sem_saldo", "saldo": saldo, "preco": preco}
            await tx.conn.execute(
                "UPDATE cartas_pity SET comuns_seguidas=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (streak, user_id),
            )
            await tx.conn.execute(
                "INSERT INTO cartas_transacoes(tx_key,user_id,kind,denarios_delta,details_json) VALUES (?,?,?,?,?)",
                (f"pack-purchase:{pack_id}", user_id, "pacote_fogueira", -preco,
                 json.dumps({"cards": aberturas, "quantity": quantidade}, ensure_ascii=False)),
            )
            novo_saldo = await tx._one("SELECT denarios FROM users WHERE user_id=?", (user_id,))
            return {"status": "ok", "cards": aberturas, "pity": streak,
                    "saldo": int(novo_saldo["denarios"] or 0),
                    "pacotes_restantes": max(0, limite_pacotes_dia - pacotes_24h - 1), "preco": preco}
