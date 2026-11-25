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

VERSAO_ARTES = 25

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
    "primeira_luz": {"nome": "Graça Dourada", "texto": "Recebe +1 de poder ao entrar na primeira rodada."},
    "retaliacao": {"nome": "Retaliação dos Semideuses", "texto": "Recebe +1 de poder quando sua pontuação está abaixo da rival."},
    "impeto": {"nome": "Ímpeto do Lorde", "texto": "Recebe +1 de poder quando sua pontuação está acima da rival."},
    "ultimo_folego": {"nome": "Último Suspiro", "texto": "Recebe +1 de poder na terceira rodada."},
    "contragolpe": {"nome": "Contragolpe", "texto": "Recebe +2 de poder quando sua pontuação está abaixo da rival."},
    "encadeamento": {"nome": "Postura Encadeada", "texto": "Recebe +2 ao jogar na mesma fileira da sua unidade anterior."},
    "adaptacao": {"nome": "Passo do Peregrino", "texto": "Recebe +1 ao jogar em uma fileira diferente da sua última unidade."},
    "sangue_frio": {"nome": "Concentração", "texto": "Recebe +2 quando as pontuações atuais estão empatadas."},
    "instinto": {"nome": "Instinto de Caçador", "texto": "Recebe +2 quando sua pontuação está abaixo da rival."},
    "precisao": {"nome": "Mira Cariana", "texto": "Recebe +1 ao entrar na fileira de longa distância."},
    "drenagem": {"nome": "Selo Enfraquecedor", "texto": "Reduz em 1 o bônus de todas as unidades inimigas, até o limite de -2."},
    "cacador_arcano": {"nome": "Caçador de Feitiços", "texto": "Recebe +1 se o adversário controlar uma unidade da Lua Negra ou qualquer unidade com bônus positivo."},
    "quebra_ritmo": {"nome": "Ruptura de Postura", "texto": "Recebe +1 se o adversário jogou na mesma fileira em seu último turno."},
    # Efeitos exclusivos: somente a respectiva Primordial pode utilizá-los.
    "lei_primeva": {"nome": "Lei Primeva", "texto": "Recebe +2 de poder ao entrar na primeira rodada."},
    "decreto_soberano": {"nome": "Decreto Soberano", "texto": "Reduz em 2 o bônus de todas as unidades inimigas, até o limite de -2."},
    "olho_tempestade": {"nome": "Olho da Tempestade", "texto": "Recebe +2 quando sua fileira estiver sob efeito climático."},
    "fome_abismo": {"nome": "Fome do Abismo", "texto": "Recebe +2 quando sua pontuação está abaixo da rival."},
    "paradoxo_eterno": {"nome": "Paradoxo Eterno", "texto": "Recebe +2 na terceira rodada se o adversário venceu a segunda."},
    "guardiao_fileira": {"nome": "Guardião da Fileira", "texto": "+1 para cada outra unidade sua na mesma fileira, até +3."},
    "cacador_solitario": {"nome": "Caçador Solitário", "texto": "+2 se não houver outra unidade sua na fileira."},
    "estandarte": {"nome": "Estandarte", "texto": "Concede +1 às outras unidades aliadas da mesma fileira."},
    "resistencia_climatica": {"nome": "Resistência Climática", "texto": "Ignora até 2 pontos de penalidade climática; sem clima ativo ao entrar, recebe +1."},
    "eco_arcano": {"nome": "Eco Arcano", "texto": "+2 se você tiver uma carta especial no descarte."},
    "gwent_nevoa": {"nome": "Névoa de Sellia", "texto": "Aplica clima -2 à fileira escolhida: todas as unidades nela perdem 2 de poder efetivo até o fim da rodada."},
    "gwent_geada": {"nome": "Lua Gélida", "texto": "Aplica clima -1 às três fileiras: todas as unidades nelas perdem 1 de poder efetivo até o fim da rodada."},
    "gwent_chuva": {"nome": "Chuva de Estrelas", "texto": "Aplica clima -2 à fileira de cerco: todas as unidades nela perdem 2 de poder efetivo até o fim da rodada."},
    "gwent_chifre": {"nome": "Rugido de Godfrey", "texto": "Concede +2 às suas unidades na fileira escolhida até o fim da rodada."},
    "gwent_medico": {"nome": "Lágrima Sagrada", "texto": "Devolve à sua mão uma unidade do seu descarte com poder-base 4 ou menos; você pode escolher o alvo."},
    "gwent_queima": {"nome": "Chama Negra", "texto": "Tenta remover a unidade de maior poder efetivo de cada lado; um escudo pode bloquear cada remoção."},
    "gwent_purificar": {"nome": "Lei da Regressão", "texto": "Remove todos os efeitos climáticos."},
    "gwent_execucao": {"nome": "Lâmina da Morte Destinada", "texto": "Remove uma unidade inimiga escolhida da fileira selecionada se ela tiver poder efetivo 6 ou menos; um escudo pode bloquear a remoção."},
    "gwent_vinculo": {"nome": "Juramento do Crisol", "texto": "Se houver ao menos duas unidades aliadas na fileira escolhida, concede +2 a todas elas até o fim da rodada."},
    "gwent_batedor": {"nome": "Passo do Cão de Caça", "texto": "Compra uma carta da reserva, se disponível."},
    "gwent_muralha": {"nome": "Bastião de Leyndell", "texto": "Concede +1 às suas unidades na fileira escolhida até o fim da rodada."},
    "vinganca": {"nome": "Vingança", "texto": "Ao cair, concede +1 às unidades aliadas da mesma fileira."},
    "escudo_ferro": {"nome": "Escudo de Ferro", "texto": "Entra com escudo: ignora a primeira remoção sofrida."},
    "ressurgir": {"nome": "Ressurgir", "texto": "Se houver uma unidade elegível, traz do descarte a mais forte com poder base 5 ou menos diretamente ao campo."},
    "devorar": {"nome": "Devorar", "texto": "Ao entrar, consome a unidade aliada de menor poder efetivo na mesma fileira e recebe bônus igual ao poder dela, até +4."},
    "sobrevivente": {"nome": "Sobrevivente", "texto": "Ao fim da rodada, permanece no campo (a mais forte, se houver várias)."},
    "espolios": {"nome": "Espólios", "texto": "Se você vencer a rodada com ela em campo, compra uma carta."},
    "gwent_egide": {"nome": "Bênção da Árvore Áurea", "texto": "Concede escudo a uma unidade sua."},
    "gwent_requiem": {"nome": "Chamado dos Mortos", "texto": "Traz do descarte diretamente ao campo uma unidade com poder base 6 ou menos."},
    "gwent_passo": {"nome": "Passo do Lobo", "texto": "Move uma unidade sua para a fileira escolhida."},
    "dupla_fornalha": {"nome": "Pacto da Fornalha", "texto": "+2 se houver outra unidade de Força na mesma fileira."},
    "irmandade_veu": {"nome": "Formação do Véu", "texto": "+2 se houver uma unidade de Destreza em outra fileira."},
    "circulo_arcano": {"nome": "Círculo de Ressonância", "texto": "+2 se houver Magia aliada na mesma fileira ou especial no descarte."},
    "gwent_sangramento": {"nome": "Sangramento", "texto": "Marca as unidades inimigas da fileira; a segunda marca reduz o bônus em 2 (mínimo -2) e consome as marcas. Marcas expiram no fim da rodada."},
    "gwent_geada_cariana": {"nome": "Geada Cariana", "texto": "Aplica até duas marcas às unidades inimigas da fileira escolhida; cada marca reduz 1 de poder efetivo até o fim da rodada."},
    "gwent_podrida": {"nome": "Podridão Escarlate", "texto": "Cada marca reduz 1 de poder efetivo; a segunda também corrói 1 ponto de bônus positivo, se houver. Marcas expiram no fim da rodada."},
    "gwent_loucura": {"nome": "Loucura Frenética", "texto": "Cada marca reduz 1 de poder efetivo; a segunda remove todos os bônus positivos da unidade. Marcas expiram no fim da rodada."},
    "gwent_chama": {"nome": "Chama do Gigante", "texto": "Remove Geada de todas as suas unidades; cada unidade purificada recebe +1 de poder até o fim da rodada."},
    "gwent_invocacao": {"nome": "Cinzas dos Lobos Solitários", "texto": "Invoca Lobos Espirituais com 3 de poder na fileira escolhida."},
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
        faccao = faccoes.get(self.tipo, "Ordem Áurea")
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
    Carta("chefe_guardiao_cinzas", "Cavaleiro da Árvore Áurea", "Chefe", "Força", 5, "Rara", 2, "quebra_ritmo"),
    Carta("chefe_dama_vazio", "Ranni, Bruxa da Lua", "Chefe", "Magia", 6, "Épica", 3, "ultimo_folego"),
    Carta("chefe_cervo_sombrio", "Cavaleiro do Cão de Caça", "Chefe", "Destreza", 4, "Comum", 1, "contragolpe"),
    Carta("chefe_rei_afogado", "Godfrey, Primeiro Lorde Prístino", "Chefe", "Força", 7, "Épica", 3, "primeira_luz"),
    Carta("chefe_oraculo_ruina", "Gurranq, Clérigo Bestial", "Chefe", "Magia", 7, "Lendária", 4, "impeto"),
    Carta("chefe_cacador_sem_rosto", "Assassino da Faca Negra", "Chefe", "Destreza", 5, "Rara", 2, "retaliacao"),
    Carta("chefe_vigia_cinzento", "Cavaleiro de Leyndell", "Chefe", "Força", 4, "Comum", 1, "drenagem"),
    Carta("chefe_aparicao_veio", "Lâmina Negra Errante", "Chefe", "Destreza", 3, "Comum", 1, "adaptacao"),
    Carta("chefe_malenia_lamina_miquella", "Malenia, Lâmina de Miquella", "Chefe", "Destreza", 9, "Primordial", 4, "drenagem", "Reduz em 1 os bônus de todas as unidades inimigas, até o limite de -2."),
    Carta("chefe_radahn_flagelo_estrelas", "Radahn, Flagelo das Estrelas", "Chefe", "Força", 9, "Primordial", 4, "quebra_ritmo", "Recebe +1 se o adversário jogou na mesma fileira em seu último turno."),
    Carta("chefe_maliketh_morte_destinada", "Maliketh, Lâmina Negra", "Chefe", "Força", 8, "Lendária", 4, "cacador_arcano", "Recebe +1 se o adversário controlar uma unidade da Lua Negra ou qualquer unidade com bônus positivo."),
    Carta("chefe_messmer_impalador", "Messmer, o Empalador", "Chefe", "Força", 8, "Lendária", 4, "quebra_ritmo", "Recebe +1 se o adversário jogou na mesma fileira em seu último turno."),
    Carta("chefe_placidusax_lorde_dragao", "Placidusax, Lorde Dragão", "Chefe", "Magia", 9, "Primordial", 4, "olho_tempestade", "Recebe +2 quando sua fileira estiver sob efeito climático."),
    # Armas
    Carta("arma_lamina_peregrino", "Duelista da Casa Hoslow", "Arma", "Destreza", 4, "Comum", 1, "primeira_luz"),
    Carta("arma_martelo_fornalha", "Ferreiro de Volcano Manor", "Arma", "Força", 6, "Rara", 2, "encadeamento"),
    Carta("arma_cajado_marulho", "Feiticeiro Cariano", "Arma", "Magia", 5, "Rara", 2, "cacador_arcano"),
    Carta("arma_duas_luas", "Espadachim da Lua Negra", "Arma", "Destreza", 7, "Épica", 3, "precisao"),
    Carta("arma_grande_sino", "Sentinela do Portão de Leyndell", "Arma", "Força", 8, "Lendária", 4, "instinto"),
    Carta("arma_agulha_astro", "Leitora de Estrelas de Sellia", "Arma", "Magia", 3, "Comum", 1, "primeira_luz"),
    Carta("arma_lanca_fornalha", "Lanceiro da Árvore Áurea", "Arma", "Força", 4, "Comum", 1, "primeira_luz"),
    Carta("arma_arco_peregrino", "Batedor da Mansão Vulcânica", "Arma", "Destreza", 5, "Comum", 1, "impeto"),
    # Magias
    Carta("magia_brasa_errante", "Monge do Fogo", "Magia", "Magia", 3, "Comum", 1, "sangue_frio"),
    Carta("magia_selo_vigilia", "Confessora da Ordem Áurea", "Magia", "Destreza", 5, "Rara", 2, "adaptacao"),
    Carta("magia_trovao_oco", "Dragoeiro Ancião", "Magia", "Força", 6, "Épica", 3, "drenagem"),
    Carta("magia_nevoa_antiga", "Astróloga de Liurnia", "Magia", "Magia", 7, "Épica", 3, "encadeamento"),
    Carta("magia_sol_negro", "Apóstolo da Pele Divina", "Magia", "Magia", 8, "Lendária", 4, "quebra_ritmo"),
    Carta("magia_fagulha", "Aprendiz de Feitiçaria Cariana", "Magia", "Destreza", 4, "Comum", 1, "cacador_arcano"),
    Carta("magia_orbe_eco", "Erudito da Academia", "Magia", "Magia", 4, "Comum", 1, "precisao"),
    Carta("magia_chama_fria", "Feiticeira da Lua Gélida", "Magia", "Magia", 3, "Comum", 1, "sangue_frio"),
    # Covenants / juramentos
    Carta("covenant_lobos_cinza", "Cavaleiros de Radahn", "Covenant", "Força", 5, "Rara", 2, "instinto"),
    Carta("covenant_lua_velada", "Juramentada de Ranni", "Covenant", "Destreza", 6, "Épica", 3, "primeira_luz"),
    Carta("covenant_sentinelas", "Guardiões de Sellia", "Covenant", "Magia", 4, "Comum", 1, "adaptacao"),
    Carta("covenant_coroa_abismo", "Cavaleiro da Dinastia Mohgwyn", "Covenant", "Força", 7, "Lendária", 4, "drenagem"),
    Carta("covenant_ultimos", "Cavaleiros de sangue juramentados", "Covenant", "Destreza", 5, "Rara", 2, "ultimo_folego"),
    Carta("covenant_filhos_brasa", "Discípulos do Monge do Fogo", "Covenant", "Força", 5, "Comum", 1, "contragolpe"),
    Carta("covenant_peregrinos_nevoa", "Peregrinos da Cidade Eterna", "Covenant", "Destreza", 4, "Comum", 1, "primeira_luz"),
    Carta("covenant_irmandade_ferro", "Guardas da Árvore Áurea", "Covenant", "Força", 4, "Comum", 1, "retaliacao"),
    # Cartas especiais do modo Gwent: entram na coleção por recompensas/pacotes do Discord.
    Carta("gwent_especial_nevoa", "Miasma da Podridão", "Especial", "Magia", 0, "Rara", 2, "gwent_nevoa", "Aplica Podridão Escarlate às unidades inimigas da fileira escolhida; raridades elevadas podem aplicar uma segunda marca."),
    Carta("gwent_especial_geada", "Geada dos Picos dos Gigantes", "Especial", "Magia", 0, "Rara", 2, "gwent_geada", "Aplica Geada a todas as unidades inimigas; raridades elevadas podem aplicar uma segunda marca."),
    Carta("gwent_especial_chuva", "Sangue Corrompido", "Especial", "Destreza", 0, "Comum", 1, "gwent_chuva", "Aplica Sangramento às unidades inimigas de Cerco; a segunda marca causa Hemorragia e reduz bônus."),
    Carta("gwent_especial_chifre", "Rugido de Godfrey", "Especial", "Força", 0, "Épica", 3, "gwent_chifre", "Concede +2 de poder às suas unidades na fileira escolhida até o fim da rodada."),
    Carta("gwent_especial_medico", "Lágrima Sagrada", "Especial", "Destreza", 0, "Rara", 2, "gwent_medico", "Devolve à mão uma unidade com poder base 4 ou menos do seu descarte."),
    Carta("gwent_especial_queima", "Chama Negra", "Especial", "Magia", 0, "Épica", 3, "gwent_queima", "Tenta remover a unidade mais forte de cada lado; escudos podem bloquear a remoção."),
    Carta("gwent_especial_purificar", "Lei da Regressão", "Especial", "Magia", 0, "Rara", 2, "gwent_purificar", "Remove todos os efeitos climáticos das três fileiras."),
    Carta("gwent_especial_execucao", "Lâmina da Morte Destinada", "Especial", "Força", 0, "Épica", 3, "gwent_execucao", "Remove a unidade inimiga escolhida da fileira selecionada se ela tiver poder efetivo 6 ou menos; um escudo pode bloquear a remoção."),
    Carta("gwent_especial_vinculo", "Juramento do Crisol", "Especial", "Força", 0, "Rara", 2, "gwent_vinculo", "Se houver ao menos duas unidades aliadas na fileira escolhida, concede +2 a todas elas até o fim da rodada."),
    Carta("gwent_especial_batedor", "Passo do Cão de Caça", "Especial", "Destreza", 0, "Rara", 2, "gwent_batedor", "Compra uma carta da reserva para sua mão, se ainda houver."),
    Carta("gwent_especial_muralha", "Bastião de Leyndell", "Especial", "Força", 0, "Comum", 1, "gwent_muralha", "Concede +1 às suas unidades na fileira escolhida até o fim da rodada."),
    # Táticas de estado inspiradas nos efeitos de Elden Ring.
    Carta("elden_especial_sangramento", "Ritual de Sangue", "Especial", "Destreza", 0, "Rara", 2, "gwent_sangramento", "Marca as unidades inimigas da fileira; a segunda marca reduz o bônus em 2 (mínimo -2) e consome as marcas. Marcas expiram no fim da rodada."),
    Carta("elden_especial_geada", "Lua Cheia de Rennala", "Especial", "Magia", 0, "Rara", 2, "gwent_geada_cariana", "Aplica até duas marcas de Geada às unidades inimigas da fileira escolhida; cada marca reduz 1 de poder efetivo até o fim da rodada."),
    Carta("elden_especial_podrida", "Flor da Podridão Escarlate", "Especial", "Magia", 0, "Épica", 3, "gwent_podrida", "Cada marca reduz 1 de poder efetivo; a segunda também corrói 1 ponto de bônus positivo, se houver. Marcas expiram no fim da rodada."),
    Carta("elden_especial_loucura", "Chama Frenética", "Especial", "Magia", 0, "Épica", 3, "gwent_loucura", "Cada marca reduz 1 de poder efetivo; a segunda remove todos os bônus positivos das unidades atingidas. Marcas expiram no fim da rodada."),
    Carta("elden_especial_chama", "Chama do Gigante", "Especial", "Força", 0, "Rara", 2, "gwent_chama", "Remove Geada de todas as suas unidades; cada unidade purificada recebe +1 de poder até o fim da rodada."),
    Carta("elden_especial_invocacao", "Cinzas dos Lobos Solitários", "Especial", "Magia", 0, "Rara", 2, "gwent_invocacao", "Invoca Lobos Espirituais com 3 de poder na fileira escolhida. A invocação ocupa uma unidade no campo, mas não consome carta da mão, e vai ao descarte no fim da rodada."),
    # V19 — Relíquias: cada jogador pode ativar apenas uma por partida.
    Carta("reliquia_grande_runa_godrick", "Grande Runa de Godrick", "Especial", "Força", 0, "Lendária", 3, "reliquia_godrick", "Concede +1 de bônus a todas as suas unidades em campo."),
    Carta("reliquia_runa_nao_nascidos", "Grande Runa dos Não Nascidos", "Especial", "Magia", 0, "Lendária", 3, "reliquia_renala", "Purifica Geada e Podridão dos aliados e concede +1 às unidades purificadas."),
    Carta("reliquia_runa_morte", "Runa da Morte", "Especial", "Destreza", 0, "Mítica", 4, "reliquia_morte", "Remove até 2 pontos de bônus da unidade inimiga mais forte em cada fileira."),
    Carta("reliquia_noite_chama", "Espada da Noite e da Chama", "Especial", "Magia", 0, "Lendária", 3, "reliquia_noite_chama", "Escolha: Chama reduz poder de um alvo; Noite aplica Geada a uma fileira inimiga."),
    Carta("reliquia_lamina_negra", "Lâmina Negra", "Especial", "Destreza", 0, "Mítica", 4, "reliquia_lamina_negra", "Reduz em 3 o bônus de uma unidade inimiga; Escudo bloqueia o efeito."),
    Carta("reliquia_algemas_margit", "Algemas de Margit", "Especial", "Força", 0, "Épica", 2, "reliquia_algemas", "Anula os bônus positivos de uma unidade inimiga."),
    # Novas unidades de facção e sinergia.
    Carta("gwent_unidade_baluarte", "Cavaleiro do Crisol", "Chefe", "Força", 6, "Rara", 2, "guardiao_fileira", "Quanto maior a formação aliada, mais difícil é derrubá-lo."),
    Carta("gwent_unidade_lamina_sem_juramento", "Caçador de Dedos", "Arma", "Destreza", 6, "Rara", 2, "cacador_solitario", "Ataca melhor quando opera sem apoio na fileira."),
    Carta("gwent_unidade_portaestandarte", "Porta-estandarte de Leyndell", "Covenant", "Força", 4, "Comum", 1, "estandarte", "Fortalece as demais unidades aliadas na mesma fileira."),
    Carta("gwent_unidade_oraculo_clima", "Profeta de Liurnia", "Magia", "Magia", 5, "Rara", 2, "resistencia_climatica", "Sua visão atravessa tempestades e geadas."),
    Carta("gwent_unidade_eco", "Erudito das Pedras Cintilantes", "Magia", "Magia", 5, "Rara", 2, "eco_arcano", "Canaliza o poder das cartas especiais já utilizadas."),
    Carta("gwent_unidade_cavaleira", "Cavaleira Cariana", "Chefe", "Destreza", 5, "Comum", 1, "quebra_ritmo", "Uma duelista que pune movimentos previsíveis."),
    Carta("gwent_unidade_gigante", "Gigante de Fogo", "Chefe", "Força", 7, "Épica", 3, "instinto", "Uma presença colossal na linha de frente."),
    Carta("gwent_unidade_cartografa", "Exploradora da Cidade Eterna", "Covenant", "Destreza", 4, "Comum", 1, "adaptacao", "Encontra rotas onde os outros veem obstáculos."),
    Carta("gwent_unidade_invocador", "Apóstolo da Pele Divina Errante", "Magia", "Magia", 7, "Épica", 3, "cacador_arcano", "Converte conhecimento arcano em força de combate."),
    Carta("gwent_unidade_mestre_forja", "Mestre Ferreiro de Volcano Manor", "Chefe", "Força", 5, "Rara", 2, "dupla_fornalha", "Luta melhor ao lado de outra unidade da Ordem Áurea."),
    Carta("gwent_unidade_dupla_veu", "Gêmeas da Cidade Eterna", "Covenant", "Destreza", 5, "Rara", 2, "irmandade_veu", "Coordena ataques com aliados posicionados em outra fileira."),
    Carta("gwent_unidade_circulo", "Discípulo da Academia", "Magia", "Magia", 5, "Rara", 2, "circulo_arcano", "Amplifica a magia quando encontra aliados ou resíduos arcanos."),

    # Etapa 2: unidades de facção que usam os efeitos de ciclo de vida (escudo, queda, ressurreição...).
    # Ordem Áurea — muralha (escudo/sobrevivência/vingança) e banquete (devorar/espólios).
    Carta("gwent_unidade_sentinela_rubra", "Cavaleiro de Radahn", "Covenant", "Força", 4, "Comum", 1, "escudo_ferro", "Primeira a receber o golpe, última a recuar."),
    Carta("gwent_unidade_veterano_cercos", "Cavaleiro Draconiano", "Chefe", "Força", 5, "Rara", 2, "sobrevivente", "Já viu mais muralhas caírem do que rostos conhecidos."),
    Carta("gwent_unidade_herdeiro_portao", "Godwyn, o Dourado", "Chefe", "Força", 6, "Épica", 3, "vinganca", "Quando cai, a formação inteira jura vingá-lo."),
    Carta("gwent_unidade_carniceiro_forja", "Carrasco de Volcano Manor", "Arma", "Força", 4, "Rara", 2, "devorar", "Consome os restos da batalha para ampliar a própria força."),
    Carta("gwent_unidade_intendente", "Mercador Nômade", "Covenant", "Força", 3, "Comum", 1, "espolios", "Cada vitória enche os depósitos da Ordem."),
    # Lua Negra — fantasmas (retorno e persistência) e caravana (saque e blindagem).
    Carta("gwent_unidade_cacadora_fantasma", "Assassina de Ravenmount", "Chefe", "Destreza", 5, "Rara", 2, "sobrevivente", "Some na névoa e reaparece quando a próxima rodada começa."),
    Carta("gwent_unidade_cantora_lamentos", "Fia, Companheira do Leito de Morte", "Covenant", "Destreza", 4, "Rara", 2, "ressurgir", "Seu canto arrasta os caídos de volta ao campo."),
    Carta("gwent_unidade_senhor_cacada", "Blaidd, o Meio-Lobo", "Chefe", "Destreza", 6, "Épica", 3, "vinganca", "A presa que o derruba desperta a matilha inteira."),
    Carta("gwent_unidade_saqueadora_veu", "Ladina da Cidade Eterna", "Arma", "Destreza", 4, "Comum", 1, "espolios", "Nenhuma rota é cara demais para quem leva o butim."),
    Carta("gwent_unidade_contrabandista", "Recusante da Mansão Vulcânica", "Covenant", "Destreza", 4, "Comum", 1, "escudo_ferro", "Sempre tem um truque guardado para a primeira emboscada."),
    # Véu Carmesim — rúnico (proteção e retorno) e eclipse (consumo e conhecimento).
    Carta("gwent_unidade_guardiao_runas", "Guardião da Ordem Áurea", "Magia", "Magia", 5, "Comum", 1, "escudo_ferro", "Runas gravadas na pele desviam o primeiro feitiço."),
    Carta("gwent_unidade_necromante", "Servo dos que Vivem na Morte", "Magia", "Magia", 4, "Rara", 2, "ressurgir", "Desperta no campo os que o descarte ainda guarda."),
    Carta("gwent_unidade_detonador", "Guerreiro da Chama Frenética", "Arma", "Magia", 6, "Épica", 3, "vinganca", "Sua queda libera a energia que ele guardava."),
    Carta("gwent_unidade_devorador_mana", "Cavaleiro de Sangue de Mohg", "Magia", "Magia", 5, "Rara", 2, "devorar", "Consome aliados menores para alimentar o ritual de sangue."),
    Carta("gwent_unidade_bibliotecaria", "Bibliotecária de Raya Lucaria", "Covenant", "Magia", 4, "Comum", 1, "espolios", "O conhecimento reunido na guerra vale mais que ouro."),

    # Etapa 2: cartas especiais novas (todas funcionam sem alvo escolhido; `target_id` apenas refina).
    Carta("gwent_especial_egide", "Bênção da Árvore Áurea", "Especial", "Força", 0, "Rara", 2, "gwent_egide", "Concede escudo a uma unidade sua (a escolhida, ou a mais forte sem escudo)."),
    Carta("gwent_especial_requiem", "Chamado dos Mortos", "Especial", "Magia", 0, "Épica", 3, "gwent_requiem", "Traz direto ao campo uma unidade com poder base 6 ou menos do seu descarte (a escolhida, ou a mais forte)."),
    Carta("gwent_especial_passo", "Passo do Lobo", "Especial", "Destreza", 0, "Rara", 2, "gwent_passo", "Move uma unidade sua para a fileira escolhida (a escolhida, ou a mais fraca fora dela)."),
    Carta("gwent_mitica_coroa", "Cavaleiro Consagrado do Haligtree", "Relíquia", "Força", 8, "Mítica", 5, "estandarte", "Uma presença mítica que fortalece a formação aliada."),
    Carta("gwent_singular_primeiro", "Juramento do Crisol", "Relíquia", "Destreza", 10, "Singular", 0, "cacador_solitario", "Exemplar singular conquistado por um feito extraordinário."),
    Carta("gwent_singular_intocavel", "Adaga da Faca Negra", "Relíquia", "Destreza", 9, "Singular", 0, "precisao", "Conquistada ao concluir um desafio sem sofrer dano."),
    Carta("gwent_singular_nivel1", "Vontade de Marika", "Relíquia", "Força", 10, "Singular", 0, "ultimo_folego", "Conquistada ao vencer um desafio no nível um."),
    Carta("gwent_singular_cacador_chefes", "Coroa do Lorde Prístino", "Relíquia", "Magia", 9, "Singular", 0, "paradoxo_eterno", "Conquistada ao derrotar todos os chefes de um desafio."),
]

CARTAS_PRIMORDIAIS = [
    Carta("primordial_origem", "Besta Prístina, Arauto da Vontade Maior", "Relíquia", "Força", 8, "Primordial", 4, "lei_primeva", "Uma cópia por jogador. Recebe +2 na primeira rodada."),
    Carta("primordial_trono", "Marika, Rainha Eterna", "Relíquia", "Força", 8, "Primordial", 4, "decreto_soberano", "Uma cópia por jogador. Reduz em 2 os bônus de todas as unidades inimigas, respeitando o limite de -2."),
    Carta("primordial_tempestade", "Placidusax, Senhor Dragão", "Relíquia", "Destreza", 8, "Primordial", 4, "olho_tempestade", "Uma cópia por jogador. Recebe +2 quando sua fileira está sob clima."),
    Carta("primordial_abismo", "Mãe Sem Forma", "Relíquia", "Destreza", 8, "Primordial", 4, "fome_abismo", "Uma cópia por jogador. Recebe +2 quando sua pontuação está abaixo da rival."),
    Carta("primordial_eternidade", "Maliketh, Guardião da Morte Destinada", "Relíquia", "Força", 8, "Primordial", 4, "paradoxo_eterno", "Uma cópia por jogador. Recebe +2 na terceira rodada se o rival venceu a segunda."),
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
    """Gera recompensa temática do universo Gwent sem expor o título do jogo externo."""
    marco = "platina" if str(marco).lower() == "platina" else "zerado"
    slug = slug_jogo(nome_jogo)
    n = _hash_int(f"{slug}:{marco}:gwent-reward-v2")
    tipo = TIPOS[n % len(TIPOS)]
    raridade = "Épica" if marco == "platina" else "Rara"
    habilidade = HABILIDADES_COMUNS[(n // 7) % len(HABILIDADES_COMUNS)] if (raridade == "Épica" or n % 2 == 0) else ""
    minimo, maximo = FAIXA_PODER[raridade]
    poder = minimo + ((n // 11) % (maximo - minimo + 1))
    nomes = {
        "Força": ("Cavaleiro de Leyndell", "Sentinela da Árvore Áurea", "Juramentado do Crisol"),
        "Destreza": ("Cavaleiro Sanguíneo", "Recusante de Volcano Manor", "Lâmina de Ravenmount"),
        "Magia": ("Feiticeiro Cariano", "Astrólogo de Liurnia", "Erudito de Raya Lucaria"),
    }
    epitetos = ("da Graça Dourada", "do Palácio de Mohgwyn", "das Ruínas de Farum Azula", "da Lua Negra", "do Monte Gelmir")
    titulo = nomes[tipo][(n // 13) % len(nomes[tipo])] + " " + epitetos[(n // 19) % len(epitetos)]
    return Carta(
        id=f"jogo_{slug}_{marco}", nome=titulo[:95], categoria="Chefe", tipo=tipo,
        poder=int(poder), raridade=raridade, custo=CUSTO_RARIDADE[raridade],
        habilidade=habilidade,
        descricao=("Recompensa de domínio: guerreiro de elite das Terras Intermédias." if marco == "platina"
                   else "Recompensa de conquista: combatente das Terras Intermédias."),
        jogo_origem="",
    )



def carta_patente(indice: int, nivel_minimo: int, nome_patente: str) -> Carta:
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
    card_id = f"patente_{indice + 1}"
    return Carta(
        id=card_id,
        nome=(
            ("Lorde de Leyndell" if nivel_minimo >= 75 else "Veterano de Leyndell" if nivel_minimo >= 30 else "Escudeiro de Leyndell" if nivel_minimo >= 10 else "Recruta de Leyndell")
            if tipo == "Força" else
            ("Lorde Sanguíneo" if nivel_minimo >= 75 else "Cavaleiro de Mohgwyn" if nivel_minimo >= 30 else "Acólito Sanguíneo" if nivel_minimo >= 10 else "Recruta de Mohgwyn")
            if tipo == "Destreza" else
            ("Mestre Cariano" if nivel_minimo >= 75 else "Feiticeiro Cariano" if nivel_minimo >= 30 else "Aprendiz Cariano" if nivel_minimo >= 10 else "Novato de Raya Lucaria")
        ) + " " + ("da Graça Perdida", "da Noite dos Punhais", "do Palácio de Mohgwyn", "da Lua Negra", "das Ruínas de Farum Azula")[(n // 29) % 5],
        categoria="Patente",
        tipo=tipo,
        poder=int(poder),
        raridade=raridade,
        custo=CUSTO_RARIDADE[raridade],
        habilidade=habilidade,
        descricao=f"Recompensa de progressão nas Terras Intermédias — nível {nivel_minimo}.",
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
