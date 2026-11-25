"""Rotas do portal NARA: submissões web e histórico pessoal."""
from __future__ import annotations
import os, re, uuid, json
from pathlib import Path
from aiohttp import web

ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"}
MAX_FILE = 8 * 1024 * 1024

def registrar_rotas(bot, app: web.Application) -> None:
    import config
    base = Path(config.DATA_DIR) / "site_uploads"
    base.mkdir(parents=True, exist_ok=True)

    def user_id(request):
        return bot._api_user_id(request)

    async def ensure_table():
        await bot.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS site_submission_proofs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                submission_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                filename TEXT NOT NULL,
                media_type TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await bot.db.conn.commit()

    async def upload_file(part, uid, kind, submission_id):
        filename = Path(part.filename or "comprovante").name
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED:
            raise ValueError("Formato não permitido. Use PNG, JPG, WEBP, GIF, MP4 ou WEBM.")
        data = await part.read()
        if not data or len(data) > MAX_FILE:
            raise ValueError("Cada arquivo deve ter até 8 MB.")
        safe = f"{uuid.uuid4().hex}{ext}"
        (base / safe).write_bytes(data)
        url = f"/api/portal/uploads/{safe}"
        await bot.db.conn.execute(
            "INSERT INTO site_submission_proofs(kind,submission_id,user_id,url,filename,media_type) VALUES(?,?,?,?,?,?)",
            (kind, submission_id, uid, url, filename[:180], part.headers.get("Content-Type", "")[:100])
        )
        return url

    async def submit(request: web.Request):
        uid = user_id(request)
        if uid is None:
            return web.json_response({"error":"Entre com sua conta Discord."}, status=401)
        if not bot._api_origin_ok(request):
            return web.json_response({"error":"Origem não autorizada."}, status=403)
        kind = request.match_info["kind"]
        if kind not in {"platina", "zerado"}:
            return web.json_response({"error":"Tipo de envio inválido."}, status=404)
        try:
            reader = await request.multipart()
            fields = {}
            files = []
            async for part in reader:
                if part.name == "proofs" and part.filename:
                    files.append(part)
                else:
                    fields[part.name] = (await part.text()).strip()
            game = fields.get("game","")[:100]
            platform = fields.get("platform","")[:40]
            date = fields.get("date","")
            comment = fields.get("comment","")[:500]
            if not game or not platform or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                return web.json_response({"error":"Preencha jogo, plataforma e data corretamente."}, status=400)
            rating = int(fields["rating"]) if fields.get("rating","").isdigit() else None
            difficulty = int(fields["difficulty"]) if fields.get("difficulty","").isdigit() else None
            if rating is not None and not 1 <= rating <= 10:
                return web.json_response({"error":"A nota deve ser de 1 a 10."}, status=400)
            if difficulty is not None and not 1 <= difficulty <= 5:
                return web.json_response({"error":"A dificuldade deve ser de 1 a 5."}, status=400)
            if len(files) > 5:
                return web.json_response({"error":"Envie no máximo 5 comprovantes."}, status=400)
            if kind == "platina" and not files:
                return web.json_response({"error":"Adicione ao menos um comprovante da platina."}, status=400)
            if kind == "platina":
                first_proof = "site://pending-proof"
                sid = await bot.db.criar_platina_unica(uid, game, platform, date, first_proof, None, rating, comment, difficulty)
            else:
                sid = await bot.db.criar_zerado_pendente(uid, game, platform, date, comment, rating, difficulty)
            if sid is None:
                return web.json_response({"error":"Você já possui um registro pendente ou aprovado desse jogo nessa plataforma."}, status=409)
            await ensure_table()
            try:
                for part in files[:5]:
                    await upload_file(part, uid, kind, sid)
                await bot.db.conn.commit()
                if kind == "platina":
                    rows = await bot.db._all("SELECT url FROM site_submission_proofs WHERE kind=? AND submission_id=? ORDER BY id", (kind,sid))
                    if rows:
                        await bot.db.conn.execute("UPDATE platinas SET proof_url=? WHERE id=?", (rows[0]["url"],sid))
                        await bot.db.conn.commit()
                return web.json_response({"ok":True,"id":sid,"status":"pending","message":"Envio registrado e aguardando aprovação."})
            except Exception:
                if kind == "platina":
                    await bot.db.excluir_platina_pendente(sid)
                else:
                    await bot.db.apagar_zerado(sid)
                raise
        except ValueError as exc:
            return web.json_response({"error":str(exc)}, status=400)
        except Exception:
            return web.json_response({"error":"Não foi possível concluir o envio. Tente novamente."}, status=500)

    async def mine(request):
        uid = user_id(request)
        if uid is None:
            return web.json_response({"error":"Autenticação necessária."}, status=401)
        await ensure_table()
        plats = await bot.db._all(
            "SELECT id,game,platform,earned_at AS date,status,comment,created_at,'platina' AS kind FROM platinas WHERE user_id=? ORDER BY id DESC LIMIT 100",(uid,))
        zeros = await bot.db._all(
            "SELECT id,game,platform,finished_at AS date,status,comment,created_at,'zerado' AS kind FROM zerados WHERE user_id=? ORDER BY id DESC LIMIT 100",(uid,))
        runs = await bot.db._all(
            "SELECT r.id,g.name AS game,c.name AS platform,substr(r.created_at,1,10) AS date,r.status,r.comment,r.created_at,'run' AS kind FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id WHERE r.user_id=? ORDER BY r.id DESC LIMIT 100",(uid,))
        items = [dict(x) for x in list(plats)+list(zeros)+list(runs)]
        items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        for item in items:
            proofs = await bot.db._all("SELECT url,filename,media_type FROM site_submission_proofs WHERE kind=? AND submission_id=? AND user_id=? ORDER BY id",
                (item["kind"],item["id"],uid))
            item["proofs"] = [dict(p) for p in proofs]
        return web.json_response({"items":items[:100]}, headers={"Cache-Control":"no-store"})

    async def serve_upload(request):
        name = Path(request.match_info["filename"]).name
        if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|jpeg|webp|gif|mp4|webm)", name):
            raise web.HTTPNotFound()
        path = base / name
        if not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control":"private, max-age=3600","X-Content-Type-Options":"nosniff"})


    def guild_id():
        import config
        return int(getattr(config, "GUILD_ID", 0) or 0)

    async def is_moderator(uid):
        guild = bot.get_guild(guild_id()) if guild_id() else None
        if guild is None:return False
        member = guild.get_member(int(uid))
        if member is None:
            try: member=await guild.fetch_member(int(uid))
            except Exception:return False
        if member.guild_permissions.manage_guild or member.guild_permissions.administrator:
            return True
        import admin_config, config
        role_id=await admin_config.GuildConfig.get(bot.db,guild.id,"mod_role")
        fallback=int(getattr(config,"MOD_ROLE_ID",0) or 0)
        return bool((role_id and any(r.id==int(role_id) for r in member.roles)) or
                    (fallback and any(r.id==fallback for r in member.roles)))

    async def require_user(request):
        uid = user_id(request)
        if uid is None:
            raise web.HTTPUnauthorized(text="Entre com sua conta Discord.")
        if not bot._api_origin_ok(request):
            raise web.HTTPForbidden(text="Origem não autorizada.")
        return int(uid)

    async def run_options(request):
        uid = await require_user(request)
        games = await bot.db._all("SELECT id,name FROM sl_games ORDER BY name")
        challenges = await bot.db._all("SELECT id,name,game_id,rules FROM sl_challenges ORDER BY name")
        return web.json_response({"games":[dict(x) for x in games],"challenges":[dict(x) for x in challenges]})

    async def run_submit(request):
        uid = await require_user(request)
        try:
            reader = await request.multipart()
            f, proofs = {}, []
            async for part in reader:
                if part.name == "proofs" and part.filename: proofs.append(part)
                else: f[part.name] = (await part.text()).strip()
            gid, cid = int(f.get("game_id","0")), int(f.get("challenge_id","0"))
            seconds = int(f.get("seconds","0"))
            game = await bot.db._one("SELECT id FROM sl_games WHERE id=?", (gid,))
            challenge = await bot.db._one("SELECT id FROM sl_challenges WHERE id=? AND (game_id IS NULL OR game_id=?)", (cid,gid))
            if len(proofs)>5:return web.json_response({"error":"Envie no máximo 5 comprovantes."},status=400)
            if not game or not challenge or seconds < 30 or seconds > 604800 or not proofs:
                return web.json_response({"error":"Selecione jogo e desafio válidos, informe tempo entre 30 segundos e 7 dias e anexe comprovante."},status=400)
            rating = int(f["rating"]) if f.get("rating","").isdigit() else None
            difficulty = int(f["difficulty"]) if f.get("difficulty","").isdigit() else None
            if rating is not None and not 1<=rating<=10 or difficulty is not None and not 1<=difficulty<=5:
                return web.json_response({"error":"Nota deve ser 1–10 e dificuldade 1–5."},status=400)
            cur = await bot.db.conn.execute(
                "INSERT INTO sl_runs(user_id,game_id,challenge_id,build,seconds,rating,difficulty,comment,status) VALUES(?,?,?,?,?,?,?,?,'pending')",
                (uid,gid,cid,f.get("build","")[:300],seconds,rating,difficulty,f.get("comment","")[:500]))
            rid=cur.lastrowid; await bot.db.conn.commit()
            try:
                await ensure_table()
                urls=[]
                for part in proofs[:5]: urls.append(await upload_file(part,uid,"run",rid))
                await bot.db.conn.execute("UPDATE sl_runs SET proof_url=? WHERE id=?", (urls[0],rid))
                await bot.db.conn.commit()
                return web.json_response({"ok":True,"id":rid,"status":"pending"})
            except Exception:
                await bot.db.conn.execute("DELETE FROM sl_runs WHERE id=? AND status='pending'",(rid,)); await bot.db.conn.commit()
                raise
        except (ValueError,TypeError):
            return web.json_response({"error":"Dados inválidos."},status=400)

    async def contributions(request):
        uid = user_id(request)
        gid = guild_id()
        if not gid: return web.json_response({"error":"Servidor não configurado."},status=503)
        status = request.query.get("status")
        owner = int(request.query.get("mine","0") or 0)
        rows = await bot.db.listar_contribuicoes(guild_id=gid,status=status,user_id=uid if owner and uid else None,limit=40)
        return web.json_response({"items":[dict(r) for r in rows]})

    async def contribution_submit(request):
        uid = await require_user(request)
        gid = guild_id()
        data = await request.json()
        kind = str(data.get("kind","guide"))
        allowed = {"lore","guide","run","correction","idea","faq","challenge","game_suggestion"}
        if kind not in allowed: return web.json_response({"error":"Tipo de contribuição inválido."},status=400)
        title=str(data.get("title","")).strip()[:120]
        content=str(data.get("content","")).strip()[:12000]
        if not title or len(content)<20: return web.json_response({"error":"Informe título e conteúdo com pelo menos 20 caracteres."},status=400)
        cid=await bot.db.criar_contribuicao(guild_id=gid,user_id=uid,kind=kind,game_name=str(data.get("game_name",""))[:100],title=title,summary=str(data.get("summary",""))[:500],content=content,sources=str(data.get("sources",""))[:1500],spoiler_level=str(data.get("spoiler_level","none")))
        return web.json_response({"ok":True,"id":cid,"status":"pending"})


    async def challenge_participation(request):
        uid=await require_user(request); data=await request.json()
        cid=int(data.get("contribution_id",0))
        row=await bot.db.get_contribuicao(cid)
        if not row or row["guild_id"]!=guild_id() or row["kind"]!="challenge" or row["status"]!="approved":
            return web.json_response({"error":"Desafio indisponível."},status=404)
        action=str(data.get("action","join"))
        try:
            if action=="join":
                joined=await bot.db.alternar_participacao_desafio(guild_id(),cid,uid)
            else:
                status="completed" if action=="complete" else "in_progress"
                joined=await bot.db.atualizar_progresso_desafio(guild_id(),cid,uid,status,str(data.get("note",""))[:700],str(data.get("evidence",""))[:500])
        except ValueError as exc:return web.json_response({"error":str(exc)},status=400)
        return web.json_response({"ok":bool(joined)})

    async def favorites(request):
        uid=await require_user(request)
        rows=await bot.db.listar_favoritos(guild_id(),uid,50)
        return web.json_response({"items":[dict(r) for r in rows]})

    async def community_interact(request):
        uid=await require_user(request); data=await request.json()
        target_type=str(data.get("target_type","contribution"))
        target_id=int(data.get("target_id",0)); reaction=str(data.get("reaction","like"))
        if target_type not in {"contribution","post"} or reaction not in {"like","useful","respect"} or target_id<=0:
            return web.json_response({"error":"Interação inválida."},status=400)
        if target_type=="contribution":
            target=await bot.db.get_contribuicao(target_id)
            if not target or target["guild_id"]!=guild_id() or target["status"]!="approved":
                return web.json_response({"error":"Publicação indisponível."},status=404)
        added=await bot.db.alternar_interacao(guild_id(),target_type,target_id,uid,reaction)
        counts=await bot.db.contar_interacoes(guild_id(),target_type,target_id)
        return web.json_response({"added":added,"counts":counts})

    async def community_bookmark(request):
        uid=await require_user(request); data=await request.json()
        target_type=str(data.get("target_type","contribution")); target_id=int(data.get("target_id",0))
        if target_type not in {"contribution","post"} or target_id<=0: return web.json_response({"error":"Favorito inválido."},status=400)
        if target_type=="contribution":
            target=await bot.db.get_contribuicao(target_id)
            if not target or target["guild_id"]!=guild_id() or target["status"]!="approved":
                return web.json_response({"error":"Publicação indisponível."},status=404)
        added=await bot.db.alternar_favorito(guild_id(),uid,target_type,target_id)
        return web.json_response({"saved":added})

    async def community_follow(request):
        uid=await require_user(request); data=await request.json(); target=int(data.get("user_id",0))
        try: following=await bot.db.alternar_seguir(guild_id(),uid,target)
        except ValueError as exc: return web.json_response({"error":str(exc)},status=400)
        return web.json_response({"following":following})

    async def guestbook(request):
        uid=await require_user(request); owner=int(request.match_info["user_id"])
        if request.method=="GET":
            rows=await bot.db.listar_mensagens_santuario(guild_id(),owner,25)
            return web.json_response({"messages":[dict(r) for r in rows]})
        if request.method=="DELETE":
            if uid!=owner:return web.json_response({"error":"Somente o dono pode apagar mensagens."},status=403)
            mid=int(request.query.get("id","0"))
            ok=await bot.db.apagar_mensagem_santuario(guild_id(),owner,mid)
            return web.json_response({"ok":ok},status=200 if ok else 404)
        data=await request.json(); message=str(data.get("message","")).strip()
        if not message or len(message)>300: return web.json_response({"error":"Mensagem deve ter entre 1 e 300 caracteres."},status=400)
        try: mid=await bot.db.criar_mensagem_santuario(guild_id(),owner,uid,message)
        except ValueError as exc: return web.json_response({"error":str(exc)},status=400)
        if mid is None: return web.json_response({"error":"Você já deixou uma mensagem para este santuário nas últimas 24 horas."},status=429)
        return web.json_response({"ok":True,"id":mid})

    async def notifications(request):
        uid=await require_user(request); gid=guild_id()
        if request.method=="GET":
            rows=await bot.db.listar_notificacoes_pendentes(gid,uid,25)
            prefs=await bot.db.get_preferencias_notificacao(gid,uid)
            return web.json_response({"items":[dict(r) for r in rows],"preferences":prefs})
        data=await request.json()
        if data.get("action")=="read_all":
            n=await bot.db.marcar_notificacoes_lidas(gid,uid); return web.json_response({"marked":n})
        key=str(data.get("key","")); await bot.db.definir_preferencia_notificacao(gid,uid,key,bool(data.get("enabled")))
        return web.json_response({"ok":True})

    async def profile(request):
        uid=await require_user(request)
        await bot.db.conn.execute("CREATE TABLE IF NOT EXISTS site_profile_web(user_id INTEGER PRIMARY KEY,tagline TEXT NOT NULL DEFAULT '',bio TEXT NOT NULL DEFAULT '',fav_game TEXT NOT NULL DEFAULT '',theme TEXT NOT NULL DEFAULT 'Ouro',links TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        await bot.db.conn.commit()
        if request.method=="GET":
            row=await bot.db._one("SELECT * FROM site_profile_web WHERE user_id=?",(uid,))
            if row is None: row=await bot.db.get_perfil(uid)
            return web.json_response({"profile":dict(row) if row else {}})
        data=await request.json()
        fields={"tagline":str(data.get("tagline",""))[:100],"bio":str(data.get("bio",""))[:1000],"fav_game":str(data.get("fav_game",""))[:100],"theme":str(data.get("theme","Ouro"))[:30]}
        links=data.get("links",{})
        if not isinstance(links,dict): return web.json_response({"error":"Links inválidos."},status=400)
        fields["links"]=json.dumps({str(k)[:20]:str(v)[:250] for k,v in links.items() if str(v).startswith(("https://","http://"))},ensure_ascii=False)
        await bot.db.conn.execute("""INSERT INTO site_profile_web(user_id,tagline,bio,fav_game,theme,links) VALUES(?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET tagline=excluded.tagline,bio=excluded.bio,fav_game=excluded.fav_game,theme=excluded.theme,links=excluded.links,updated_at=CURRENT_TIMESTAMP""",
            (uid,fields["tagline"],fields["bio"],fields["fav_game"],fields["theme"],fields["links"]))
        await bot.db.conn.commit()
        row=await bot.db.get_perfil(uid)
        if row: await bot.db.atualizar_perfil(uid,**fields)
        return web.json_response({"ok":True})


    async def cancel_submission(request):
        uid=await require_user(request)
        kind=request.match_info["kind"]; sid=int(request.match_info["item_id"])
        if kind=="platina":
            row=await bot.db._one("SELECT user_id,status FROM platinas WHERE id=?",(sid,))
            if not row or int(row["user_id"])!=uid:return web.json_response({"error":"Registro não encontrado."},status=404)
            if row["status"]!="pending":return web.json_response({"error":"Somente registros pendentes podem ser cancelados."},status=409)
            await bot.db.excluir_platina_pendente(sid)
        elif kind=="zerado":
            cur=await bot.db.conn.execute("DELETE FROM zerados WHERE id=? AND user_id=? AND status='pending'",(sid,uid));await bot.db.conn.commit()
            if not cur.rowcount:return web.json_response({"error":"Registro não encontrado ou já processado."},status=409)
        elif kind=="run":
            cur=await bot.db.conn.execute("DELETE FROM sl_runs WHERE id=? AND user_id=? AND status='pending'",(sid,uid));await bot.db.conn.commit()
            if not cur.rowcount:return web.json_response({"error":"Registro não encontrado ou já processado."},status=409)
        else:return web.json_response({"error":"Categoria inválida."},status=400)
        await bot.db.conn.execute("DELETE FROM site_submission_proofs WHERE kind=? AND submission_id=? AND user_id=?",(kind,sid,uid));await bot.db.conn.commit()
        return web.json_response({"ok":True})


    async def admin_config(request):
        uid=await require_user(request)
        if not await is_moderator(uid):return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        import admin_config
        gid=guild_id()
        if request.method=="GET":
            result=[]
            for key,(attr,cast) in admin_config.KEYS.items():
                value=await admin_config.GuildConfig.get(bot.db,gid,key)
                result.append({"key":key,"label":admin_config.LABELS.get(key,key),"value":value if value is not None else ""})
            return web.json_response({"settings":result})
        data=await request.json(); key=str(data.get("key",""))
        if key not in admin_config.KEYS:return web.json_response({"error":"Configuração não permitida."},status=400)
        cast=admin_config.KEYS[key][1]
        try:
            value=cast(data.get("value",""))
            if cast is int and value<0:return web.json_response({"error":"IDs e valores não podem ser negativos."},status=400)
            await admin_config.GuildConfig.set(bot.db,gid,key,value)
        except (ValueError,TypeError):return web.json_response({"error":"Valor inválido para esta configuração."},status=400)
        return web.json_response({"ok":True})

    async def admin_queue(request):
        uid=await require_user(request)
        await ensure_table()
        if not await is_moderator(uid): return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        plats=[dict(x) for x in await bot.db._all("SELECT id,user_id,game,platform,earned_at AS date,created_at,'platina' AS kind FROM platinas WHERE status='pending' ORDER BY id LIMIT 100")]
        zeros=[dict(x) for x in await bot.db._all("SELECT id,user_id,game,platform,finished_at AS date,created_at,'zerado' AS kind FROM zerados WHERE status='pending' ORDER BY id LIMIT 100")]
        runs=[dict(x) for x in await bot.db._all("SELECT r.id,r.user_id,g.name AS game,c.name AS challenge,r.seconds,r.build,r.comment,r.proof_url,r.created_at,'run' AS kind FROM sl_runs r JOIN sl_games g ON g.id=r.game_id JOIN sl_challenges c ON c.id=r.challenge_id WHERE r.status='pending' ORDER BY r.id LIMIT 100")]
        contrib=[dict(x) for x in await bot.db.listar_contribuicoes(guild_id=guild_id(),status="pending",limit=100)]
        for item in plats+zeros:
            site_proofs=[dict(p) for p in await bot.db._all("SELECT url,filename FROM site_submission_proofs WHERE kind=? AND submission_id=? ORDER BY id", (item["kind"],item["id"]))]
            legacy_proofs=[]
            if item["kind"]=="platina":
                legacy_proofs=[{"url":p["proof_url"],"filename":"Comprovante do Discord"} for p in await bot.db._all("SELECT proof_url FROM platina_proofs WHERE platina_id=?",(item["id"],))]
            item["proofs"]=site_proofs+legacy_proofs
            if item["kind"]=="platina" and item.get("game"):
                row=await bot.db._one("SELECT proof_url FROM platinas WHERE id=?",(item["id"],))
                if row and row["proof_url"] and not row["proof_url"].startswith("site://"):
                    item["proofs"].append({"url":row["proof_url"],"filename":"Comprovante principal"})
        catalog_pending=[]
        conn=catalog_db()
        try:
            for row in conn.execute("SELECT id,nome AS game,plataforma AS platform,autor_id,'ports' AS kind,'ports' AS queue_kind FROM jogos WHERE status='pendente' LIMIT 100").fetchall(): catalog_pending.append(dict(row))
            for row in conn.execute("SELECT id,jogo_nome AS game,mod_nome AS name,autor_id,'mods' AS kind,'mods' AS queue_kind FROM mods WHERE status='pendente' LIMIT 100").fetchall(): catalog_pending.append(dict(row))
        finally: conn.close()
        return web.json_response({"items":list(plats)+list(zeros)+list(runs)+list(contrib)+catalog_pending})

    async def admin_decide(request):
        uid=await require_user(request)
        if not await is_moderator(uid): return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        data=await request.json(); kind=request.match_info["kind"]; item_id=int(request.match_info["item_id"])
        action=str(data.get("action","")); note=str(data.get("note",""))[:300]
        owner_row=None; title="seu registro"
        if kind=="platina": owner_row=await bot.db._one("SELECT user_id,game AS title FROM platinas WHERE id=?",(item_id,))
        elif kind=="zerado": owner_row=await bot.db._one("SELECT user_id,game AS title FROM zerados WHERE id=?",(item_id,))
        elif kind=="run": owner_row=await bot.db._one("SELECT r.user_id,g.name AS title FROM sl_runs r JOIN sl_games g ON g.id=r.game_id WHERE r.id=?",(item_id,))
        elif kind=="contribution": owner_row=await bot.db._one("SELECT user_id,title FROM community_contributions WHERE id=?",(item_id,))
        if owner_row: title=str(owner_row["title"] or title)
        if action not in {"approved","rejected","changes_requested"}: return web.json_response({"error":"Decisão inválida."},status=400)
        if kind=="platina":
            if action=="approved":
                import config
                result=await bot.db.aprovar_platina_com_recompensa(item_id,uid,config.XP_PLATINA,config.DENARIOS_PLATINA,config.XP_ZERADO,config.DENARIOS_ZERADO,config.ZERADOS_XP_LIMITE_DIARIO)
            else: result=await bot.db.decidir_platina(item_id,"rejected",uid,note)
        elif kind=="zerado":
            if action=="approved":
                import config
                result=await bot.db.aprovar_zerado_com_recompensa(item_id,uid,config.XP_ZERADO,config.DENARIOS_ZERADO,config.ZERADOS_XP_LIMITE_DIARIO)
            else: result=await bot.db.rejeitar_zerado(item_id,uid,note)
        elif kind=="run":
            if action=="approved": result=await bot.db.aprovar_run_com_recompensa(item_id,uid)
            else:
                cur=await bot.db.conn.execute("UPDATE sl_runs SET status='rejected',reviewer_id=?,reject_reason=? WHERE id=? AND status='pending'",(uid,note,item_id)); await bot.db.conn.commit(); result=cur.rowcount==1
        elif kind=="contribution":
            result=await bot.db.decidir_contribuicao(item_id,uid,action,note)
        else: return web.json_response({"error":"Categoria não suportada."},status=400)
        if not result: return web.json_response({"error":"Registro já processado ou inexistente."},status=409)
        if owner_row:
            category="approvals" if action=="approved" else "rejections"
            status_text="aprovado" if action=="approved" else ("precisa de ajustes" if action=="changes_requested" else "rejeitado")
            await bot.db.registrar_notificacao_pendente(guild_id(),int(owner_row["user_id"]),category,
                f"Seu envio “{title}” foi {status_text} pela equipe. {note}".strip(),
                f"portal-{kind}-{item_id}-{action}")
        return web.json_response({"ok":True})



    def catalog_db():
        import sqlite3, config
        path=os.path.abspath(os.getenv("CATALOGO_DATA_DIR") or str(config.DATA_DIR))
        conn=sqlite3.connect(os.path.join(path,"jogos.db")); conn.row_factory=sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS jogos (id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,plataforma TEXT NOT NULL,descricao TEXT,link TEXT NOT NULL,tutorial TEXT,capa TEXT,iso TEXT,status TEXT NOT NULL DEFAULT 'aprovado',autor_id INTEGER,outros_links TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS mods (id INTEGER PRIMARY KEY AUTOINCREMENT,jogo_nome TEXT NOT NULL,mod_nome TEXT NOT NULL,descricao TEXT,imagem TEXT,link TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'aprovado',autor_id INTEGER,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        # Compatibilidade com bancos antigos que ainda não possuem links extras.
        columns = {r[1] for r in conn.execute("PRAGMA table_info(jogos)")}
        if "outros_links" not in columns:
            conn.execute("ALTER TABLE jogos ADD COLUMN outros_links TEXT")
        conn.commit()
        return conn

    async def catalog_image(request):
        """Entrega capas locais do catálogo sem expor caminhos internos do servidor."""
        import config
        kind = request.match_info["kind"]
        try:
            item_id = int(request.match_info["item_id"])
        except (TypeError, ValueError):
            raise web.HTTPNotFound()
        if kind not in {"ports", "mods"}:
            raise web.HTTPNotFound()

        conn = catalog_db()
        try:
            table, column = ("jogos", "capa") if kind == "ports" else ("mods", "imagem")
            row = conn.execute(
                f"SELECT {column} AS image FROM {table} WHERE id=? AND status='aprovado'",
                (item_id,)
            ).fetchone()
            if not row or not row["image"]:
                raise web.HTTPNotFound()
            raw = str(row["image"]).strip()
        finally:
            conn.close()

        if raw.startswith(("https://", "http://")):
            raise web.HTTPFound(raw)

        data_root = Path(os.path.abspath(os.getenv("CATALOGO_DATA_DIR") or str(config.DATA_DIR))).resolve()
        allowed_dirs = [(data_root / "capas").resolve(), (data_root / "capas_mods").resolve()]
        candidates = [Path(raw)] if os.path.isabs(raw) else [
            data_root / raw,
            data_root / ("capas" if kind == "ports" else "capas_mods") / raw
        ]
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
                if not resolved.is_file() or not any(
                    resolved == folder or folder in resolved.parents for folder in allowed_dirs
                ):
                    continue
                return web.FileResponse(
                    resolved,
                    headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"}
                )
            except (OSError, RuntimeError):
                continue
        raise web.HTTPNotFound()

    async def catalog_list(request):
        # Lista todos os registros aprovados; sem LIMIT fixo que esconda parte do catálogo.
        kind=request.query.get("kind","ports")
        q=request.query.get("q","").strip()[:100]
        if kind not in {"ports","mods"}: return web.json_response({"error":"Categoria inválida."},status=400)
        conn=catalog_db()
        try:
            if kind=="ports":
                rows=conn.execute(
                    """SELECT id,nome AS name,plataforma AS platform,descricao AS description,
                       link,tutorial,iso,outros_links,capa AS image,status
                       FROM jogos WHERE status='aprovado'
                       AND (nome LIKE ? OR plataforma LIKE ? OR descricao LIKE ?) ORDER BY nome""",
                    (f"%{q}%",f"%{q}%",f"%{q}%")
                ).fetchall()
            else:
                rows=conn.execute(
                    """SELECT id,jogo_nome AS game,mod_nome AS name,descricao AS description,
                       link,imagem AS image,status FROM mods WHERE status='aprovado'
                       AND (jogo_nome LIKE ? OR mod_nome LIKE ? OR descricao LIKE ?)
                       ORDER BY jogo_nome,mod_nome""",
                    (f"%{q}%",f"%{q}%",f"%{q}%")
                ).fetchall()

            items=[]
            for row in rows:
                item=dict(row)
                item["image_url"] = f"/api/portal/catalog/image/{kind}/{item['id']}" if item.get("image") else ""
                if kind=="ports":
                    try:
                        extras=json.loads(item.pop("outros_links", None) or "[]")
                        item["other_links"]=[
                            {
                                "name": str(x.get("nome") or x.get("name") or "Link adicional")[:80],
                                "url": str(x.get("url") or x.get("link") or "")[:1000]
                            }
                            for x in extras
                            if isinstance(x,dict) and str(x.get("url") or x.get("link") or "").startswith(("http://","https://"))
                        ]
                    except (TypeError, ValueError):
                        item["other_links"]=[]
                items.append(item)
            return web.json_response({"items":items}, headers={"Cache-Control":"no-store"})
        finally:
            conn.close()

    async def catalog_submit(request):
        uid=await require_user(request)
        kind=request.match_info["kind"]
        if kind not in {"ports","mods"}: return web.json_response({"error":"Categoria inválida."},status=400)
        data=await request.json()
        game=str(data.get("game","")).strip()[:100]
        name=str(data.get("name","")).strip()[:120]
        link=str(data.get("link","")).strip()[:500]
        desc=str(data.get("description","")).strip()[:1000]
        if not game or not name or not link.startswith(("https://","http://")):
            return web.json_response({"error":"Preencha jogo, nome e um link HTTP/HTTPS válido."},status=400)
        conn=catalog_db()
        try:
            table="jogos" if kind=="ports" else "mods"
            pending=conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE autor_id=? AND status='pendente'",(uid,)).fetchone()["n"]
            if int(pending)>=3:return web.json_response({"error":"Você já possui três sugestões pendentes nesta categoria."},status=429)
            duplicate=conn.execute(f"SELECT 1 FROM {table} WHERE autor_id=? AND lower({ 'nome' if kind=='ports' else 'mod_nome' })=lower(?) AND status IN ('pendente','aprovado') LIMIT 1",(uid,name)).fetchone()
            if duplicate:return web.json_response({"error":"Você já enviou uma sugestão semelhante."},status=409)
            if kind=="ports":
                conn.execute("INSERT INTO jogos(nome,plataforma,descricao,link,tutorial,status,autor_id) VALUES(?,?,?,?,?,'pendente',?)",
                    (game,str(data.get("platform","Outra"))[:40],desc,link,str(data.get("tutorial",""))[:500],uid))
            else:
                conn.execute("INSERT INTO mods(jogo_nome,mod_nome,descricao,link,status,autor_id) VALUES(?,?,?,?,'pendente',?)",
                    (game,name,desc,link,uid))
            conn.commit()
            return web.json_response({"ok":True,"status":"pending"})
        except Exception:
            return web.json_response({"error":"Não foi possível registrar a sugestão."},status=500)
        finally: conn.close()


    async def store_data(request):
        uid=await require_user(request)
        import loja
        inv=await bot.db.inventario_do_usuario(uid); own={x["item"]:dict(x) for x in inv}
        user=await bot.db.get_user(uid)
        items=[]
        for item in loja.ITENS:
            row=own.get(item.id,{})
            items.append({"id":item.id,"type":item.tipo,"name":item.nome,"price":item.preco,"emoji":item.emoji,"description":item.descricao,"min_level":item.nivel_min,"owned":bool(row),"equipped":bool(row.get("equipado",0))})
        return web.json_response({"balance":int(user["denarios"] or 0) if user else 0,"items":items,"inventory":[dict(x) for x in inv]})

    async def store_action(request):
        uid=await require_user(request); data=await request.json()
        import loja
        item=loja.POR_ID.get(str(data.get("item","")))
        if not item:return web.json_response({"error":"Item inexistente."},status=404)
        action=str(data.get("action",""))
        if action=="buy":
            import levels
            user=await bot.db.get_user(uid)
            nivel=levels.nivel_por_xp(int(user["xp"] or 0) if user else 0)
            if nivel < item.nivel_min:return web.json_response({"error":f"Este item exige nível {item.nivel_min}."},status=403)
            result=await bot.db.comprar_item(uid,item.id,item.tipo,item.preco)
            if result!="ok":
                msg={"ja_tem":"Você já possui esse item.","sem_saldo":"Denários insuficientes."}.get(result,"Compra não realizada.")
                return web.json_response({"error":msg},status=409)
        elif action=="equip":
            ok=await bot.db.equipar_item(uid,item.id,item.tipo)
            if not ok:return web.json_response({"error":"Você não possui esse item."},status=403)
        elif action=="unequip":
            await bot.db.desequipar_tipo(uid,item.tipo)
        else:return web.json_response({"error":"Ação inválida."},status=400)
        return web.json_response({"ok":True})

    async def catalog_admin_decide(request):
        uid=await require_user(request)
        if not await is_moderator(uid):return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        kind=request.match_info["kind"]; item_id=int(request.match_info["item_id"]); data=await request.json()
        if kind not in {"ports","mods"}:return web.json_response({"error":"Categoria inválida."},status=400)
        status="aprovado" if data.get("action")=="approved" else "rejeitado"
        conn=catalog_db()
        try:
            table="jogos" if kind=="ports" else "mods"
            row=conn.execute(f"SELECT autor_id, {'nome' if kind=='ports' else 'mod_nome'} AS title FROM {table} WHERE id=?",(item_id,)).fetchone()
            cur=conn.execute(f"UPDATE {table} SET status=? WHERE id=? AND status='pendente'",(status,item_id))
            conn.commit()
            if not cur.rowcount:return web.json_response({"error":"Sugestão inexistente ou já revisada."},status=409)
            if row and row["autor_id"]:
                await bot.db.registrar_notificacao_pendente(guild_id(),int(row["autor_id"]),"approvals" if status=="aprovado" else "rejections",
                    f"Sua sugestão “{row['title']}” foi {'aprovada' if status=='aprovado' else 'rejeitada'} pela equipe.",f"portal-{kind}-{item_id}-{status}")
            return web.json_response({"ok":True})
        finally:conn.close()



    def news_connection():
        import sqlite3
        from cogs.catalogo_integrado import DB_PATH
        conn=sqlite3.connect(DB_PATH)
        conn.row_factory=sqlite3.Row
        conn.execute("CREATE TABLE IF NOT EXISTS news_feeds (id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT NOT NULL,url TEXT NOT NULL UNIQUE,ativo INTEGER NOT NULL DEFAULT 1,inicializado INTEGER NOT NULL DEFAULT 0,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS news_seen (item_key TEXT PRIMARY KEY,feed_id INTEGER NOT NULL,visto_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS news_config (chave TEXT PRIMARY KEY,valor TEXT)")
        conn.commit()
        return conn

    async def admin_news(request):
        uid=await require_user(request)
        if not await is_moderator(uid):
            return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        cog=bot.get_cog("GameNewsCog")
        conn=news_connection()
        try:
            if request.method=="GET":
                feeds=[dict(r) for r in conn.execute("SELECT id,nome,url,ativo,inicializado FROM news_feeds ORDER BY id").fetchall()]
                row=conn.execute("SELECT valor FROM news_config WHERE chave='channel_id'").fetchone()
                channel_id=row["valor"] if row else None
                return web.json_response({"feeds":feeds,"channel_id":channel_id or ""})
            data=await request.json()
            action=str(data.get("action",""))
            if action=="add":
                name=str(data.get("name","")).strip()[:80]
                url=str(data.get("url","")).strip()
                if len(name)<2 or not url.startswith("https://") or len(url)>500:
                    return web.json_response({"error":"Informe nome (2–80 caracteres) e URL HTTPS válida."},status=400)
                if cog is None:
                    return web.json_response({"error":"Monitor RSS não está carregado."},status=503)
                try:
                    if cog._session is None or cog._session.closed:
                        import aiohttp
                        cog._session=aiohttp.ClientSession()
                    items=await cog._fetch_feed(cog._session,url)
                    if not items:
                        return web.json_response({"error":"O endereço não retornou itens RSS/Atom válidos."},status=400)
                    cur=conn.execute("INSERT INTO news_feeds(nome,url) VALUES(?,?)",(name,url))
                    feed_id=cur.lastrowid
                    conn.executemany("INSERT OR IGNORE INTO news_seen(item_key,feed_id) VALUES(?,?)",[(item["key"],feed_id) for item in items])
                    conn.execute("UPDATE news_feeds SET inicializado=1 WHERE id=?",(feed_id,))
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    return web.json_response({"error":f"Não foi possível validar/adicionar o feed: {str(exc)[:180]}"},status=400)
                return web.json_response({"ok":True,"id":feed_id})
            if action=="remove":
                feed_id=int(data.get("id",0))
                cur=conn.execute("DELETE FROM news_feeds WHERE id=?",(feed_id,))
                conn.execute("DELETE FROM news_seen WHERE feed_id=?",(feed_id,))
                conn.commit()
                if not cur.rowcount:return web.json_response({"error":"Feed não encontrado."},status=404)
                return web.json_response({"ok":True})
            if action=="channel":
                raw_channel=str(data.get("channel_id","")).strip()
                try: channel_id=int(raw_channel) if raw_channel else 0
                except ValueError: return web.json_response({"error":"Informe um ID numérico de canal."},status=400)
                if channel_id < 0: return web.json_response({"error":"ID de canal inválido."},status=400)
                if channel_id:
                    channel=bot.get_channel(channel_id)
                    if channel is None:
                        try: channel=await bot.fetch_channel(channel_id)
                        except Exception:return web.json_response({"error":"Não foi possível acessar esse canal."},status=400)
                    if not hasattr(channel,"send"):
                        return web.json_response({"error":"O ID informado não é um canal de texto compatível."},status=400)
                conn.execute("INSERT INTO news_config(chave,valor) VALUES('channel_id',?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",(str(channel_id) if channel_id else "",))
                conn.commit()
                return web.json_response({"ok":True})
            return web.json_response({"error":"Ação inválida."},status=400)
        finally:
            conn.close()

    async def nara_chat(request):
        uid=await require_user(request)
        data=await request.json()
        message_text=str(data.get("message","")).strip()[:4000]
        if not message_text:return web.json_response({"error":"Escreva uma mensagem."},status=400)
        cog=bot.get_cog("NaraIA")
        if cog is None:return web.json_response({"error":"O módulo NARA IA não está carregado."},status=503)
        guild=bot.get_guild(guild_id())
        if guild is None:return web.json_response({"error":"Servidor indisponível."},status=503)
        author=guild.get_member(uid)
        if author is None:
            try: author=await bot.fetch_user(uid)
            except Exception:return web.json_response({"error":"Não foi possível identificar sua conta Discord."},status=404)
        import config
        channel=bot.get_channel(int(getattr(config,"NARA_CHANNEL_ID",0) or 0)) if getattr(config,"NARA_CHANNEL_ID",0) else None
        channel=channel or guild.system_channel
        if channel is None:
            channel=type("WebChannel",(),{"id":0})()
        from types import SimpleNamespace
        message=SimpleNamespace(author=author,guild=guild,channel=channel,attachments=[],reference=None)
        try:
            reply=await cog._conversar(message,message_text)
            return web.json_response({"reply":str(reply or "Não consegui responder agora.")})
        except Exception:
            return web.json_response({"error":"A NARA não conseguiu responder neste momento."},status=503)

    async def nara_memory(request):
        uid=await require_user(request); gid=guild_id()
        await bot.db.conn.execute("""CREATE TABLE IF NOT EXISTS nara_memoria_privacidade(guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL,PRIMARY KEY(guild_id,user_id))""")
        await bot.db.conn.execute("""CREATE TABLE IF NOT EXISTS nara_memoria(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)""")
        await bot.db.conn.execute("""CREATE TABLE IF NOT EXISTS nara_social_perfil(guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,interacoes INTEGER NOT NULL DEFAULT 0,afinidade REAL NOT NULL DEFAULT 0,intimidade REAL NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL,PRIMARY KEY(guild_id,user_id))""")
        await bot.db.conn.execute("""CREATE TABLE IF NOT EXISTS nara_relacionamento_perfil(guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,afinidade REAL NOT NULL DEFAULT 5.0,paciencia REAL NOT NULL DEFAULT 5.0,updated_at INTEGER NOT NULL,recovered_at INTEGER NOT NULL,PRIMARY KEY(guild_id,user_id))""")
        await bot.db.conn.execute("""CREATE TABLE IF NOT EXISTS nara_relacionamento_eventos(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER NOT NULL,user_id INTEGER NOT NULL,event_type TEXT NOT NULL,summary TEXT NOT NULL,afinidade_delta REAL NOT NULL DEFAULT 0,paciencia_delta REAL NOT NULL DEFAULT 0,created_at INTEGER NOT NULL)""")
        await bot.db.conn.commit()
        if request.method=="GET":
            row=await bot.db._one("SELECT enabled FROM nara_memoria_privacidade WHERE guild_id=? AND user_id=?",(gid,uid))
            count=await bot.db._one("SELECT COUNT(*) AS n FROM nara_memoria WHERE guild_id=? AND user_id=?",(gid,uid))
            return web.json_response({"enabled":bool(row and row["enabled"]),"messages":int(count["n"] or 0)})
        data=await request.json(); action=str(data.get("action",""))
        import time
        if action in {"enable","disable"}:
            await bot.db.conn.execute("""INSERT INTO nara_memoria_privacidade(guild_id,user_id,enabled,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at""",(gid,uid,1 if action=="enable" else 0,int(time.time())))
        elif action=="delete":
            await bot.db.conn.execute("DELETE FROM nara_memoria WHERE guild_id=? AND user_id=?",(gid,uid))
            await bot.db.conn.execute("DELETE FROM nara_social_perfil WHERE guild_id=? AND user_id=?",(gid,uid))
            await bot.db.conn.execute("DELETE FROM nara_relacionamento_perfil WHERE guild_id=? AND user_id=?",(gid,uid))
            await bot.db.conn.execute("DELETE FROM nara_relacionamento_eventos WHERE guild_id=? AND user_id=?",(gid,uid))
        else:return web.json_response({"error":"Ação inválida."},status=400)
        await bot.db.conn.commit()
        return web.json_response({"ok":True})

    async def sanctuary(request):
        viewer=await require_user(request)
        target=int(request.match_info["user_id"])
        await bot.db.conn.execute("CREATE TABLE IF NOT EXISTS site_profile_web(user_id INTEGER PRIMARY KEY,tagline TEXT NOT NULL DEFAULT '',bio TEXT NOT NULL DEFAULT '',fav_game TEXT NOT NULL DEFAULT '',theme TEXT NOT NULL DEFAULT 'Ouro',links TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        await bot.db.conn.commit()
        profile=await bot.db.get_perfil(target)
        if profile is None: profile=await bot.db._one("SELECT * FROM site_profile_web WHERE user_id=?",(target,))
        if not profile:return web.json_response({"error":"Este jogador ainda não possui santuário."},status=404)
        summary=await bot.db.resumo_painel_nara(target)
        honors=await bot.db.contar_honras(guild_id(),target)
        followers=await bot.db.contar_seguidores(guild_id(),target)
        messages=await bot.db.listar_mensagens_santuario(guild_id(),target,20)
        return web.json_response({"profile":dict(profile),"summary":dict(summary),"honors":honors,"followers":followers,"messages":[dict(m) for m in messages],"is_owner":viewer==target})

    async def honor(request):
        uid=await require_user(request); data=await request.json()
        target=int(data.get("user_id",0)); key=str(data.get("honor_key",""))
        await bot.db.conn.execute("CREATE TABLE IF NOT EXISTS site_profile_web(user_id INTEGER PRIMARY KEY,tagline TEXT NOT NULL DEFAULT '',bio TEXT NOT NULL DEFAULT '',fav_game TEXT NOT NULL DEFAULT '',theme TEXT NOT NULL DEFAULT 'Ouro',links TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        await bot.db.conn.commit()
        target_profile=await bot.db.get_perfil(target)
        if target_profile is None:
            target_profile=await bot.db._one("SELECT user_id FROM site_profile_web WHERE user_id=?",(target,))
        if target_profile is None:return web.json_response({"error":"O jogador ainda não possui santuário."},status=404)
        if key not in {"respect","determination","greatness"}:return web.json_response({"error":"Honra inválida."},status=400)
        from datetime import datetime, timezone
        week=datetime.now(timezone.utc).strftime("%G-W%V")
        try: result=await bot.db.registrar_honra(guild_id(),uid,target,key,week)
        except ValueError as exc:return web.json_response({"error":str(exc)},status=400)
        return web.json_response({"result":result})



    async def admin_roles(request):
        uid=await require_user(request)
        if not await is_moderator(uid):
            return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        gid=guild_id(); guild=bot.get_guild(gid) if gid else None
        if guild is None:return web.json_response({"error":"Servidor Discord indisponível."},status=503)
        key=f"portal:self_roles:{gid}"
        if request.method=="GET":
            raw=await bot.db.get_kv(key)
            try: ids=[int(x) for x in json.loads(raw or "[]")]
            except (TypeError,ValueError): ids=[]
            roles=[{"id":r.id,"name":r.name,"position":r.position,"managed":r.managed} for r in guild.roles if r.id in ids]
            available=[{"id":r.id,"name":r.name,"position":r.position,"managed":r.managed} for r in guild.roles if r.id!=guild.id and not r.managed]
            return web.json_response({"roles":roles,"available":available})
        data=await request.json()
        if data.get("action")!="save":return web.json_response({"error":"Ação inválida."},status=400)
        ids=data.get("role_ids",[])
        if not isinstance(ids,list) or len(ids)>25:return web.json_response({"error":"Selecione até 25 cargos."},status=400)
        try: ids=list(dict.fromkeys(int(x) for x in ids))
        except (TypeError,ValueError):return web.json_response({"error":"IDs de cargos inválidos."},status=400)
        bot_member=guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            return web.json_response({"error":"O bot precisa da permissão Gerenciar Cargos."},status=409)
        selected=[]
        for rid in ids:
            role=guild.get_role(rid)
            if role is None or role.is_default() or role.managed or role >= bot_member.top_role:
                return web.json_response({"error":f"O cargo {rid} não existe, é gerenciado ou está acima da hierarquia do bot."},status=400)
            selected.append(rid)
        await bot.db.set_kv(key,json.dumps(selected))
        return web.json_response({"ok":True,"role_ids":selected})

    async def admin_panels(request):
        uid=await require_user(request)
        if not await is_moderator(uid):
            return web.json_response({"error":"Acesso restrito à moderação."},status=403)
        gid=guild_id(); guild=bot.get_guild(gid) if gid else None
        if guild is None:return web.json_response({"error":"Servidor Discord indisponível."},status=503)
        if request.method=="GET":
            channels=[{"id":c.id,"name":c.name} for c in guild.text_channels]
            return web.json_response({"channels":channels})
        data=await request.json()
        kind=str(data.get("kind",""))
        try: channel_id=int(data.get("channel_id",0))
        except (TypeError,ValueError):return web.json_response({"error":"ID de canal inválido."},status=400)
        channel=guild.get_channel(channel_id)
        if channel is None or not hasattr(channel,"send"):
            return web.json_response({"error":"Canal de texto não encontrado neste servidor."},status=400)
        me=guild.me
        perms=channel.permissions_for(me) if me else None
        if not perms or not perms.send_messages or not perms.embed_links:
            return web.json_response({"error":"O bot precisa de Enviar Mensagens e Inserir Links nesse canal."},status=403)
        try:
            if kind=="self_roles":
                raw=await bot.db.get_kv(f"portal:self_roles:{gid}")
                try: ids=[int(x) for x in json.loads(raw or "[]")]
                except (TypeError,ValueError): ids=[]
                if not ids:return web.json_response({"error":"Configure ao menos um cargo selecionável antes de publicar."},status=409)
                roles=[guild.get_role(x) for x in ids]
                roles=[r for r in roles if r and not r.managed and r < me.top_role]
                if not roles:return web.json_response({"error":"Nenhum cargo configurado está abaixo do cargo do bot."},status=409)
                import discord
                from cogs.portal_role_panel import SelfRolePanelView
                embed=discord.Embed(title="Cargos da comunidade",description="Selecione os cargos que deseja receber. Você pode alterar suas escolhas quando quiser.",color=0xC49A52)
                embed.add_field(name="Disponíveis",value="\\n".join(f"• {r.name}" for r in roles)[:1024],inline=False)
                view=SelfRolePanelView(bot,roles)
                key=f"panel:self_roles:{gid}:{channel.id}"
            elif kind in {"platinas","zerados"}:
                import discord
                cog=bot.get_cog("Platinas" if kind=="platinas" else "Zerados")
                if cog is None:return web.json_response({"error":f"Módulo {kind} não está carregado."},status=503)
                if kind=="platinas":
                    from cogs.platinas import PainelPublicoView
                    view=PainelPublicoView(cog)
                    content="🏆 **NARA — PLATINAS**\\nRegistre suas conquistas e consulte suas platinas. Abra seu painel pessoal no botão abaixo."
                else:
                    from cogs.zerados import ZeradosPublicoView
                    view=ZeradosPublicoView(cog)
                    content="✅ **NARA — JOGOS ZERADOS**\\nRegistre jogos finalizados e acompanhe seu histórico e ranking."
                embed=None
                key=f"panel:{kind}:{gid}:{channel.id}"
            else:
                return web.json_response({"error":"Tipo de painel não suportado."},status=400)
            old_id=await bot.db.get_kv(key)
            message=None
            if old_id:
                try: message=await channel.fetch_message(int(old_id))
                except Exception: message=None
            if message:
                await message.edit(content=content if kind!="self_roles" else None,embed=embed,view=view)
            else:
                message=await channel.send(content=content if kind!="self_roles" else None,embed=embed,view=view,allowed_mentions=discord.AllowedMentions.none())
            await bot.db.set_kv(key,str(message.id))
            return web.json_response({"ok":True,"message_id":message.id,"channel_id":channel.id,"updated":bool(old_id)})
        except Exception:
            import logging
            logging.getLogger("site_portal").exception("Falha ao publicar painel %s",kind)
            return web.json_response({"error":"Não foi possível publicar o painel. Verifique permissões e logs do bot."},status=500)

    app.router.add_route("*", "/api/portal/admin/roles", admin_roles)
    app.router.add_route("*", "/api/portal/admin/panels", admin_panels)
    app.router.add_route("*", "/api/portal/admin/news", admin_news)
    app.router.add_post("/api/portal/nara/chat", nara_chat)
    app.router.add_route("*", "/api/portal/nara/memory", nara_memory)
    app.router.add_get("/api/portal/sanctuaries/{user_id}", sanctuary)
    app.router.add_post("/api/portal/sanctuaries/honor", honor)
    app.router.add_get("/api/portal/store", store_data)
    app.router.add_post("/api/portal/store/action", store_action)
    app.router.add_post("/api/portal/catalog/{kind}/{item_id}", catalog_admin_decide)
    app.router.add_get("/api/portal/catalog", catalog_list)
    app.router.add_get("/api/portal/catalog/image/{kind}/{item_id}", catalog_image)
    app.router.add_post("/api/portal/catalog/{kind}", catalog_submit)
    app.router.add_get("/api/portal/runs/options", run_options)
    app.router.add_post("/api/portal/runs", run_submit)
    app.router.add_get("/api/portal/contributions", contributions)
    app.router.add_post("/api/portal/contributions", contribution_submit)
    app.router.add_post("/api/portal/community/challenge", challenge_participation)
    app.router.add_get("/api/portal/community/favorites", favorites)
    app.router.add_post("/api/portal/community/interact", community_interact)
    app.router.add_post("/api/portal/community/bookmark", community_bookmark)
    app.router.add_post("/api/portal/community/follow", community_follow)
    app.router.add_route("*", "/api/portal/sanctuaries/{user_id}/guestbook", guestbook)
    app.router.add_route("*", "/api/portal/notifications", notifications)
    app.router.add_route("*", "/api/portal/profile", profile)
    app.router.add_delete("/api/portal/mine/{kind}/{item_id}", cancel_submission)
    app.router.add_route("*", "/api/portal/admin/config", admin_config)
    app.router.add_get("/api/portal/admin/queue", admin_queue)
    app.router.add_post("/api/portal/admin/{kind}/{item_id}", admin_decide)
    app.router.add_post("/api/portal/submit/{kind}", submit)
    app.router.add_get("/api/portal/mine", mine)
    app.router.add_get("/api/portal/uploads/{filename}", serve_upload)
