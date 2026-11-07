"""Roteamento local e respostas determinísticas da Nara.

Este módulo é offline: não chama rede, modelo, OCR nem lê anexos. A Nara só usa IA
externa quando existe um pedido explícito de pesquisa que tenha uma ferramenta de
pesquisa compatível. Pesquisa de troféus/platinas é encaminhada ao Caçador (`/jogo_buscar`),
que usa o fluxo próprio de identificação, fontes, confirmação e revisão.
"""
from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"https?://\S+", " ", texto)
    texto = re.sub(r"[^a-z0-9@+*/=.,!?%$ -]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _tem(texto: str, *termos: str) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", texto) for t in termos)


_GAME_NAMES = (
    "elden ring", "dark souls", "dark souls 2", "dark souls 3", "demon souls", "demons souls",
    "bloodborne", "sekiro", "god of war", "lies of p", "black myth wukong", "hollow knight",
    "nioh", "ghost of tsushima", "cyberpunk", "the witcher", "resident evil", "final fantasy",
    "baldurs gate", "red dead redemption", "assassins creed", "silksong", "stellar blade",
    "armored core", "hades", "the last of us", "spider man", "spiderman", "horizon zero dawn",
    "horizon forbidden west", "tomb raider", "witcher 3", "sekiro shadows die twice",
)


def classificar_resposta_local(mensagem: str) -> str | None:
    """Retorna uma intenção FAQ/SQLite. Nenhuma intenção chama Gemini."""
    t = normalizar(mensagem)
    if not t:
        return None

    # Perguntas operacionais e formulários do próprio Soulsbot têm prioridade.
    if _tem(t, "como registrar platina", "registrar platina", "enviar platina", "cadastrar platina",
            "como posto minha platina", "como adiciono uma platina", "como registrar trofeu",
            "enviar minha platina", "adicionar platina", "como mandar minha platina", "como submeter platina") \
            or ("registrar" in t and "platina" in t):
        return "como_registrar_platina"
    if _tem(t, "como registrar zerado", "registrar zerado", "registrar jogo zerado", "cadastrar zerado",
            "como registro que zerei", "como adicionar jogo zerado", "como marcar jogo zerado",
            "como registrar que zerei", "como posto jogo zerado"):
        return "como_registrar_zerado"
    if _tem(t, "como registrar run", "registrar run", "cadastrar run", "enviar run", "registrar desafio",
            "como cadastrar uma run", "como mandar uma run", "como submeter uma run", "como posto minha run",
            "como participar das runs", "como entrar nas runs", "como participar do soulslike"):
        return "como_registrar_run"
    if _tem(t, "como remover zerado", "remover zerado", "excluir zerado", "apagar zerado",
            "como apagar um jogo zerado", "como excluir um jogo zerado", "quero remover meu zerado"):
        return "como_remover_zerado"
    if _tem(t, "quando recebo a recompensa", "quando recebo xp", "quando recebo os denarios",
            "quando cai a recompensa", "quando ganho a recompensa", "quando entra o xp",
            "minha recompensa nao caiu", "nao recebi a recompensa"):
        return "quando_recebo_recompensa"
    if _tem(t, "minha platina esta pendente", "platina pendente", "registro pendente", "minha run esta pendente",
            "quanto demora para aprovar", "quanto tempo para aprovar", "quem aprova minha platina",
            "quem aprova minha run", "como funciona a aprovacao", "como funciona a moderacao"):
        return "como_funciona_aprovacao"
    if _tem(t, "como ver minhas platinas", "onde vejo minhas platinas", "consultar minhas platinas",
            "abrir minhas platinas", "lista das minhas platinas"):
        return "como_ver_platinas"
    if _tem(t, "como ver meus zerados", "onde vejo meus zerados", "consultar meus zerados",
            "lista dos meus jogos zerados"):
        return "como_ver_zerados"
    if _tem(t, "como ver minhas runs", "onde vejo minhas runs", "consultar minhas runs",
            "lista das minhas runs", "historico de runs"):
        return "como_ver_runs"
    if _tem(t, "como enviar comprovante", "como mandar comprovante", "como mando o comprovante",
            "onde envio print", "enviar print", "print de comprovante", "comprovante da platina",
            "comprovante da run", "onde mando o print", "como anexar comprovante") or \
            ("comprovante" in t and _tem(t, "como", "onde", "enviar", "mandar", "mando", "anexar")):
        return "como_comprovante"
    if _tem(t, "como abrir o cacador", "como usar o cacador", "como funciona o cacador",
            "como pesquisar um jogo no bot", "como buscar um jogo no bot", "como adicionar jogo no cacador",
            "como criar catalogo", "como funciona catalogo", "como pesquisar trofeus no bot"):
        return "como_buscar_jogo"

    # Sistemas, regras e dúvidas comuns.
    if _tem(t, "como ganhar xp", "ganhar xp", "conseguir xp", "como funciona xp", "xp por mensagem",
            "quanto xp por mensagem", "quanto ganho de xp", "como farmar xp", "como pegar xp",
            "como acumular xp", "como subir de nivel", "como upar", "o que e xp"):
        return "como_ganhar_xp"
    if _tem(t, "como ganhar denarios", "ganhar denarios", "conseguir denarios", "como conseguir moedas",
            "como farmar denarios", "como pegar denarios", "como acumular denarios", "o que sao denarios",
            "o que e denario", "para que servem denarios"):
        return "como_ganhar_denarios"
    if _tem(t, "quanto vale uma platina", "quanto da uma platina", "recompensa da platina",
            "recompensa de uma platina", "quanto recebo por uma platina", "quanto ganha por platinar",
            "recompensa por platinar", "recompensa por jogo zerado", "quanto ganha por zerar"):
        return "recompensas"
    if _tem(t, "como funciona a loja", "loja de denarios", "o que tem na loja", "itens da loja",
            "como comprar", "comprar item", "comprar uma cor", "como equipar", "equipar item",
            "como trocar minha cor", "como mudar meu titulo", "como funciona o inventario",
            "o que posso comprar"):
        return "loja"
    if _tem(t, "como funciona patente", "patentes", "cargos de nivel", "cargos por nivel",
            "quais sao as patentes", "lista de patentes", "como ganho cargo"):
        return "patentes"
    if _tem(t, "como funciona o coliseu", "o que e coliseu", "painel do coliseu", "central soulslike",
            "o que tem no coliseu", "areas do coliseu"):
        return "coliseu"
    if _tem(t, "como funciona santuario", "meu santuario", "santuario", "como criar meu santuario",
            "como editar meu santuario", "como visitar santuario", "como personalizar meu perfil",
            "como mudar meu banner", "como colocar minhas redes", "como visitar o santuario de alguem"):
        return "santuario"
    if _tem(t, "como funciona ranking", "ver ranking", "quais rankings", "ranking de xp",
            "ranking de platinas", "ranking de zerados", "top do servidor", "classificacao do servidor",
            "como subir no ranking", "como entrar no ranking"):
        return "rankings"
    if _tem(t, "como funciona youtube", "aviso de video", "avisos de video", "avisos de live",
            "notificacao de live", "como receber aviso de live", "como receber aviso de video"):
        return "youtube"
    if _tem(t, "ofertas", "promocoes", "jogos gratis", "jogos gratuitos", "steam gratis", "epic gratis") and \
            _tem(t, "como", "quais", "onde", "tem", "funciona", "aviso", "avisos", "receber", "ver", "mostrar"):
        return "ofertas"
    if _tem(t, "regras do servidor", "regras do bot", "quais as regras", "como funcionam as regras",
            "posso divulgar", "pode divulgar", "regras para divulgar"):
        return "regras"
    if _tem(t, "meus dados sao privados", "meu saldo e privado", "quem pode ver meu saldo",
            "quem ve meu inventario", "privacidade", "meus dados"):
        return "privacidade"
    if _tem(t, "como falar com a nara", "como chamar a nara", "como eu chamo a nara", "como te marco",
            "como marcar voce", "preciso te marcar", "voce responde aqui"):
        return "como_chamar_nara"
    if _tem(t, "como ver perfil de outro", "ver perfil de outra pessoa", "consultar perfil de outro",
            "perfil de outro membro", "como olhar perfil de alguem", "como ver perfil de membro"):
        return "perfil_outro_membro"

    # Consultas pessoais que o SQLite já consegue responder.
    if _tem(t, "meu saldo", "meus denarios", "quantos denarios", "quanto tenho", "quanto eu tenho de denarios",
            "quantos denarios eu tenho", "quanto de moeda", "meu dinheiro", "meu saldo de moedas"):
        return "meu_saldo"
    if _tem(t, "meu nivel", "qual meu nivel", "qual e meu nivel", "meu xp", "quanto xp tenho",
            "quanto xp eu tenho", "minha patente", "meu perfil", "minhas estatisticas",
            "quanto falta para upar", "quanto falta pro proximo nivel", "quanto falta para o proximo nivel",
            "minha posicao no ranking", "minha colocacao"):
        return "meu_perfil"
    if _tem(t, "minhas platinas", "quantas platinas tenho", "quantas platinas eu tenho",
            "minhas conquistas aprovadas", "minhas platinas aprovadas", "meus trofeus", "minhas conquistas",
            "minhas platinas no perfil"):
        return "minhas_platinas"
    if _tem(t, "meus jogos zerados", "quantos jogos zerei", "quantos jogos eu zerei", "meus zerados",
            "jogos que zerei", "quantos zerados tenho", "minhas finalizacoes"):
        return "meus_zerados"
    if _tem(t, "minhas runs", "quantas runs tenho", "minhas runs aprovadas", "minhas estatisticas de run",
            "minhas runs no coliseu"):
        return "minhas_runs"
    if _tem(t, "meu inventario", "meus itens", "itens que comprei", "o que eu tenho na loja",
            "quais itens eu possuo", "minhas cores compradas", "meus titulos comprados"):
        return "meu_inventario"
    if _tem(t, "quem esta no top", "top xp", "top 10 xp", "ranking xp", "maior xp", "quem tem mais xp",
            "top 10 de xp", "top do xp"):
        return "ranking_xp"
    if _tem(t, "top platinas", "quem tem mais platinas", "ranking platinas", "top de platinas"):
        return "ranking_platinas"
    if _tem(t, "top zerados", "quem zerou mais jogos", "ranking zerados", "top jogos zerados"):
        return "ranking_zerados"

    # Conversa social e ajuda simples.
    if _tem(t, "oi", "ola", "eai", "e ae", "e ai", "opa", "salve", "bom dia", "boa tarde", "boa noite",
            "fala nara", "fala ai") and len(t.split()) <= 10:
        return "saudacao"
    if _tem(t, "quem e voce", "qual seu nome", "seu nome", "quem e a nara", "o que e voce", "voce e uma ia",
            "voce e humana", "voce e um bot"):
        return "identidade"
    if _tem(t, "o que voce faz", "o que voce consegue fazer", "como voce funciona", "suas funcoes",
            "suas funcionalidades", "no que voce pode ajudar", "com o que voce ajuda"):
        return "capacidades"
    if _tem(t, "ajuda", "me ajuda", "preciso de ajuda", "comandos", "quais comandos", "lista de comandos",
            "comandos do bot", "como uso o bot", "como usar o bot", "me mostra os comandos"):
        return "ajuda"
    if _tem(t, "obrigado", "obrigada", "obg", "valeu", "vlw", "agradeco", "muito obrigado", "tmj",
            "brigado", "brigada", "era isso", "perfeito valeu"):
        return "agradecimento"
    if _tem(t, "tchau", "falou", "ate mais", "fui", "vou nessa", "ate depois", "flw", "boa noite nara"):
        return "despedida"
    if _tem(t, "tudo bem", "como voce esta", "como vai", "de boa", "suave", "tudo certo") and len(t.split()) <= 12:
        return "como_esta"
    if _tem(t, "voce e burra", "voce e chata", "sua inutil", "burra", "nao serve pra nada"):
        return "provocacao"
    if _tem(t, "voce esta online", "esta funcionando", "ta funcionando", "bot esta online", "nara esta ai",
            "nara esta online", "a nara esta online", "esta ai", "voce esta viva", "nara funciona"):
        return "status"
    if _tem(t, "conta uma piada", "me conta uma piada", "faz uma piada", "me faz rir", "conte uma piada"):
        return "piada"
    if _tem(t, "me motiva", "uma frase motivacional", "preciso de motivacao", "me de motivacao",
            "fala algo motivador", "me da uma frase"):
        return "motivacao"
    if _tem(t, "quem te criou", "quem criou voce", "quem e seu criador", "quem fez voce", "quem programou voce"):
        return "criador"
    if _tem(t, "voce pode ver print", "voce analisa imagem", "voce pode analisar meu print", "analisa meu print",
            "olha essa imagem", "ve esse print", "voce enxerga imagem", "consegue ler screenshot"):
        return "sem_visao"

    return None


def _tem_pedido_explicito(t: str) -> bool:
    acoes = (
        "pesquise", "pesquisar", "pesquisa", "procure", "procura", "buscar", "busque", "consulta", "consultar",
        "me diga", "me mostra", "me fale", "me fala", "me passa", "me passe", "me lista", "quero saber",
        "quero a lista", "quero ver", "lista", "listar", "guia", "como conseguir", "como pegar", "como platinar", "onde encontrar", "onde fica",
        "quais sao", "quais os", "quais", "todos os", "requisitos", "perdivel", "perdiveis", "missavel",
        "missaveis", "tempo de platina", "dificuldade", "100 por cento", "como derrotar", "como vencer",
        "como fazer", "me explica", "me explique", "explique", "me ensina", "melhor build", "qual a melhor build", "qual arma",
        "melhor arma", "localizacao", "onde pego", "onde achar", "dicas de", "rota", "final secreto",
        "final verdadeiro", "identifique o jogo", "identificar o jogo", "procure o jogo", "buscar jogo",
        "pesquisar jogo", "pesquise o jogo", "adicione no cacador", "catalogo de", "me diga os trofeus",
        "me fala os trofeus", "me passe os trofeus", "mostre os trofeus", "quero os trofeus",
    )
    return any(acao in t for acao in acoes)


def is_pesquisa_de_catalogo(mensagem: str) -> bool:
    """Detecta pedidos para catálogo de jogo/troféus, que devem usar `/jogo_buscar`."""
    t = normalizar(mensagem)
    if not t or not _tem_pedido_explicito(t):
        return False
    if classificar_resposta_local(mensagem) in {
        "como_registrar_platina", "como_comprovante", "minhas_platinas", "como_buscar_jogo"
    }:
        # A pergunta sobre como usar o catálogo é FAQ; não é uma busca.
        return False
    termos_catalogo = (
        "trofeu", "trofeus", "platina", "platinar", "conquista", "conquistas", "100 por cento",
        "coletavel", "coletaveis", "colecionavel", "colecionaveis", "perdivel", "perdiveis", "missavel",
        "missaveis", "lista completa", "todos os itens",
    )
    # Se o usuário omitir o título, ainda encaminhamos ao comando para ele informar
    # o jogo. Não mandamos essa solicitação incompleta para o modelo conversacional.
    return any(term in t for term in termos_catalogo)


def is_pesquisa_de_jogo(mensagem: str) -> bool:
    """Pesquisa conversacional por wiki. Nesta versão, o conjunto de fontes de chat é Elden Ring.

    Catálogo de troféus/platinas de qualquer jogo não passa por aqui: é encaminhado para
    `/jogo_buscar`, cuja integração usa Google Search grounding e revisão própria.
    """
    t = normalizar(mensagem)
    if not t or is_pesquisa_de_catalogo(mensagem) or not _tem_pedido_explicito(t):
        return False
    # Ferramentas `buscar_wiki`/`abrir_pagina` só permitem fontes de Elden Ring. Não
    # enviar pedidos de outros jogos para esse conjunto de ferramentas.
    temas_elden = (
        "elden ring", "shadow of the erdtree", "malenia", "radahn", "margit", "messmer", "ranni",
        "moonlight greatsword", "erdtree", "mohg", "godfrey", "rykard", "maliketh", "rennala",
        "radagon", "elden beast", "blaidd", "millicent", "varre", "roundtable hold",
    )
    return any(tema in t for tema in temas_elden)


def is_pesquisa_nao_suportada(mensagem: str) -> bool:
    """Pesquisa explícita de jogo que não cabe nas fontes de chat habilitadas."""
    t = normalizar(mensagem)
    if not t or is_pesquisa_de_catalogo(mensagem) or is_pesquisa_de_jogo(mensagem):
        return False
    if not _tem_pedido_explicito(t):
        return False
    game_context = ("jogo", "game", "videogame", "souls", "soulslike", "soulsborne", "boss", "chefe",
                    "arma", "armas", "build", "talisma", "dlc", "trofeu", "platina", "conquista")
    return any(nome in t for nome in _GAME_NAMES) or _tem(t, *game_context)


def decidir_rota(mensagem: str, *, direcionada: bool, canal_livre: bool,
                 tem_imagem: bool = False) -> tuple[str, str | None]:
    """Roteia sem rede/modelo: FAQ, catálogo, busca Elden Ring, recusa de print ou ignorar."""
    texto = (mensagem or "").strip()
    if not direcionada and not canal_livre:
        return "ignorar", None
    if tem_imagem and not texto:
        return "recusar_imagem", None

    intent = classificar_resposta_local(texto)
    if intent:
        return "local", intent
    if is_pesquisa_de_catalogo(texto):
        return ("catalogo", None) if direcionada else ("pedir_mencao", None)
    if is_pesquisa_de_jogo(texto):
        return ("gemini", None) if direcionada else ("pedir_mencao", None)
    if is_pesquisa_nao_suportada(texto):
        return ("pesquisa_nao_suportada", None) if direcionada else ("pedir_mencao", None)
    return ("fallback", None) if direcionada else ("ignorar", None)




def aplicar_politica_de_quota(rota: str, *, chat_ia_ativa: bool = False) -> str:
    """Desliga pesquisa conversacional por padrão; preserva apenas rotas locais/catálogo.

    `/jogo_buscar` é um comando separado e não passa por este roteador de chat.
    """
    if rota == "gemini" and not chat_ia_ativa:
        return "pesquisa_chat_desativada"
    return rota

def resposta_local_fallback(mensagem: str) -> str:
    """Fallback sem IA para mensagens dirigidas à Nara não cobertas pelo FAQ."""
    t = normalizar(mensagem)
    if any(x in t for x in ("jogo", "elden", "souls", "boss", "chefe", "trofeu", "platina", "conquista", "dlc")):
        return (
            "Isso exige informação específica de um jogo. Para pesquisar troféus, platina e colecionáveis, "
            "use `/jogo_buscar` com o nome do jogo. Para guias gerais, eu só consulto fontes de Elden Ring "
            "nesta conversa; prefiro não inventar dados de outros títulos."
        )
    return (
        "Consigo resolver perguntas frequentes e consultar seus dados do Soulsbot sem gastar quota de IA. "
        "Tente **ajuda**, **meu perfil**, **meu saldo**, **minhas platinas**, **como registrar platina** ou "
        "**como ganhar XP**. Pesquisa de catálogo é feita por `/jogo_buscar`."
    )


def tem_anexo_visual(attachments) -> bool:
    """Verifica somente MIME/nome; jamais chama read(), save(), download ou OCR."""
    image_exts = (
        ".png", ".jpg", ".jpeg", ".jfif", ".pjpeg", ".pjp", ".webp", ".gif", ".apng",
        ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif", ".svg",
    )
    for attachment in attachments or ():
        mime = (getattr(attachment, "content_type", None) or "").split(";", 1)[0].strip().lower()
        filename = (getattr(attachment, "filename", None) or "").lower()
        if mime.startswith("image/") or filename.endswith(image_exts):
            return True
    return False
