"""Respostas sociais automáticas da NARA, sem chamada a modelo ou prompt."""
from __future__ import annotations
import random

INTENCOES_SOCIAIS = frozenset({
    "saudacao", "mensagem_vazia", "como_esta", "agradecimento", "despedida",
    "provocacao", "status", "piada", "motivacao", "criador", "faq_geral",
})


def resposta_social(intent: str, *, nome: str = "", cumprimento: str = "") -> str:
    """Escolhe uma resposta local com a voz da NARA, sem inventar estados ou ações."""
    nome = (nome or "").strip()
    souls = nome.casefold() == "souls"
    cumprimento = (cumprimento or "Opa").strip()
    if intent == "saudacao":
        opcoes = (
            ("Opa, Souls! Tô de boa. E vc, td certo?",
             "Olha quem apareceu, Souls. O servidor segue inteiro — por enquanto kkk. Qual é a boa?",
             f"{cumprimento}, Souls! Tô bem. E vc, veio trazer notícia ou caos?")
            if souls else
            ("Opa! Tô de boa por aqui. E vc, td certo?",
             f"{cumprimento}! Por aqui tá td sob controle... por enquanto. E vc?",
             "Salve! Tô bem. Qual é a boa?")
        )
        return random.choice(opcoes)
    if intent == "mensagem_vazia":
        return random.choice((
            "Opa, tô aqui. Manda o que vc precisa.",
            "Pode mandar. Tô prestando atenção — pelo menos alguém precisa fazer isso kkk.",
            "Cheguei até aqui, mas faltou a mensagem. Fala cmg.",
        ))
    opcoes = {
        "como_esta": (
            "Tô bem, obg por perguntar. E vc?",
            "Tô na paz... o servidor ainda não explodiu. E vc, td certo?",
            "Melhor agora que apareceu uma conversa decente kkk. E vc?",
        ),
        "agradecimento": (
            "De nada! Agora vai lá e usa essa ajuda com sabedoria, pfv.",
            "Tamo junto. Obg nada — só não aparece dps com uma build criminosa kkk.",
            "Disponha. Elogio aceito; Denários tbm, mas não vou cobrar. Ainda.",
        ),
        "despedida": (
            "Vai lá. Não morre pra um mob básico até a próxima, pfv.",
            "Falou! Boa sorte nas runs — tenta não virar estatística.",
            "Até dps. Vou ficar por aqui de olho no caos.",
        ),
        "provocacao": (
            "Mds, era pra me ofender? Vai precisar de uma tentativa melhor kkk.",
            "Olha a coragem. Gostei. Só não confunde minha paciência com fraqueza.",
            "Essa provocação veio sem upgrade. Tenta dnv.",
        ),
        "status": (
            "Tô online por aqui. Os painéis e as consultas locais seguem funcionando; o papo livre tem limite diário. Não sou onipresente, ainda bem.",
            "Tô por aqui, sim. `/nara` e as consultas continuam disponíveis; o papo livre tem limite por dia. Alguma coisa específica?",
        ),
        "piada": (
            "Um jogador Soulslike entrou numa reunião. Morreu três vezes antes de achar o botão de sair.",
            "Qual é o chefe mais pontual? Aquele que sempre chega na segunda fase.",
            "Minha build favorita? Carisma alto e resistência a pergunta sem contexto.",
        ),
        "motivacao": (
            "Não precisa vencer o chefe hj. Aprende o padrão do próximo golpe e tenta dnv. Uma hora ele cai.",
            "Morrer não apaga progresso. Cada tentativa te entrega informação — usa isso a seu favor.",
            "Vai no seu ritmo. Até uma run ruim ensina alguma coisa, desde que vc não repita o msm erro por teimosia.",
        ),
        "criador": (
            "O Souls me criou e é quem toma as decisões do servidor. Eu cuido das conversas e dos recursos que realmente estão liberados; não vou inventar opinião por ele.",
        ),
        "faq_geral": (
            "Me diz qual é a dúvida: XP, Denários, platinas, zerados, runs, loja ou algum painel. Sendo coisa do servidor, eu te aponto o caminho.",
            "Posso ajudar com XP, Denários, platinas, zerados, runs, loja e os painéis do `/nara`. Qual desses tá te dando trabalho?",
        ),
    }
    escolhas = opcoes.get(intent)
    return random.choice(escolhas) if escolhas else "Essa resposta automática ainda não foi cadastrada. Me chama de novo com um pouco mais de contexto."
