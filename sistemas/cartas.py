"""Catálogo e regras puras do Cartas do Coliseu.

Todas as artes usam símbolos e geometria original; nenhum recurso visual de jogos
proprietários é incorporado ao catálogo.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from levels import PATENTES

VERSAO_ARTES = 33

TIPOS = ("Destreza", "Força", "Magia")

RARIDADES = ("Comum", "Rara", "Épica", "Lendária", "Mítica", "Primordial", "Singular")
PESOS_RARIDADE = {"Comum": 69.47, "Rara": 22.02, "Épica": 7.01, "Lendária": 1.00, "Mítica": 0.50, "Primordial": 0.0, "Singular": 0.0}
CUSTO_RARIDADE = {"Comum": 1, "Rara": 2, "Épica": 3, "Lendária": 4, "Mítica": 5, "Primordial": 6, "Singular": 0}
FAIXA_PODER = {
    "Comum": (3, 5),
    "Rara": (4, 6),
    "Épica": (5, 7),
    "Lendária": (6, 8),
    "Mítica": (8, 9),
    "Primordial": (8, 9),
    "Singular": (8, 10),
}
ALMAS_DUPLICATA = {"Comum": 5, "Rara": 15, "Épica": 40, "Lendária": 100, "Mítica": 180, "Primordial": 250, "Singular": 0}
BONUS_EVOLUCAO_FRAGMENTOS = {"Comum": 20, "Rara": 40, "Épica": 80, "Lendária": 160}
CUSTO_APRIMORAMENTO_ALMAS = {"Comum": 10, "Rara": 20, "Épica": 40, "Lendária": 80, "Mítica": 150, "Primordial": 250}


def limite_poder_modelo(carta: "Carta") -> int:
    """Teto individual do modelo: parte do poder-base e nunca ultrapassa 12."""
    if str(getattr(carta, "categoria", "")).casefold() == "especial":
        return 0
    return min(12, max(5, int(getattr(carta, "poder", 1)) + 6))


def faixa_poder_exemplar(carta: "Carta", raridade: str) -> tuple[int, int]:
    """Faixa inicial da raridade limitada pelo teto próprio do modelo."""
    if str(getattr(carta, "categoria", "")).casefold() == "especial":
        return (0, 0)
    minimo, maximo = FAIXA_PODER.get(str(raridade), FAIXA_PODER["Comum"])
    maximo = min(int(maximo), limite_poder_modelo(carta))
    minimo = min(int(minimo), maximo)
    return (minimo, maximo)
CUSTO_FORJA = {"Comum": 0, "Rara": 0, "Épica": 0, "Lendária": 0, "Mítica": 0, "Primordial": 0, "Singular": 0}
PRECO_PACOTE_FOGUEIRA = 120
CARTAS_POR_PACOTE = 3
PITY_CARTAS = 10

# Habilidades comuns: efeitos situacionais que permitem montar decks com estilos diferentes.
# As cinco habilidades Primordiais ficam separadas porque cada uma pertence a uma carta única.
HABILIDADES_COMUNS = (
    "primeira_luz", "retaliacao", "impeto", "ultimo_folego", "contragolpe",
    "encadeamento", "adaptacao", "sangue_frio", "instinto", "precisao",
    "drenagem", "cacador_arcano", "quebra_ritmo",
)
HABILIDADES_PRIMORDIAIS = (
    "lei_primeva", "decreto_soberano", "olho_tempestade", "fome_abismo", "paradoxo_eterno",
)

HABILIDADES: dict[str, dict[str, str]] = {
    "primeira_luz": {"nome": "Graça Dourada", "texto": "Na primeira rodada, ganha +1 de bônus ao entrar em campo."},
    "retaliacao": {"nome": "Retaliação dos Semideuses", "texto": "Se sua equipe estiver perdendo quando esta carta entrar, ganha +1 de bônus."},
    "impeto": {"nome": "Ímpeto do Lorde", "texto": "Se sua equipe estiver vencendo quando esta carta entrar, ganha +1 de bônus."},
    "ultimo_folego": {"nome": "Último Suspiro", "texto": "Na terceira rodada, ganha +1 de bônus ao entrar em campo."},
    "contragolpe": {"nome": "Contragolpe", "texto": "Se sua equipe estiver perdendo quando esta carta entrar, ganha +2 de bônus."},
    "encadeamento": {"nome": "Postura Encadeada", "texto": "Ganha +2 de bônus se sua última unidade foi jogada nesta mesma fileira."},
    "adaptacao": {"nome": "Passo do Peregrino", "texto": "Ganha +1 de bônus se sua última unidade foi jogada em outra fileira."},
    "sangue_frio": {"nome": "Concentração", "texto": "Se as equipes estiverem empatadas quando esta carta entrar, ganha +2 de bônus."},
    "instinto": {"nome": "Instinto de Caçador", "texto": "Se sua equipe estiver perdendo quando esta carta entrar, ganha +2 de bônus."},
    "precisao": {"nome": "Mira Cariana", "texto": "Ao entrar na fileira de Longa Distância, ganha +1 de bônus."},
    "drenagem": {"nome": "Selo Enfraquecedor", "texto": "Ao entrar, tira 1 ponto do bônus de cada inimigo. O bônus não pode ficar abaixo de -2."},
    "cacador_arcano": {"nome": "Caçador de Feitiços", "texto": "Ganha +1 de bônus se o inimigo tiver uma unidade da Lua Negra ou qualquer unidade com bônus acima de 0."},
    "quebra_ritmo": {"nome": "Ruptura de Postura", "texto": "Ganha +1 de bônus se a última unidade jogada pelo inimigo nesta rodada entrou nesta fileira."},
    # Efeitos exclusivos: somente a respectiva Primordial pode utilizá-los.
    "lei_primeva": {"nome": "Lei Primeva", "texto": "Na primeira rodada, ganha +2 de bônus ao entrar em campo."},
    "decreto_soberano": {"nome": "Decreto Soberano", "texto": "Ao entrar, tira 2 pontos do bônus de cada inimigo. Nenhum bônus pode ficar abaixo de -2."},
    "olho_tempestade": {"nome": "Olho da Tempestade", "texto": "Se houver clima na fileira escolhida, ganha +2 de bônus ao entrar."},
    "fome_abismo": {"nome": "Fome do Abismo", "texto": "Se sua equipe estiver perdendo quando esta carta entrar, ganha +2 de bônus."},
    "paradoxo_eterno": {"nome": "Paradoxo Eterno", "texto": "Na terceira rodada, ganha +2 de bônus se o inimigo venceu a segunda rodada."},
    "guardiao_fileira": {"nome": "Guardião da Fileira", "texto": "Ganha +1 de bônus para cada aliado que já esteja nesta fileira, até +3."},
    "cacador_solitario": {"nome": "Caçador Solitário", "texto": "Ganha +2 de bônus se não houver outro aliado nesta fileira quando entrar."},
    "estandarte": {"nome": "Estandarte", "texto": "Ao entrar, dá +1 de bônus a cada aliado que já esteja na mesma fileira."},
    "resistencia_climatica": {"nome": "Resistência Climática", "texto": "O clima tira até 2 pontos a menos desta carta. Se não houver clima em nenhuma fileira, ela ganha +1 de bônus ao entrar."},
    "eco_arcano": {"nome": "Eco Arcano", "texto": "+2 de bônus se houver pelo menos uma carta Especial no seu descarte."},
    "gwent_nevoa": {"nome": "Névoa de Sellia", "texto": "Escolha a fileira desejada. Todos os inimigos da fileira escolhida recebem Podridão Escarlate. Cada marca reduz o poder atual em 1 até o fim da rodada."},
    "gwent_geada": {"nome": "Lua Gélida", "texto": "Todos os inimigos em campo recebem 1 marca de Geada. Cada marca reduz o poder atual em 1 até o fim da rodada."},
    "gwent_chuva": {"nome": "Sangue Corrompido", "texto": "Todos os inimigos em Cerco recebem Sangramento. A segunda marca causa Hemorragia: tira 2 pontos do bônus (até -2) e apaga as marcas. As marcas restantes somem no fim da rodada."},
    "gwent_chifre": {"nome": "Rugido de Godfrey", "texto": "Escolha uma fileira. Todos os seus aliados nela ganham +2 de bônus nesta rodada."},
    "gwent_medico": {"nome": "Lágrima Sagrada", "texto": "Escolha uma unidade do seu descarte e coloque-a na sua mão. O poder-base máximo permitido depende da raridade."},
    "gwent_queima": {"nome": "Chama Negra", "texto": "Remove a unidade mais forte de cada lado do campo. Se ela tiver escudo, perde o escudo e continua em campo."},
    "gwent_purificar": {"nome": "Lei da Regressão", "texto": "Acaba com o clima nas três fileiras. Não remove as marcas de Geada, Sangramento, Podridão ou Loucura das unidades."},
    "gwent_execucao": {"nome": "Lâmina da Morte Destinada", "texto": "Escolha uma fileira e remova 1 inimigo com poder atual de até 6. Se ele tiver escudo, perde o escudo e continua em campo."},
    "gwent_vinculo": {"nome": "Juramento do Crisol", "texto": "Escolha uma fileira com pelo menos 2 aliados. Todos os seus aliados nela ganham +2 de bônus nesta rodada."},
    "gwent_batedor": {"nome": "Passo do Cão de Caça", "texto": "Compra cartas do topo do seu baralho. A raridade define quantas cartas você compra."},
    "gwent_muralha": {"nome": "Bastião de Leyndell", "texto": "Escolha uma fileira. Todos os seus aliados nela ganham +1 de bônus nesta rodada."},
    "vinganca": {"nome": "Vingança", "texto": "Quando esta unidade sair do campo, cada aliado que continuar na mesma fileira ganha +1 de bônus."},
    "escudo_ferro": {"nome": "Escudo de Ferro", "texto": "Entra em campo com 1 escudo. O escudo bloqueia a primeira tentativa de destruição ou execução. Sacrifícios ignoram o escudo."},
    "ressurgir": {"nome": "Ressurgir", "texto": "Ao entrar, se houver uma unidade no seu descarte com poder-base até 5, traz de volta a mais forte entre elas. Ela retorna à fileira original."},
    "devorar": {"nome": "Devorar", "texto": "Ao entrar, sacrifica o aliado mais fraco da mesma fileira e ganha bônus igual à força atual dele, até +4. O escudo não impede o sacrifício. Sem aliado, não ganha bônus."},
    "sobrevivente": {"nome": "Sobrevivente", "texto": "No fim da rodada, a unidade com esta habilidade que tiver maior força atual permanece para a próxima rodada. Todas as outras unidades aliadas vão para o descarte. Bônus, escudos e marcas são removidos."},
    "espolios": {"nome": "Espólios", "texto": "Se sua equipe vencer a rodada e pelo menos uma unidade com esta habilidade estiver em campo, você compra 1 carta."},
    "gwent_egide": {"nome": "Bênção da Árvore Áurea", "texto": "Dá escudo aos aliados que ainda não tenham um. Você escolhe o primeiro; se não escolher, o mais forte recebe primeiro. Depois, os mais fortes são protegidos até o limite da raridade."},
    "gwent_requiem": {"nome": "Chamado dos Mortos", "texto": "Escolha uma unidade do seu descarte para voltar ao campo, na fileira em que caiu. Ela retorna sem bônus e sem escudo. O poder-base máximo depende da raridade."},
    "gwent_passo": {"nome": "Passo do Lobo", "texto": "Move aliados de outras fileiras para a fileira escolhida. Você pode escolher quem será movido primeiro; depois, os demais seguem a ordem em que aparecem no campo. Sem escolha, o mais fraco é movido primeiro."},
    "dupla_fornalha": {"nome": "Pacto da Fornalha", "texto": "Ganha +2 de bônus se já houver outra unidade do tipo Força nesta fileira."},
    "irmandade_veu": {"nome": "Formação do Véu", "texto": "Ganha +2 de bônus se já houver outra unidade do tipo Destreza em outra fileira."},
    "circulo_arcano": {"nome": "Círculo de Ressonância", "texto": "Ganha +2 de bônus se já houver uma unidade do tipo Magia nesta fileira ou uma carta Especial no seu descarte."},
    "gwent_sangramento": {"nome": "Sangramento", "texto": "Escolha uma fileira. Todos os inimigos nela recebem Sangramento. A segunda marca causa Hemorragia: tira 2 pontos do bônus (até -2) e apaga as marcas. As marcas restantes somem no fim da rodada."},
    "gwent_geada_cariana": {"nome": "Geada Cariana", "texto": "Escolha uma fileira. Todos os inimigos nela recebem Geada. Cada marca reduz o poder atual em 1; cada inimigo pode ter até 2 marcas. Elas somem no fim da rodada."},
    "gwent_podrida": {"nome": "Podridão Escarlate", "texto": "Escolha uma fileira. Todos os inimigos nela recebem Podridão Escarlate. Cada marca reduz o poder atual em 1; a segunda também tira 1 ponto do bônus positivo. As marcas somem no fim da rodada."},
    "gwent_loucura": {"nome": "Loucura Frenética", "texto": "Escolha uma fileira. Todos os inimigos nela recebem Loucura. Cada marca reduz o poder atual em 1; a segunda zera o bônus positivo. As marcas somem no fim da rodada."},
    "gwent_chama": {"nome": "Chama do Gigante", "texto": "Remove Geada de todos os aliados que tenham essa marca. Cada aliado purificado ganha +1 de bônus nesta rodada."},
    "gwent_invocacao": {"nome": "Cinzas dos Lobos Solitários", "texto": "Invoca a unidade Lobos Espirituais na fileira escolhida. O poder-base dela depende da raridade."},
    "reliquia_godrick": {"nome": "Grande Runa de Godrick", "texto": "Uma vez por partida: se você tiver ao menos 1 aliado em campo, todos os seus aliados recebem +1 de bônus."},
    "reliquia_renala": {"nome": "Grande Runa dos Não Nascidos", "texto": "Uma vez por partida: remove Geada e Podridão de todos os aliados afetados. Cada aliado purificado recebe +1 de bônus."},
    "reliquia_morte": {"nome": "Runa da Morte", "texto": "Uma vez por partida: em cada fileira, encontra o inimigo com maior bônus positivo e reduz esse bônus em 2, sem deixá-lo abaixo de 0."},
    "reliquia_noite_chama": {"nome": "Espada da Noite e da Chama", "texto": "Uma vez por partida, escolha fileira e postura. Noite: aplica 1 marca de Geada a todos os inimigos da fileira (-1 de poder atual até o fim da rodada). Chama: tira 1 do poder-base (mín. 1) e 2 do bônus do inimigo mais forte. Escudo bloqueia Chama, mas a Relíquia é consumida."},
    "reliquia_lamina_negra": {"nome": "Lâmina Negra", "texto": "Uma vez por partida, escolha um inimigo da fileira: o bônus dele cai em 3. Sem alvo escolhido, atinge o mais forte da fileira. Se houver escudo, ele é gasto e a Relíquia não é consumida."},
    "reliquia_algemas": {"nome": "Algemas de Margit", "texto": "Uma vez por partida, escolha um inimigo da fileira. Se o bônus for positivo, cai para 0; bônus negativos não mudam. Sem alvo escolhido, atinge quem tem o maior bônus na fileira."},
}


# Alinhamento narrativo individual. Não altera o tipo mecânico nem a composição
# predominante do deck; serve para identificar a lealdade/ambientação da carta.
FACCOES_IDENTIDADE_POR_CARTA = {
    # Personagens e grupos cuja facção narrativa não coincide com o tipo de combate.
    "chefe_oraculo_ruina": "Ordem Áurea",              # Gurranq/Maliketh, sombra leal de Marika
    "primordial_tempestade": "Lua Negra",               # Placidusax: tempestade ancestral e domínio do tempo
    "arma_martelo_fornalha": "Véu Carmesim",           # Artesão de Volcano Manor
    "arma_duas_luas": "Lua Negra",                     # Tradição cariana
    "arma_arco_peregrino": "Véu Carmesim",              # Recusante de Volcano Manor
    "magia_selo_vigilia": "Ordem Áurea",                # Confessora da Ordem Áurea
    "magia_fagulha": "Lua Negra",                       # Feitiçaria cariana
    "magia_sol_negro": "Véu Carmesim",                  # Apóstolos da Pele Divina e chama negra
    "covenant_lua_velada": "Lua Negra",                 # Juramentada de Ranni
    "covenant_coroa_abismo": "Véu Carmesim",            # Dinastia de Mohgwyn
    "covenant_peregrinos_nevoa": "Lua Negra",           # Cidades Eternas
    "gwent_unidade_senhor_cacada": "Lua Negra",         # Blaidd, aliado de Ranni
    "gwent_unidade_cavaleira": "Lua Negra",             # Cavaleira Cariana
    "gwent_unidade_cartografa": "Lua Negra",            # Exploradora da Cidade Eterna
    "gwent_unidade_invocador": "Véu Carmesim",          # Apóstolo da Pele Divina
    "gwent_unidade_mestre_forja": "Véu Carmesim",       # Ferreiro de Volcano Manor
    "gwent_unidade_dupla_veu": "Lua Negra",              # Gêmeas da Cidade Eterna
    "gwent_unidade_saqueadora_veu": "Lua Negra",        # Ladina da Cidade Eterna
    "gwent_unidade_contrabandista": "Véu Carmesim",     # Recusante de Volcano Manor
    "gwent_unidade_guardiao_runas": "Ordem Áurea",      # Guardião da Ordem Áurea
    "gwent_unidade_detonador": "Véu Carmesim",          # Guerreiro da Chama Frenética
    "gwent_unidade_devorador_mana": "Véu Carmesim",     # Cavaleiro de Sangue de Mohg
    "gwent_unidade_carniceiro_forja": "Véu Carmesim",   # Recusante de Volcano Manor
}

# A fileira é definida pelo papel tático da unidade, não pela facção.
# Cartas geradas sem entrada explícita usam o padrão de seu arquétipo.
FILEIRAS_POR_CARTA = {
    "chefe_dama_vazio": "siege", "chefe_oraculo_ruina": "melee",
    "chefe_cervo_sombrio": "melee", "chefe_cacador_sem_rosto": "melee",
    "chefe_aparicao_veio": "melee", "arma_lamina_peregrino": "melee",
    "arma_duas_luas": "melee", "covenant_lobos_cinza": "melee",
    "arma_cajado_marulho": "ranged", "arma_agulha_astro": "ranged",
    "magia_brasa_errante": "melee", "magia_selo_vigilia": "melee",
    "magia_trovao_oco": "ranged", "magia_fagulha": "ranged",
    "magia_orbe_eco": "ranged", "magia_chama_fria": "ranged",
    "magia_sol_negro": "melee", "covenant_lua_velada": "ranged",
    "covenant_sentinelas": "melee", "covenant_coroa_abismo": "melee",
    "covenant_ultimos": "melee", "covenant_peregrinos_nevoa": "ranged",
    "gwent_unidade_oraculo_clima": "siege", "gwent_unidade_eco": "siege",
    "gwent_unidade_cavaleira": "melee", "gwent_unidade_cartografa": "ranged",
    "gwent_unidade_invocador": "siege", "gwent_unidade_dupla_veu": "melee",
    "gwent_unidade_circulo": "siege", "gwent_unidade_guardiao_runas": "melee",
    "gwent_unidade_necromante": "siege", "gwent_unidade_detonador": "melee",
    "gwent_unidade_devorador_mana": "melee", "gwent_unidade_bibliotecaria": "siege",
    "gwent_unidade_saqueadora_veu": "ranged", "gwent_unidade_contrabandista": "ranged",
    "gwent_unidade_cacadora_fantasma": "melee", "gwent_unidade_senhor_cacada": "melee",
    "gwent_unidade_sentinela_rubra": "melee", "gwent_unidade_veterano_cercos": "melee",
    "gwent_unidade_herdeiro_portao": "melee", "gwent_unidade_carniceiro_forja": "melee",
    "gwent_unidade_intendente": "ranged", "gwent_unidade_gigante": "melee",
    "gwent_unidade_mestre_forja": "melee", "gwent_unidade_lamina_sem_juramento": "melee",
    "gwent_unidade_portaestandarte": "melee", "gwent_mitica_coroa": "melee",
    "gwent_singular_primeiro": "melee", "gwent_singular_intocavel": "melee",
    "gwent_singular_nivel1": "melee", "gwent_singular_cacador_chefes": "melee",
    "primordial_origem": "siege", "primordial_trono": "melee",
    "primordial_tempestade": "siege", "primordial_abismo": "siege",
    "primordial_eternidade": "melee",
}


@dataclass(frozen=True, slots=True)
class Carta:
    id: str
    nome: str
    categoria: str
    tipo: str
    poder: int
    raridade: str
    custo: int
    habilidade: str
    descricao: str = ""
    jogo_origem: str = ""
    fileira: str = ""

    def para_dict(self) -> dict[str, Any]:
        """Serializa somente campos canônicos do Gwent; nunca expõe categorias antigas."""
        data = asdict(self)
        faccoes = {"Força": "Ordem Áurea", "Destreza": "Véu Carmesim", "Magia": "Lua Negra"}
        fileiras = {"Força": "melee", "Destreza": "ranged", "Magia": "siege"}
        papeis = {
            ("Força", "melee"): "Vanguarda",
            ("Força", "ranged"): "Batedor de Guerra",
            ("Força", "siege"): "Artilheiro",
            ("Destreza", "melee"): "Duelista",
            ("Destreza", "ranged"): "Batedor",
            ("Destreza", "siege"): "Atirador de Elite",
            ("Magia", "melee"): "Guardião Rúnico",
            ("Magia", "ranged"): "Invocador",
            ("Magia", "siege"): "Arcanista",
        }
        especial = str(self.categoria or "").casefold() == "especial"
        faccao = FACCOES_IDENTIDADE_POR_CARTA.get(self.id, faccoes.get(self.tipo, "Ordem Áurea"))
        fileira = self.fileira or FILEIRAS_POR_CARTA.get(self.id, fileiras.get(self.tipo, "melee"))
        if fileira not in {"melee", "ranged", "siege"}:
            fileira = fileiras.get(self.tipo, "melee")
        data.update({
            "categoria": "Especial" if especial else "Unidade",
            "faccao": faccao,
            "fileira": fileira,
            "papel_gwent": "Tática" if especial else papeis[(self.tipo, fileira)],
            # Campos de compatibilidade não carregam mais nomes de categorias antigas.
            "categoria_arte": "Especial" if especial else "Unidade",
            "categoria_origem": "Especial" if especial else "Unidade",
            "jogo_origem": "",
        })
        return data


# Catálogo inicial. As cartas de jogos e patentes são geradas deterministicamente.
_CARTAS_BASE = [
    # Chefes
    Carta("chefe_guardiao_cinzas", "Cavaleiro da Árvore Áurea", "Chefe", "Força", 5, "Rara", 2, "quebra_ritmo", "Um sentinela montado patrulha os caminhos que conduzem à Árvore Áurea, impondo a autoridade da capital."),
    Carta("chefe_dama_vazio", "Ranni, Bruxa da Lua", "Chefe", "Magia", 6, "Épica", 3, "ultimo_folego", "A princesa lunar rompeu com os Dois Dedos e busca um destino independente da Vontade Maior."),
    Carta("chefe_cervo_sombrio", "Cavaleiro do Cão de Caça", "Chefe", "Destreza", 4, "Comum", 1, "contragolpe", "Um cavaleiro errante segue a trilha de presas pelas florestas enevoadas das Terras Intermédias."),
    Carta("chefe_rei_afogado", "Godfrey, Primeiro Lorde Prístino", "Chefe", "Força", 7, "Épica", 3, "primeira_luz", "Primeiro Lorde Prístino e consorte de Marika, Godfrey liderou os guerreiros que conquistaram as Terras Intermédias."),
    Carta("chefe_oraculo_ruina", "Gurranq, Clérigo Bestial", "Chefe", "Magia", 7, "Lendária", 4, "impeto", "O clérigo bestial consome Raiz da Morte e guarda um segredo ligado à própria Runa da Morte."),
    Carta("chefe_cacador_sem_rosto", "Assassina da Faca Negra", "Chefe", "Destreza", 5, "Rara", 2, "retaliacao", "Uma assassina Numen ligada à Noite das Facas Negras, quando um fragmento da Runa da Morte foi usado para matar Godwyn."),
    Carta("chefe_vigia_cinzento", "Cavaleiro de Leyndell", "Chefe", "Força", 4, "Comum", 1, "drenagem", "Um soldado da capital mantém a vigília entre as muralhas erguidas em nome da Ordem Áurea."),
    Carta("chefe_aparicao_veio", "Lâmina Negra Errante", "Chefe", "Destreza", 3, "Comum", 1, "adaptacao", "Uma figura encapuzada atravessa as sombras, deixando apenas o rumor de uma lâmina silenciosa."),
    Carta("chefe_malenia_lamina_miquella", "Malenia, Lâmina de Miquella", "Chefe", "Destreza", 9, "Primordial", 4, "drenagem", "Espadachim lendária e irmã gêmea de Miquella, luta enquanto a Podridão Escarlate consome seu corpo."),
    Carta("chefe_radahn_flagelo_estrelas", "Radahn, Flagelo das Estrelas", "Chefe", "Força", 9, "Primordial", 4, "quebra_ritmo", "General temido da Fragmentação, dominou a gravidade para deter o curso das estrelas e permaneceu em Caelid após a Podridão."),
    Carta("chefe_maliketh_morte_destinada", "Maliketh, Lâmina Negra", "Chefe", "Força", 8, "Lendária", 4, "cacador_arcano", "Sombra leal de Marika e guardião da Runa da Morte, carrega a Morte Destinada selada em sua lâmina."),
    Carta("chefe_messmer_impalador", "Messmer, o Empalador", "Chefe", "Força", 8, "Lendária", 4, "quebra_ritmo", "Filho de Marika e senhor da chama impura, comandou a purga que devastou o Reino das Sombras."),
    Carta("chefe_placidusax_lorde_dragao", "Placidusax, Lorde Dragão", "Chefe", "Magia", 9, "Primordial", 4, "olho_tempestade", "Lorde Dragão ancestral que aguarda, em Farum Azula, o retorno de seu deus desaparecido."),
    # Armas
    Carta("arma_lamina_peregrino", "Duelista da Casa Hoslow", "Arma", "Destreza", 4, "Comum", 1, "primeira_luz", "Herdeiro de uma casa de duelistas, transforma a elegância do aço em uma promessa de sangue."),
    Carta("arma_martelo_fornalha", "Ferreiro de Volcano Manor", "Arma", "Força", 6, "Rara", 2, "encadeamento", "Entre fornalhas e juramentos de traição, um artesão molda armas para os recusantes do Monte Gelmir."),
    Carta("arma_cajado_marulho", "Feiticeiro Cariano", "Arma", "Magia", 5, "Rara", 2, "cacador_arcano", "Discípulo da realeza cariana, conjura feitiçarias de pedra cintilante sob a proteção da lua."),
    Carta("arma_duas_luas", "Espadachim da Lua Negra", "Arma", "Destreza", 7, "Épica", 3, "precisao", "Um duelista das tradições carianas conduz a lâmina sob a luz fria da Lua Negra."),
    Carta("arma_grande_sino", "Sentinela do Portão de Leyndell", "Arma", "Força", 8, "Lendária", 4, "instinto", "Um guardião de elite protege os acessos da capital e enfrenta qualquer ameaça à ordem dourada."),
    Carta("arma_agulha_astro", "Leitora de Estrelas de Sellia", "Arma", "Magia", 3, "Comum", 1, "primeira_luz", "Uma estudiosa de Sellia observa os astros e procura caminhos ocultos na feitiçaria noturna."),
    Carta("arma_lanca_fornalha", "Lanceiro da Árvore Áurea", "Arma", "Força", 4, "Comum", 1, "primeira_luz", "Treinado para defender os domínios da Árvore Áurea, avança com lança e disciplina militar."),
    Carta("arma_arco_peregrino", "Batedor da Mansão Vulcânica", "Arma", "Destreza", 5, "Comum", 1, "impeto", "Um recusante percorre os caminhos do Monte Gelmir, atento às rotas e aos movimentos dos inimigos."),
    # Magias
    Carta("magia_brasa_errante", "Monge do Fogo", "Magia", "Magia", 3, "Comum", 1, "sangue_frio", "Devoto do fogo dos gigantes, preserva ritos antigos nas encostas geladas dos Picos dos Gigantes."),
    Carta("magia_selo_vigilia", "Confessora da Ordem Áurea", "Magia", "Destreza", 5, "Rara", 2, "adaptacao", "Treinada para agir discretamente, a Confessora combina devoção, infiltração e combate próximo."),
    Carta("magia_trovao_oco", "Dragoeiro Ancião", "Magia", "Força", 6, "Épica", 3, "drenagem", "Um guerreiro ligado aos antigos dragões canaliza relâmpagos ancestrais em meio à batalha."),
    Carta("magia_nevoa_antiga", "Astróloga de Liurnia", "Magia", "Magia", 7, "Épica", 3, "encadeamento", "Sob os céus de Liurnia, uma astróloga procura nas estrelas sinais de destinos ainda ocultos."),
    Carta("magia_sol_negro", "Apóstolo da Pele Divina", "Magia", "Magia", 8, "Lendária", 4, "quebra_ritmo", "Devoto da antiga ordem da Pele Divina, empunha a chama negra associada à morte dos deuses."),
    Carta("magia_fagulha", "Aprendiz de Feitiçaria Cariana", "Magia", "Destreza", 4, "Comum", 1, "cacador_arcano", "Um aprendiz da tradição cariana começa a dominar os projéteis de pedra cintilante."),
    Carta("magia_orbe_eco", "Erudito da Academia", "Magia", "Magia", 4, "Comum", 1, "precisao", "Pesquisador de Raya Lucaria, dedica a vida ao estudo dos segredos das pedras cintilantes."),
    Carta("magia_chama_fria", "Feiticeira da Lua Gélida", "Magia", "Magia", 3, "Comum", 1, "sangue_frio", "Uma feiticeira errante combina o frio das antigas artes lunares com chamas de origem desconhecida."),
    # Covenants / juramentos
    Carta("covenant_lobos_cinza", "Cavaleiros de Radahn", "Covenant", "Força", 5, "Rara", 2, "instinto", "Veteranos da hoste do Flagelo das Estrelas, marcham sob o estandarte do general de Caelid."),
    Carta("covenant_lua_velada", "Juramentada de Ranni", "Covenant", "Destreza", 6, "Épica", 3, "primeira_luz", "Uma aliada juramentada à princesa lunar acompanha sua busca por um caminho além da Ordem Áurea."),
    Carta("covenant_sentinelas", "Guardiões de Sellia", "Covenant", "Magia", 4, "Comum", 1, "adaptacao", "Vigias da cidade oculta de Sellia protegem seus segredos e as passagens de feitiçaria."),
    Carta("covenant_coroa_abismo", "Cavaleiro da Dinastia Mohgwyn", "Covenant", "Força", 7, "Lendária", 4, "drenagem", "Um guerreiro jurado à dinastia sanguínea guarda os domínios ocultos de Mohg."),
    Carta("covenant_ultimos", "Cavaleiros de sangue juramentados", "Covenant", "Destreza", 5, "Rara", 2, "ultimo_folego", "Combatentes unidos por juramentos de sangue permanecem ao lado de seu senhor até o último fôlego."),
    Carta("covenant_filhos_brasa", "Discípulos do Monge do Fogo", "Covenant", "Força", 5, "Comum", 1, "contragolpe", "Seguidores dos antigos monges preservam a chama dos gigantes e seus rituais esquecidos."),
    Carta("covenant_peregrinos_nevoa", "Peregrinos da Cidade Eterna", "Covenant", "Destreza", 4, "Comum", 1, "primeira_luz", "Viajantes das cidades subterrâneas cruzam a escuridão em busca de uma nova estrela."),
    Carta("covenant_irmandade_ferro", "Guardas da Árvore Áurea", "Covenant", "Força", 4, "Comum", 1, "retaliacao", "Defensores juramentados protegem os caminhos e santuários consagrados à Árvore Áurea."),
    # Cartas especiais do modo Gwent: entram na coleção por recompensas/pacotes do Discord.
    Carta("gwent_especial_nevoa", "Miasma da Podridão", "Especial", "Magia", 0, "Rara", 2, "gwent_nevoa", "Uma nuvem pútrida se espalha pelo campo, lembrando os pântanos corrompidos de Caelid."),
    Carta("gwent_especial_geada", "Geada dos Picos dos Gigantes", "Especial", "Magia", 0, "Rara", 2, "gwent_geada", "O frio dos Picos dos Gigantes avança sobre o campo e silencia o vigor dos combatentes."),
    Carta("gwent_especial_chuva", "Sangue Corrompido", "Especial", "Destreza", 0, "Comum", 1, "gwent_chuva", "Um rito sanguíneo mancha o campo de batalha com a promessa de uma dívida ainda não paga."),
    Carta("gwent_especial_chifre", "Rugido de Godfrey", "Especial", "Força", 0, "Épica", 3, "gwent_chifre", "O rugido do Primeiro Lorde Prístino ecoa entre as fileiras e reacende a coragem dos guerreiros."),
    Carta("gwent_especial_medico", "Lágrima Sagrada", "Especial", "Destreza", 0, "Rara", 2, "gwent_medico", "Uma lágrima consagrada guarda a memória dos que tombaram e ainda podem retornar à jornada."),
    Carta("gwent_especial_queima", "Chama Negra", "Especial", "Magia", 0, "Épica", 3, "gwent_queima", "A chama negra, temida até pelos deuses, consome tudo o que toca."),
    Carta("gwent_especial_purificar", "Lei da Regressão", "Especial", "Magia", 0, "Rara", 2, "gwent_purificar", "A Lei da Regressão revela a verdade por trás das ilusões e desfaz os véus que encobrem o mundo."),
    Carta("gwent_especial_execucao", "Lâmina da Morte Destinada", "Especial", "Força", 0, "Épica", 3, "gwent_execucao", "A lâmina da Morte Destinada carrega o fragmento de um poder que deveria permanecer selado."),
    Carta("gwent_especial_vinculo", "Juramento do Crisol", "Especial", "Força", 0, "Rara", 2, "gwent_vinculo", "Um juramento ancestral une os guerreiros às formas primordiais que precederam a Erdtree."),
    Carta("gwent_especial_batedor", "Passo do Cão de Caça", "Especial", "Destreza", 0, "Rara", 2, "gwent_batedor", "O passo do cão de caça atravessa o campo antes que o inimigo perceba sua aproximação."),
    Carta("gwent_especial_muralha", "Bastião de Leyndell", "Especial", "Força", 0, "Comum", 1, "gwent_muralha", "As muralhas douradas de Leyndell erguem-se como símbolo da resistência da capital."),
    # Táticas de estado inspiradas nos efeitos de Elden Ring.
    Carta("elden_especial_sangramento", "Ritual de Sangue", "Especial", "Destreza", 0, "Rara", 2, "gwent_sangramento", "O ritual desperta o poder do sangue e transforma cada ferida em um presságio de ruína."),
    Carta("elden_especial_geada", "Lua Cheia de Rennala", "Especial", "Magia", 0, "Rara", 2, "gwent_geada_cariana", "A lua cheia de Rennala ilumina o campo com a frieza ancestral da realeza cariana."),
    Carta("elden_especial_podrida", "Flor da Podridão Escarlate", "Especial", "Magia", 0, "Épica", 3, "gwent_podrida", "A flor escarlate floresce onde a podridão encontra carne, pedra e memória."),
    Carta("elden_especial_loucura", "Chama Frenética", "Especial", "Magia", 0, "Épica", 3, "gwent_loucura", "A chama frenética consome razão e identidade, deixando apenas o caos da Chama Frenética."),
    Carta("elden_especial_chama", "Chama do Gigante", "Especial", "Força", 0, "Rara", 2, "gwent_chama", "A chama dos gigantes arde contra o frio que tenta aprisionar os vivos."),
    Carta("elden_especial_invocacao", "Cinzas dos Lobos Solitários", "Especial", "Magia", 0, "Rara", 2, "gwent_invocacao", "Cinzas antigas despertam os espíritos de lobos que outrora caçaram ao lado de seus mestres."),
    # V19 — Relíquias: cada jogador pode ativar apenas uma por partida.
    Carta("reliquia_grande_runa_godrick", "Grande Runa de Godrick", "Especial", "Força", 0, "Lendária", 3, "reliquia_godrick", "Fragmento do Anel Prístino reivindicado por Godrick, o Enxertado, que buscava poder por meio do enxerto."),
    Carta("reliquia_runa_nao_nascidos", "Grande Runa dos Não Nascidos", "Especial", "Magia", 0, "Lendária", 3, "reliquia_renala", "A Grande Runa guardada por Rennala conserva o poder do renascimento e da perfeição inacabada."),
    Carta("reliquia_runa_morte", "Runa da Morte", "Especial", "Destreza", 0, "Mítica", 4, "reliquia_morte", "O fragmento da Morte Destinada recorda o poder que Maliketh recebeu para manter selado."),
    Carta("reliquia_noite_chama", "Espada da Noite e da Chama", "Especial", "Magia", 0, "Lendária", 3, "reliquia_noite_chama", "Arma lendária da Mansão Cariana. Sua postura especial libera um ataque mágico ou uma onda de fogo."),
    Carta("reliquia_lamina_negra", "Lâmina Negra", "Especial", "Destreza", 0, "Mítica", 4, "reliquia_lamina_negra", "A arma de Maliketh, que guarda a Morte Destinada selada em sua lâmina. Não é uma das adagas usadas pelas Assassinas da Faca Negra."),
    Carta("reliquia_algemas_margit", "Algemas de Margit", "Especial", "Força", 0, "Épica", 2, "reliquia_algemas", "Correntes forjadas para conter o Agouro caído, capazes de subjugar até mesmo um inimigo temível."),
    # Novas unidades de facção e sinergia.
    Carta("gwent_unidade_baluarte", "Cavaleiro do Crisol", "Chefe", "Força", 6, "Rara", 2, "guardiao_fileira", "Um cavaleiro do Crisol, marcado pelas antigas formas que antecederam a Árvore Áurea, guarda a formação com disciplina."),
    Carta("gwent_unidade_lamina_sem_juramento", "Caçador de Dedos", "Arma", "Destreza", 6, "Rara", 2, "cacador_solitario", "Caçador de Dedos, um duelista errante que prefere trilhas solitárias e confrontos sem testemunhas."),
    Carta("gwent_unidade_portaestandarte", "Porta-estandarte de Leyndell", "Covenant", "Força", 4, "Comum", 1, "estandarte", "O estandarte de Leyndell reúne soldados dispersos sob o símbolo dourado da capital."),
    Carta("gwent_unidade_oraculo_clima", "Profeta de Liurnia", "Magia", "Magia", 5, "Rara", 2, "resistencia_climatica", "O profeta de Liurnia observa as mudanças do céu e interpreta os sinais trazidos por tempestades e geadas."),
    Carta("gwent_unidade_eco", "Erudito das Pedras Cintilantes", "Magia", "Magia", 5, "Rara", 2, "eco_arcano", "Um estudioso das pedras cintilantes investiga as ressonâncias deixadas por feitiçarias antigas."),
    Carta("gwent_unidade_cavaleira", "Cavaleira Cariana", "Chefe", "Destreza", 5, "Comum", 1, "quebra_ritmo", "Uma duelista cariana, treinada nas tradições de combate da realeza lunar."),
    Carta("gwent_unidade_gigante", "Gigante de Fogo", "Chefe", "Força", 7, "Épica", 3, "instinto", "Uma presença colossal na linha de frente."),
    Carta("gwent_unidade_cartografa", "Exploradora da Cidade Eterna", "Covenant", "Destreza", 4, "Comum", 1, "adaptacao", "Encontra rotas onde os outros veem obstáculos."),
    Carta("gwent_unidade_invocador", "Apóstolo da Pele Divina Errante", "Magia", "Magia", 7, "Épica", 3, "cacador_arcano", "Converte conhecimento arcano em força de combate."),
    Carta("gwent_unidade_mestre_forja", "Mestre Ferreiro de Volcano Manor", "Chefe", "Força", 5, "Rara", 2, "dupla_fornalha", "Um mestre ferreiro de Volcano Manor trabalha entre brasas, aço e os juramentos dos recusantes."),
    Carta("gwent_unidade_dupla_veu", "Gêmeas da Cidade Eterna", "Covenant", "Destreza", 5, "Rara", 2, "irmandade_veu", "Duas irmãs das Cidades Eternas percorrem caminhos subterrâneos que raramente aparecem nos mapas."),
    Carta("gwent_unidade_circulo", "Discípulo da Academia", "Magia", "Magia", 5, "Rara", 2, "circulo_arcano", "Discípulo de Raya Lucaria, dedica-se ao estudo dos círculos arcanos e dos resíduos de feitiçaria."),

    # Etapa 2: unidades de facção que usam os efeitos de ciclo de vida (escudo, queda, ressurreição...).
    # Ordem Áurea — muralha (escudo/sobrevivência/vingança) e banquete (devorar/espólios).
    Carta("gwent_unidade_sentinela_rubra", "Cavaleiro de Radahn", "Covenant", "Força", 4, "Comum", 1, "escudo_ferro", "Um cavaleiro da hoste de Radahn mantém sua posição sob o estandarte vermelho de Caelid."),
    Carta("gwent_unidade_veterano_cercos", "Cavaleiro Draconiano", "Chefe", "Força", 5, "Rara", 2, "sobrevivente", "Já viu mais muralhas caírem do que rostos conhecidos."),
    Carta("gwent_unidade_herdeiro_portao", "Godwyn, o Dourado", "Chefe", "Força", 6, "Épica", 3, "vinganca", "Godwyn, herdeiro da linhagem dourada, carrega o peso de uma antiga promessa ligada à capital."),
    Carta("gwent_unidade_carniceiro_forja", "Carrasco de Volcano Manor", "Arma", "Força", 4, "Rara", 2, "devorar", "Um carrasco de Volcano Manor cumpre ordens entre as fornalhas e os juramentos dos recusantes."),
    Carta("gwent_unidade_intendente", "Mercador Nômade", "Covenant", "Força", 3, "Comum", 1, "espolios", "Um mercador nômade percorre as Terras Intermédias levando provisões e notícias entre assentamentos."),
    # Lua Negra — fantasmas (retorno e persistência) e caravana (saque e blindagem).
    Carta("gwent_unidade_cacadora_fantasma", "Assassina de Ravenmount", "Chefe", "Destreza", 5, "Rara", 2, "sobrevivente", "Uma assassina de Ravenmount atravessa a névoa sem deixar rastros fáceis de seguir."),
    Carta("gwent_unidade_cantora_lamentos", "Fia, Companheira do Leito de Morte", "Covenant", "Destreza", 4, "Rara", 2, "ressurgir", "Fia, Companheira do Leito de Morte, entoa lamentos pelos que encontraram repouso entre os mortos."),
    Carta("gwent_unidade_senhor_cacada", "Blaidd, o Meio-Lobo", "Chefe", "Destreza", 6, "Épica", 3, "vinganca", "Blaidd, o Meio-Lobo, é um guerreiro ligado a Ranni e à antiga linhagem dos lobos das Terras Intermédias."),
    Carta("gwent_unidade_saqueadora_veu", "Ladina da Cidade Eterna", "Arma", "Destreza", 4, "Comum", 1, "espolios", "Nenhuma rota é cara demais para quem leva o butim."),
    Carta("gwent_unidade_contrabandista", "Recusante da Mansão Vulcânica", "Covenant", "Destreza", 4, "Comum", 1, "escudo_ferro", "Um recusante de Volcano Manor, acostumado a negociar favores e segredos nas encostas do Monte Gelmir."),
    # Véu Carmesim — rúnico (proteção e retorno) e eclipse (consumo e conhecimento).
    Carta("gwent_unidade_guardiao_runas", "Guardião da Ordem Áurea", "Magia", "Magia", 5, "Comum", 1, "escudo_ferro", "Um guardião da Ordem Áurea carrega inscrições rúnicas ligadas aos ensinamentos da capital."),
    Carta("gwent_unidade_necromante", "Servo dos que Vivem na Morte", "Magia", "Magia", 4, "Rara", 2, "ressurgir", "Um servo dos que Vivem na Morte segue os ritos que desafiam a ordem natural da morte."),
    Carta("gwent_unidade_detonador", "Guerreiro da Chama Frenética", "Arma", "Magia", 6, "Épica", 3, "vinganca", "Um guerreiro marcado pela Chama Frenética percorre as Terras Intermédias em busca de novos devotos."),
    Carta("gwent_unidade_devorador_mana", "Cavaleiro de Sangue de Mohg", "Magia", "Magia", 5, "Rara", 2, "devorar", "Um cavaleiro ligado ao sangue de Mohg participa dos rituais sombrios da dinastia subterrânea."),
    Carta("gwent_unidade_bibliotecaria", "Bibliotecária de Raya Lucaria", "Covenant", "Magia", 4, "Comum", 1, "espolios", "O conhecimento reunido na guerra vale mais que ouro."),

    # Etapa 2: cartas especiais novas (todas funcionam sem alvo escolhido; `target_id` apenas refina).
    Carta("gwent_especial_egide", "Bênção da Árvore Áurea", "Especial", "Força", 0, "Rara", 2, "gwent_egide", "Uma bênção da Árvore Áurea, invocada pelos guerreiros que buscam a proteção da capital."),
    Carta("gwent_especial_requiem", "Chamado dos Mortos", "Especial", "Magia", 0, "Épica", 3, "gwent_requiem", "Um chamado antigo ecoa entre os mortos e convida os guerreiros caídos a retornarem à batalha."),
    Carta("gwent_especial_passo", "Passo do Lobo", "Especial", "Destreza", 0, "Rara", 2, "gwent_passo", "O Passo do Lobo representa a velocidade e a precisão dos caçadores que cruzam as Terras Intermédias."),
    Carta("gwent_mitica_coroa", "Cavaleiro Consagrado do Haligtree", "Relíquia", "Força", 8, "Mítica", 5, "estandarte", "Um cavaleiro consagrado guarda os caminhos do Haligtree e permanece fiel à promessa de Miquella."),
    Carta("gwent_singular_primeiro", "Juramento Primordial do Crisol", "Relíquia", "Destreza", 10, "Singular", 0, "cacador_solitario", "Exemplar singular conquistado por um feito extraordinário."),
    Carta("gwent_singular_intocavel", "Adaga da Faca Negra", "Relíquia", "Destreza", 9, "Singular", 0, "precisao", "Conquistada ao concluir um desafio sem sofrer dano."),
    Carta("gwent_singular_nivel1", "Vontade de Marika", "Relíquia", "Força", 10, "Singular", 0, "ultimo_folego", "Conquistada ao vencer um desafio no nível um."),
    Carta("gwent_singular_cacador_chefes", "Coroa do Lorde Prístino", "Relíquia", "Magia", 9, "Singular", 0, "paradoxo_eterno", "Conquistada ao derrotar todos os chefes de um desafio."),
]

CARTAS_PRIMORDIAIS = [
    Carta("primordial_origem", "Besta Prístina, Arauto da Vontade Maior", "Relíquia", "Força", 8, "Primordial", 4, "lei_primeva", "A Besta Prístina manifesta a vontade que veio além das estrelas e deu forma à ordem dourada."),
    Carta("primordial_trono", "Marika, Rainha Eterna", "Relíquia", "Força", 8, "Primordial", 4, "decreto_soberano", "Marika, a Rainha Eterna, ergueu a ordem dourada e rompeu o Anel Prístino, mudando para sempre as Terras Intermédias."),
    Carta("primordial_tempestade", "Placidusax, Senhor Dragão", "Relíquia", "Destreza", 8, "Primordial", 4, "olho_tempestade", "Placidusax, antigo lorde dos dragões, permanece suspenso no tempo em Farum Azula."),
    Carta("primordial_abismo", "Mãe Sem Forma", "Relíquia", "Destreza", 8, "Primordial", 4, "fome_abismo", "A Mãe Sem Forma é venerada pelos seguidores de Mohg como origem do poder sanguíneo."),
    Carta("primordial_eternidade", "Maliketh, Guardião da Morte Destinada", "Relíquia", "Força", 8, "Primordial", 4, "paradoxo_eterno", "Maliketh guarda a Morte Destinada, o poder cuja ausência sustenta a ordem sem morte de Marika."),
]
# V18 — metade das unidades usa força pura, sem habilidade especial.
# Priorizamos cartas Comuns e completamos a meta com cartas Raras; Épicas+ preservam efeitos.
_unidades_v18 = [c for c in [*_CARTAS_BASE, *CARTAS_PRIMORDIAIS] if c.categoria.casefold() != "especial"]
_protegidas_com_efeito_v18 = {"chefe_guardiao_cinzas", "covenant_irmandade_ferro"}
_sem_efeito_v18 = [c for c in _unidades_v18 if c.raridade == "Comum" and c.id not in _protegidas_com_efeito_v18]
_meta_sem_efeito_v18 = (len(_unidades_v18) // 2) + 2  # reserva duas unidades sem efeito para equilibrar as patentes geradas
_faltam_v18 = max(0, _meta_sem_efeito_v18 - len(_sem_efeito_v18))
_sem_efeito_v18 += sorted(
    [c for c in _unidades_v18 if c.raridade == "Rara" and c.id not in _protegidas_com_efeito_v18],
    key=lambda c: hashlib.sha256(c.id.encode("utf-8")).hexdigest(),
)[:_faltam_v18]
CARTAS_SEM_EFEITO_IDS = frozenset(c.id for c in _sem_efeito_v18)
_cartas_v18 = []
for _c in [*_CARTAS_BASE, *CARTAS_PRIMORDIAIS]:
    if _c.id in CARTAS_SEM_EFEITO_IDS:
        _poder = min(FAIXA_PODER[_c.raridade][1], _c.poder + 1)
        _cartas_v18.append(Carta(_c.id, _c.nome, _c.categoria, _c.tipo, _poder, _c.raridade, _c.custo, "", _c.descricao, _c.jogo_origem, _c.fileira))
    else:
        _cartas_v18.append(_c)
_CARTAS_BASE = [c for c in _cartas_v18 if c.id not in {x.id for x in CARTAS_PRIMORDIAIS}]
CARTAS_PRIMORDIAIS = [c for c in _cartas_v18 if c.id in {x.id for x in CARTAS_PRIMORDIAIS}]

# Expansão V75 — 12 unidades novas, quatro por facção.
# As cartas entram após o balanceamento legado V18 para preservar suas habilidades próprias.
CARTAS_EXPANSAO_V75 = [
    # ORDEM ÁUREA — formação, proteção e purificação.
    Carta("gwent_v75_ordem_veterano_juramento", "Veterano do Juramento Dourado", "Covenant", "Força", 4, "Rara", 2, "", "Veterano de Leyndell, endurecido pelas campanhas da capital e fiel à Árvore Áurea.", fileira="melee"),
    Carta("gwent_v75_ordem_guardiao_crisol", "Guardião do Crisol Menor", "Chefe", "Força", 4, "Rara", 2, "", "Guardião treinado nos antigos rituais do Crisol, mantém a disciplina entre os guerreiros de Leyndell.", fileira="melee"),
    Carta("gwent_v75_ordem_confessora_graca", "Confessora da Graça Serena", "Magia", "Força", 5, "Épica", 3, "", "Confessora da Ordem Áurea, estuda a Lei da Regressão e protege os ritos de purificação da capital.", fileira="siege"),
    Carta("gwent_v75_ordem_arauto_estandarte", "Arauto do Estandarte Áureo", "Covenant", "Força", 5, "Épica", 3, "", "Arauto de Leyndell, carrega o estandarte dourado que reúne os soldados da capital.", fileira="ranged"),

    # VÉU CARMESIM — marcas de Sangramento, pressão e sacrifício calculado.
    Carta("gwent_v75_veu_acolito_sangue", "Acólito da Dinastia Sanguínea", "Magia", "Destreza", 4, "Rara", 2, "", "Servo do Palácio de Mohgwyn, participa dos rituais de sangue dedicados ao Senhor do Sangue.", fileira="ranged"),
    Carta("gwent_v75_veu_devota_hemorragia", "Devota da Hemorragia", "Covenant", "Destreza", 4, "Rara", 2, "", "Devota da Hemorragia, oferece preces ao Senhor do Sangue nos salões subterrâneos de Mohgwyn.", fileira="siege"),
    Carta("gwent_v75_veu_carrasco_preco", "Carrasco da Procissão Carmesim", "Chefe", "Destreza", 5, "Épica", 3, "", "Carrasco da Procissão Carmesim, executa sentenças em nome da dinastia sanguínea.", fileira="melee"),
    Carta("gwent_v75_veu_cacador_sangue", "Caçador das Catacumbas de Mohgwyn", "Arma", "Destreza", 5, "Épica", 3, "", "Caçador das Catacumbas de Mohgwyn, persegue aqueles que tentam escapar dos rituais da dinastia.", fileira="ranged"),

    # LUA NEGRA — Geada, leitura de campo e controle gravitacional.
    Carta("gwent_v75_lua_oraculo_geada", "Oráculo Gélido de Sellia", "Magia", "Magia", 4, "Rara", 2, "", "Astróloga de Sellia, estuda as correntes de frio associadas às antigas artes lunares.", fileira="siege"),
    Carta("gwent_v75_lua_cartografo_lunar", "Cartógrafo das Cidades Eternas", "Covenant", "Magia", 4, "Rara", 2, "", "Cartógrafo das Cidades Eternas, registra passagens subterrâneas e caminhos sob as estrelas.", fileira="ranged"),
    Carta("gwent_v75_lua_graviturgista", "Graviturgista de Nokron", "Magia", "Magia", 5, "Épica", 3, "", "Graviturgista de Nokron, pesquisa forças capazes de curvar o movimento dos corpos celestes.", fileira="siege"),
    Carta("gwent_v75_lua_guardia", "Guardiã do Juramento Lunar", "Chefe", "Magia", 5, "Épica", 3, "", "Guardiã juramentada à Lua Negra, protege os caminhos lunares e as alianças das Cidades Eternas.", fileira="melee"),
]

_CARTAS_BASE = [*_CARTAS_BASE, *CARTAS_EXPANSAO_V75]

CARTAS_POR_ID: dict[str, Carta] = {c.id: c for c in [*_CARTAS_BASE, *CARTAS_PRIMORDIAIS]}


def slug_jogo(nome: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(nome or ""))
    ascii_nome = "".join(ch for ch in normalizado if not unicodedata.combining(ch)).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_nome).strip("_") or "jogo_sem_nome"
    # Sufixo estável evita colisões entre títulos que normalizam para o mesmo slug.
    suffix = hashlib.sha256(str(nome or "").casefold().encode("utf-8")).hexdigest()[:6]
    return f"{slug[:62]}_{suffix}"


def _hash_int(valor: str) -> int:
    return int.from_bytes(hashlib.sha256(valor.encode("utf-8")).digest()[:8], "big")


def carta_jogo(nome_jogo: str, marco: str) -> Carta:
    """Cria uma recompensa com nome e território coerentes com seu arquétipo."""
    marco = "platina" if str(marco).lower() == "platina" else "zerado"
    slug = slug_jogo(nome_jogo)
    n = _hash_int(f"{slug}:{marco}:gwent-reward-v2")
    tipo = TIPOS[n % len(TIPOS)]
    raridade = "Épica" if marco == "platina" else "Rara"
    habilidade = HABILIDADES_COMUNS[(n // 7) % len(HABILIDADES_COMUNS)] if (raridade == "Épica" or n % 2 == 0) else ""
    minimo, maximo = FAIXA_PODER[raridade]
    poder = minimo + ((n // 11) % (maximo - minimo + 1))

    identidades = {
        "Força": (
            ("Cavaleiro de Leyndell", ("da Graça Dourada", "da Capital Dourada")),
            ("Sentinela da Árvore Áurea", ("de Leyndell", "da Árvore Áurea")),
            ("Juramentado do Crisol", ("do Crisol", "das Raízes Antigas")),
        ),
        "Destreza": (
            ("Cavaleiro Sanguíneo", ("da Dinastia Sanguínea", "de Mohgwyn")),
            ("Recusante de Volcano Manor", ("do Monte Gelmir", "da Mansão Vulcânica")),
            ("Lâmina de Ravenmount", ("da Névoa", "de Ravenmount")),
        ),
        "Magia": (
            ("Feiticeiro Cariano", ("da Lua Negra", "da Tradição Cariana")),
            ("Astrólogo de Liurnia", ("das Pedras Cintilantes", "de Liurnia")),
            ("Erudito de Raya Lucaria", ("da Academia", "dos Sábios Carianos")),
        ),
    }
    opcoes = identidades[tipo]
    nome_base, epitetos = opcoes[(n // 13) % len(opcoes)]
    epiteto = epitetos[(n // 19) % len(epitetos)]
    selo = hashlib.sha256(f"{slug}:{marco}".encode("utf-8")).hexdigest()[:4].upper()
    titulo = f"{nome_base} {epiteto} · Selo {selo}"

    descricoes = {
        "Força": "Guerreiro da Ordem Áurea, vindo das estradas de Leyndell e marcado pelos juramentos da capital.",
        "Destreza": "Guerreiro do Véu Carmesim, vindo dos salões de Mohgwyn e das rotas do Monte Gelmir.",
        "Magia": "Estudioso da Lua Negra, ligado às tradições carianas e às bibliotecas de Liurnia.",
    }
    descricao = descricoes[tipo]
    descricao += " Recompensa concedida após alcançar a platina." if marco == "platina" else " Recompensa concedida após concluir o jogo."

    return Carta(
        id=f"jogo_{slug}_{marco}", nome=titulo[:95], categoria="Chefe", tipo=tipo,
        poder=int(poder), raridade=raridade, custo=CUSTO_RARIDADE[raridade],
        habilidade=habilidade, descricao=descricao[:240], jogo_origem="",
    )



def carta_patente(indice: int, nivel_minimo: int, nome_patente: str) -> Carta:
    """Gera uma recompensa de patente com título coerente com sua facção."""
    seed = f"patente:{indice}:{nome_patente}:soulsbot-card-v1"
    n = _hash_int(seed)
    if nivel_minimo >= 75:
        raridade = "Lendária"
    elif nivel_minimo >= 30:
        raridade = "Épica"
    elif nivel_minimo >= 10:
        raridade = "Rara"
    else:
        raridade = "Comum"
    minimo, maximo = FAIXA_PODER[raridade]
    poder = minimo + (n % (maximo - minimo + 1))
    tipo = TIPOS[(n // 9) % len(TIPOS)]
    habilidade = HABILIDADES_COMUNS[(n // 17) % len(HABILIDADES_COMUNS)] if (raridade in {"Épica", "Lendária"} or n % 2 == 0) else ""

    nomes_por_tipo = {
        "Força": ("Lorde de Leyndell", "Veterano de Leyndell", "Escudeiro da Árvore Áurea", "Recruta de Leyndell"),
        "Destreza": ("Lorde Sanguíneo", "Cavaleiro de Mohgwyn", "Acólito Sanguíneo", "Recruta de Mohgwyn"),
        "Magia": ("Mestre Cariano", "Feiticeiro Cariano", "Aprendiz Cariano", "Novato de Raya Lucaria"),
    }
    indice_nome = 0 if nivel_minimo >= 75 else 1 if nivel_minimo >= 30 else 2 if nivel_minimo >= 10 else 3
    selo = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:4].upper()
    titulo = f"{nomes_por_tipo[tipo][indice_nome]} · Selo {selo}"

    return Carta(
        id=f"patente_{indice + 1}",
        nome=titulo[:95],
        categoria="Patente",
        tipo=tipo,
        poder=int(poder),
        raridade=raridade,
        custo=CUSTO_RARIDADE[raridade],
        habilidade=habilidade,
        descricao=(f"Recompensa de patente concedida ao alcançar o nível {nivel_minimo}. " + {"Força": "Combatente de Leyndell, reconhecido pelos juramentos da Árvore Áurea.", "Destreza": "Guerreiro do Véu Carmesim, vindo dos caminhos subterrâneos de Mohgwyn.", "Magia": "Estudioso da Lua Negra, ligado às tradições arcanas de Liurnia."}[tipo]),
    )



CARTAS_PATENTE = [carta_patente(i, nivel, nome) for i, (nivel, nome) in enumerate(PATENTES)]
CARTAS_POR_ID.update({c.id: c for c in CARTAS_PATENTE})

# Catálogo estático global usado pelos drops. Patentes e cartas dinâmicas de jogos antigos
# ficam fora do pool; Singular e Primordial possuem fluxos especiais.
CARTAS_PACOTE = [c for c in _CARTAS_BASE]
CARTAS_PACOTE_POR_RARIDADE = {
    raridade: [c for c in [*CARTAS_PACOTE, *CARTAS_PRIMORDIAIS] if c.raridade == raridade]
    for raridade in RARIDADES
}


def get_carta(card_id: str) -> Carta | None:
    if card_id in CARTAS_POR_ID:
        return CARTAS_POR_ID[card_id]
    if str(card_id).startswith("jogo_"):
        m = re.fullmatch(r"jogo_(.+)_(zerado|platina)", str(card_id))
        if m:
            slug, marco = m.groups()
            # O slug não é reversível em nome original; a função é usada após
            # carregar o snapshot persistido ou com o nome de jogo do registro.
            return None
    return None


def carta_de_jogo_por_id(card_id: str, nome_jogo: str) -> Carta:
    carta = carta_jogo(nome_jogo, "platina" if str(card_id).endswith("_platina") else "zerado")
    if carta.id != card_id:
        raise ValueError("ID de carta de jogo não corresponde ao título armazenado.")
    return carta
