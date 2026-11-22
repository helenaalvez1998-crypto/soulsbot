"""Testes de regressão para o núcleo de contribuições e interações comunitárias."""

import asyncio
import sqlite3

import pytest

pytest.importorskip("aiosqlite")
from database import Database


def run(coro):
    return asyncio.run(coro)


def test_community_approval_awards_xp_once_and_respects_weekly_cap():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            first = await db.criar_contribuicao(
                guild_id=10, user_id=20, kind="theory", game_name="Elden Ring",
                title="Teoria do primeiro anel", summary="Resumo", content="A" * 60,
            )
            approved = await db.decidir_contribuicao(first, 99, "approved", "OK", xp_base=20, xp_weekly_cap=25)
            assert approved["xp_awarded"] == 20
            assert approved["contribution"]["status"] == "approved"
            assert await db.decidir_contribuicao(first, 98, "approved", "duplicado", xp_base=20, xp_weekly_cap=25) is None

            second = await db.criar_contribuicao(
                guild_id=10, user_id=20, kind="guide", game_name="Dark Souls III",
                title="Guia de atalhos", summary="Resumo", content="B" * 60,
            )
            approved_second = await db.decidir_contribuicao(
                second, 99, "approved", "OK", xp_base=20, xp_weekly_cap=25
            )
            assert approved_second["xp_awarded"] == 5
            user = await db._one("SELECT xp FROM users WHERE user_id=20")
            awards = await db._one("SELECT COUNT(*) AS n FROM community_xp_awards WHERE user_id=20")
            assert int(user["xp"]) == 25
            assert int(awards["n"]) == 2
        finally:
            await db.close()

    run(scenario())


def test_community_reactions_bookmarks_follows_and_honors_are_unique_and_toggleable():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            assert await db.alternar_interacao(1, "platina", 7, 100, "gg") is True
            assert await db.alternar_interacao(1, "platina", 7, 100, "gg") is False
            assert await db.alternar_interacao(1, "platina", 7, 101, "gg") is True
            assert await db.contar_interacoes(1, "platina", 7) == {"gg": 1}

            assert await db.alternar_favorito(1, 100, "platina", 7) is True
            assert len(await db.listar_favoritos(1, 100)) == 1
            assert await db.alternar_favorito(1, 100, "platina", 7) is False
            assert await db.listar_favoritos(1, 100) == []

            assert await db.alternar_seguir(1, 100, 200) is True
            assert await db.contar_seguidores(1, 200) == 1
            assert await db.alternar_seguir(1, 100, 200) is False
            assert await db.contar_seguidores(1, 200) == 0

            assert await db.registrar_honra(1, 100, 200, "respect", "2026-W46") == "created"
            assert await db.registrar_honra(1, 100, 200, "respect", "2026-W46") == "already"
            assert await db.registrar_honra(1, 100, 201, "greatness", "2026-W46") == "changed"
            assert await db.contar_honras(1, 201) == {"greatness": 1}
        finally:
            await db.close()

    run(scenario())


def test_game_ratings_and_comments_are_saved_and_platina_syncs_to_zeroed():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            platina_id = await db.criar_platina_unica(
                101, "Sekiro", "PS5", "2026-11-20", "https://example.com/prova.png",
                9001, 9, "Combate excelente e chefes muito bem construídos.", 4,
            )
            assert platina_id is not None
            platina = await db.get_platina(platina_id)
            assert int(platina["rating"]) == 9
            assert int(platina["difficulty"]) == 4
            assert platina["comment"] == "Combate excelente e chefes muito bem construídos."

            result = await db.aprovar_platina_com_recompensa(
                platina_id, reviewer_id=999, xp=50, denarios=20,
                xp_zerado=10, denarios_zerado=5, limite_zerados=5,
            )
            assert result["platina_rating"] == 9
            assert result["platina_difficulty"] == 4
            assert result["platina_comment"] == "Combate excelente e chefes muito bem construídos."

            zerados = await db.zerados_do_usuario(101)
            assert len(zerados) == 1
            assert int(zerados[0]["rating"]) == 9
            assert int(zerados[0]["difficulty"]) == 4
            assert zerados[0]["comment"] == "Combate excelente e chefes muito bem construídos."

            manual_id = await db.criar_zerado_pendente(
                202, "Hades", "PC", "2026-11-21", "Loop viciante e ótima trilha.", 8, 2,
            )
            manual = await db.get_zerado(manual_id)
            assert int(manual["rating"]) == 8
            assert int(manual["difficulty"]) == 2
            assert manual["comment"] == "Loop viciante e ótima trilha."

            game = await db._one("SELECT id FROM sl_games LIMIT 1")
            if game is None:
                cur_game = await db.conn.execute("INSERT INTO sl_games(name) VALUES (?)", ("Dark Souls III",))
                game_id = cur_game.lastrowid
            else:
                game_id = int(game["id"])
            cur_challenge = await db.conn.execute(
                "INSERT INTO sl_challenges(name, game_id) VALUES (?,?)", ("Sem invocações", game_id)
            )
            cur_run = await db.conn.execute(
                "INSERT INTO sl_runs(user_id, game_id, challenge_id, build, seconds, rating, difficulty, comment) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (303, game_id, cur_challenge.lastrowid, "Força", 3600, 10, 5, "Desafio intenso."),
            )
            await db.conn.commit()
            run = await db._one("SELECT * FROM sl_runs WHERE id=?", (cur_run.lastrowid,))
            assert int(run["difficulty"]) == 5
            assert int(run["rating"]) == 10

            pending_zerado_id = await db.criar_zerado_pendente(
                404, "Hollow Knight", "Switch", "2026-11-20", "Registro inicial.", 6, 2,
            )
            pending_platina_id = await db.criar_platina_unica(
                404, "Hollow Knight", "Switch", "2026-11-21", "https://example.com/hk.png",
                9002, 9, "A platina exigiu bastante exploração.", 4,
            )
            await db.aprovar_platina_com_recompensa(
                pending_platina_id, reviewer_id=999, xp=10, denarios=5,
                xp_zerado=0, denarios_zerado=0, limite_zerados=5,
            )
            converted = await db.get_zerado(pending_zerado_id)
            assert converted["status"] == "approved"
            assert int(converted["rating"]) == 9
            assert int(converted["difficulty"]) == 4
            assert converted["comment"] == "A platina exigiu bastante exploração."
        finally:
            await db.close()

    run(scenario())



def test_existing_database_gets_nullable_difficulty_columns_without_losing_records(tmp_path):
    async def scenario():
        path = tmp_path / "soulsbot-migration.db"
        db = Database(str(path))
        await db.connect()
        try:
            platina_id = await db.criar_platina_unica(
                501, "Bloodborne", "PS4", "2026-11-21", "https://example.com/bb.png",
                None, 8, "Combate preciso e atmosfera excelente.", 4,
            )
            zerado_id = await db.criar_zerado_pendente(
                502, "Celeste", "PC", "2026-11-21", "Controles excelentes.", 9, 3,
            )
            assert platina_id is not None and zerado_id is not None
        finally:
            await db.close()

        # Simula um banco criado pela versão anterior, que ainda não tinha essas colunas.
        with sqlite3.connect(path) as conn:
            for table in ("platinas", "zerados", "sl_runs"):
                conn.execute(f"ALTER TABLE {table} DROP COLUMN difficulty")

        migrated = Database(str(path))
        await migrated.connect()
        try:
            platina = await migrated.get_platina(platina_id)
            zerado = await migrated.get_zerado(zerado_id)
            assert platina["comment"] == "Combate preciso e atmosfera excelente."
            assert int(platina["rating"]) == 8
            assert platina["difficulty"] is None
            assert zerado["comment"] == "Controles excelentes."
            assert int(zerado["rating"]) == 9
            assert zerado["difficulty"] is None
            for table in ("platinas", "zerados", "sl_runs"):
                columns = {row["name"] for row in await migrated._all(f"PRAGMA table_info({table})")}
                assert "difficulty" in columns
        finally:
            await migrated.close()

    run(scenario())

def test_approved_game_and_game_specific_challenge_are_materialized_idempotently():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            game_id = await db.criar_contribuicao(
                guild_id=1, user_id=2, kind="game_suggestion", game_name="",
                title="Elden Ring Nightreign", summary="Incluir nas runs", content="Jogo para novas categorias." * 4,
            )
            await db.decidir_contribuicao(game_id, 9, "approved", xp_base=10)
            applied_game = await db.aplicar_contribuicao_soulslike(game_id)
            applied_game_again = await db.aplicar_contribuicao_soulslike(game_id)
            assert applied_game["type"] == "sl_game"
            assert applied_game["created"] is True
            assert applied_game_again["created"] is False

            game = await db._one("SELECT id FROM sl_games WHERE name=?", ("Elden Ring Nightreign",))
            challenge_id = await db.criar_contribuicao(
                guild_id=1, user_id=3, kind="challenge", game_name="Elden Ring Nightreign",
                title="Sem invocações", summary="Terminar sem invocações", content="Não use invocações durante toda a campanha." * 3,
            )
            await db.decidir_contribuicao(challenge_id, 9, "approved", xp_base=15)
            applied_challenge = await db.aplicar_contribuicao_soulslike(challenge_id)
            challenge = await db._one("SELECT game_id FROM sl_challenges WHERE name=?", ("Sem invocações",))
            assert applied_challenge["type"] == "sl_challenge"
            assert int(challenge["game_id"]) == int(game["id"])
        finally:
            await db.close()

    run(scenario())


def test_challenge_participation_and_progress_require_a_registration():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            contribution = await db.criar_contribuicao(
                guild_id=5, user_id=10, kind="challenge", game_name="Dark Souls III",
                title="Sem escudo", summary="Não usar escudo", content="Conclua a campanha sem equipar escudos." * 3,
            )
            await db.decidir_contribuicao(contribution, 99, "approved", xp_base=15)
            assert await db.alternar_participacao_desafio(5, contribution, 11) is True
            assert await db.atualizar_progresso_desafio(5, contribution, 11, "in_progress", "Metade concluída", "") is True
            assert await db.atualizar_progresso_desafio(5, contribution, 12, "completed", "Concluído", "https://example.com/prova") is False
            assert await db.atualizar_progresso_desafio(5, contribution, 11, "completed", "Concluído", "https://example.com/prova") is True
            try:
                await db.alternar_participacao_desafio(5, contribution, 11)
            except ValueError:
                pass
            else:
                raise AssertionError("Participação concluída não pode ser removida pelo botão de inscrição")
            totals = await db.contar_participantes_desafio(5, contribution)
            assert totals == {"completed": 1}
        finally:
            await db.close()

    run(scenario())


def test_community_publication_registry_upserts_without_duplicate_rows():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            await db.registrar_post_comunitario(1, "run", 50, 100, 200)
            await db.registrar_post_comunitario(1, "run", 50, 101, 201, 202)
            row = await db.get_post_comunitario(1, "run", 50)
            count = await db._one("SELECT COUNT(*) AS n FROM community_posts")
            assert int(count["n"]) == 1
            assert int(row["channel_id"]) == 101
            assert int(row["message_id"]) == 201
            assert int(row["thread_id"]) == 202
        finally:
            await db.close()

    run(scenario())


def test_reports_are_deduplicated_and_hiding_archives_only_community_content():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            contribution = await db.criar_contribuicao(
                guild_id=44, user_id=100, kind="theory", game_name="Dark Souls",
                title="Teoria sobre Gwyn", summary="Resumo", content="C" * 80,
            )
            await db.decidir_contribuicao(contribution, 900, "approved", xp_base=15)
            await db.marcar_publicacao_contribuicao(contribution, 333, 444)
            await db.registrar_post_comunitario(44, "contrib_theory", contribution, 333, 444)

            report_id = await db.criar_denuncia_comunitaria(
                44, 200, "contrib_theory", contribution, "Informação enganosa", "A fonte citada não confirma o trecho." 
            )
            assert report_id is not None
            assert await db.criar_denuncia_comunitaria(
                44, 200, "contrib_theory", contribution, "Spam", "Duplicada."
            ) is None

            result = await db.decidir_denuncia_comunitaria(report_id, 901, "hidden", "Conteúdo retirado após revisão")
            assert result["status"] == "hidden"
            post = await db.get_post_comunitario(44, "contrib_theory", contribution)
            content = await db.get_contribuicao(contribution)
            assert int(post["is_hidden"]) == 1
            assert content["status"] == "archived"
            assert await db.listar_posts_comunitarios() == []
        finally:
            await db.close()

    run(scenario())


def test_existing_database_migrates_new_community_columns_without_replacing_tables(tmp_path):
    import sqlite3

    db_path = tmp_path / "legacy.sqlite3"
    raw = sqlite3.connect(db_path)
    raw.execute("CREATE TABLE sl_challenges (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, rules TEXT NOT NULL DEFAULT '')")
    raw.execute("CREATE TABLE community_posts (id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, target_type TEXT NOT NULL, target_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, message_id INTEGER NOT NULL, thread_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(guild_id,target_type,target_id))")
    raw.commit()
    raw.close()

    async def scenario():
        db = Database(str(db_path))
        await db.connect()
        try:
            challenge_columns = {row["name"] for row in await db._all("PRAGMA table_info(sl_challenges)")}
            post_columns = {row["name"] for row in await db._all("PRAGMA table_info(community_posts)")}
            assert "game_id" in challenge_columns
            assert "is_hidden" in post_columns
            await db._one("SELECT COUNT(*) AS n FROM community_reports")
        finally:
            await db.close()

    run(scenario())


def test_sanctuary_guestbook_limits_spam_and_allows_owner_moderation():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            assert await db.criar_mensagem_santuario(1, 100, 200, "Parabéns pela jornada!") == 1
            assert await db.criar_mensagem_santuario(1, 100, 200, "Outra mensagem no mesmo dia") is None
            assert len(await db.listar_mensagens_santuario(1, 100)) == 1
            assert await db.apagar_mensagem_santuario(1, 100, 1) is True
            assert await db.listar_mensagens_santuario(1, 100) == []
            try:
                await db.criar_mensagem_santuario(1, 200, 200, "Mensagem para mim mesmo")
            except ValueError:
                pass
            else:
                raise AssertionError("O próprio dono não deve escrever no Livro de Visitas")
        finally:
            await db.close()

    run(scenario())


def test_coliseu_run_rankings_and_gladiator_comparison_queries_are_available():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            assert await db.ranking_runs() == []
            assert await db.ranking_recordes_runs() == []
            assert await db.listar_gladiadores_comparacao(25) == []
        finally:
            await db.close()

    run(scenario())


def test_challenge_participant_listing_returns_progress_and_evidence():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            contribution = await db.criar_contribuicao(
                guild_id=8, user_id=10, kind="challenge", game_name="Dark Souls III",
                title="Sem escudo", summary="Não usar escudo", content="Conclua a campanha sem equipar escudos." * 3,
            )
            await db.decidir_contribuicao(contribution, 99, "approved", xp_base=15)
            await db.alternar_participacao_desafio(8, contribution, 20)
            await db.atualizar_progresso_desafio(8, contribution, 20, "in_progress", "Quatro chefes derrotados", "")
            rows = await db.listar_participantes_desafio(8, contribution)
            assert len(rows) == 1
            assert rows[0]["user_id"] == 20
            assert rows[0]["progress_note"] == "Quatro chefes derrotados"
        finally:
            await db.close()

    run(scenario())


def test_approved_community_faq_becomes_searchable_and_hidden_faq_is_deactivated():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            contribution = await db.criar_contribuicao(
                guild_id=12, user_id=21, kind="faq", game_name="NARA",
                title="Como acompanhar as novidades de um jogador?", summary="Configuração de notificações",
                content="Abra o painel de contribuições, escolha Notificações e ligue as categorias que deseja acompanhar. As atualizações chegam por mensagem direta quando disponíveis." * 2,
            )
            await db.decidir_contribuicao(contribution, 99, "approved", xp_base=10)
            entry_id = await db.ativar_faq_comunitaria(contribution)
            assert entry_id is not None
            found = await db.buscar_faq_comunitaria(12, "como eu acompanho as novidades de um jogador")
            assert found is not None and int(found["id"]) == entry_id

            await db.registrar_post_comunitario(12, "contrib_faq", contribution, 400, 500)
            report_id = await db.criar_denuncia_comunitaria(12, 22, "contrib_faq", contribution, "Resposta desatualizada", "A interface mudou.")
            await db.decidir_denuncia_comunitaria(report_id, 99, "hidden", "Conteúdo removido e FAQ desativada")
            assert await db.buscar_faq_comunitaria(12, "como eu acompanho as novidades de um jogador") is None
        finally:
            await db.close()

    run(scenario())


def test_legacy_community_contribution_table_receives_new_challenge_columns(tmp_path):
    import sqlite3

    db_path = tmp_path / "legacy_community.sqlite3"
    raw = sqlite3.connect(db_path)
    raw.execute("""CREATE TABLE community_contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,game_name TEXT NOT NULL DEFAULT '',title TEXT NOT NULL,summary TEXT NOT NULL DEFAULT '',
        content TEXT NOT NULL,sources TEXT NOT NULL DEFAULT '',spoiler_level TEXT NOT NULL DEFAULT 'none',
        status TEXT NOT NULL DEFAULT 'pending',reviewer_id INTEGER,review_note TEXT NOT NULL DEFAULT '',
        xp_awarded INTEGER NOT NULL DEFAULT 0,published_channel_id INTEGER,published_message_id INTEGER,
        published_thread_id INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    raw.commit()
    raw.close()

    async def scenario():
        db = Database(str(db_path))
        await db.connect()
        try:
            columns = {row["name"] for row in await db._all("PRAGMA table_info(community_contributions)")}
            assert {"challenge_mode", "challenge_goal", "applied_target_type", "applied_target_id"} <= columns
            await db._one("SELECT COUNT(*) AS n FROM community_faq_entries")
        finally:
            await db.close()

    run(scenario())


def test_collective_challenge_keeps_a_goal_and_counts_completed_members():
    async def scenario():
        db = Database(":memory:")
        await db.connect()
        try:
            contribution = await db.criar_contribuicao(
                guild_id=18, user_id=30, kind="challenge", game_name="Dark Souls III",
                title="Arena coletiva", summary="Reunir a comunidade para concluir a jornada",
                content="Cada participante deve concluir a campanha e anexar evidência verificável." * 2,
                challenge_mode="collective", challenge_goal=5,
            )
            row = await db.get_contribuicao(contribution)
            assert row["challenge_mode"] == "collective"
            assert row["challenge_goal"] == 5
            await db.decidir_contribuicao(contribution, 99, "approved", xp_base=15)
            for user_id in (40, 41, 42):
                await db.alternar_participacao_desafio(18, contribution, user_id)
                await db.atualizar_progresso_desafio(18, contribution, user_id, "completed", "Campanha concluída", "https://example.com/evidencia")
            totals = await db.contar_participantes_desafio(18, contribution)
            assert totals == {"completed": 3}
            participants = await db.listar_participantes_desafio(18, contribution)
            assert len(participants) == 3
        finally:
            await db.close()

    run(scenario())
