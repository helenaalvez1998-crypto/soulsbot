"""Assistente interativo para configurar o NARA sem expor credenciais na tela.

Uso: python configurar_bot.py
Cria/atualiza .env preservando configurações existentes. Não conecta ao Discord nem
valida a chave junto ao Google; apenas prepara a configuração local.
"""
from __future__ import annotations

import getpass
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
TEMPLATE_CANDIDATES = (ROOT / ".env.example", ROOT / "env.example")


def carregar_template() -> str:
    for caminho in TEMPLATE_CANDIDATES:
        if caminho.is_file():
            return caminho.read_text(encoding="utf-8")
    raise FileNotFoundError("Não encontrei env.example para criar a configuração inicial.")


def atualizar_env_texto(conteudo: str, atualizacoes: dict[str, str]) -> str:
    """Atualiza chaves sem apagar comentários, ordem ou outras configurações."""
    linhas = conteudo.splitlines()
    encontradas: set[str] = set()
    saida: list[str] = []
    for linha in linhas:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", linha)
        if match and match.group(1) in atualizacoes:
            chave = match.group(1)
            if chave not in encontradas:
                saida.append(f"{chave}={atualizacoes[chave]}")
                encontradas.add(chave)
            # Remove duplicatas da mesma variável para não deixar valor ambíguo.
            continue
        saida.append(linha)
    for chave, valor in atualizacoes.items():
        if chave not in encontradas:
            saida.append(f"{chave}={valor}")
    return "\n".join(saida).rstrip() + "\n"


def ler_valor_existente(texto: str, chave: str) -> str:
    for linha in texto.splitlines():
        match = re.match(rf"^\s*{re.escape(chave)}\s*=\s*(.*?)\s*$", linha)
        if match:
            valor = match.group(1)
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in {'"', "'"}:
                valor = valor[1:-1]
            return valor
    return ""


def pedir_segredo(rotulo: str, existente: str, *, obrigatorio: bool) -> str:
    dica = " (Enter mantém o valor atual)" if existente else ""
    while True:
        valor = getpass.getpass(f"{rotulo}{dica}: ").strip()
        if not valor and existente:
            return existente
        if valor:
            return valor
        if not obrigatorio:
            return ""
        print("Este campo é obrigatório para o recurso solicitado.")


def main() -> int:
    if sys.version_info < (3, 11):
        print("ERRO: o NARA requer Python 3.11 ou superior.")
        return 2

    if ENV_PATH.exists():
        original = ENV_PATH.read_text(encoding="utf-8")
        print("Arquivo .env encontrado. Valores existentes serão preservados ao pressionar Enter.")
    else:
        original = carregar_template()
        print("Criando .env a partir do env.example.")

    atualizacoes: dict[str, str] = {}
    token_atual = ler_valor_existente(original, "DISCORD_TOKEN")
    gemini_atual = ler_valor_existente(original, "GEMINI_API_KEY")
    backup_atual = ler_valor_existente(original, "GEMINI_BACKUP_API_KEY")
    third_atual = ler_valor_existente(original, "GEMINI_THIRD_API_KEY")
    tavily_atual = ler_valor_existente(original, "TAVILY_API_KEY")

    print("\n=== Credenciais necessárias ===")
    print("O token do Discord e as chaves Gemini serão ocultados durante a digitação.")
    atualizacoes["DISCORD_TOKEN"] = pedir_segredo("Token do bot Discord", token_atual, obrigatorio=True)
    atualizacoes["GEMINI_API_KEY"] = pedir_segredo("Chave Gemini principal", gemini_atual, obrigatorio=False)
    atualizacoes["GEMINI_BACKUP_API_KEY"] = pedir_segredo("Chave Gemini reserva (opcional)", backup_atual, obrigatorio=False)
    atualizacoes["GEMINI_THIRD_API_KEY"] = pedir_segredo("Terceira chave Gemini (opcional)", third_atual, obrigatorio=False)
    atualizacoes["TAVILY_API_KEY"] = pedir_segredo("Chave Tavily para pesquisa web (opcional)", tavily_atual, obrigatorio=False)

    guild_atual = ler_valor_existente(original, "GUILD_ID")
    guild_id = input(f"ID do servidor Discord [{guild_atual or '0'}]: ").strip() or guild_atual or "0"
    if not guild_id.isdigit():
        print("ERRO: GUILD_ID deve conter apenas números.")
        return 2
    atualizacoes["GUILD_ID"] = guild_id

    # Mantém conversa livre ativa e mantém pesquisa com ferramentas/moderação sob opt-in.
    atualizacoes.update({
        "NARA_CONVERSA_ENABLED": "true",
        "NARA_CHAT_IA_ENABLED": "true" if atualizacoes["TAVILY_API_KEY"] else "false",
        "IA_ACOES_MODERACAO": "false",
        "GEMINI_MODEL": ler_valor_existente(original, "GEMINI_MODEL") or "gemini-3.5-flash-lite",
    })

    novo = atualizar_env_texto(original, atualizacoes)
    ENV_PATH.write_text(novo, encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass

    tem_gemini = bool(atualizacoes["GEMINI_API_KEY"] or atualizacoes["GEMINI_BACKUP_API_KEY"] or atualizacoes["GEMINI_THIRD_API_KEY"])
    print("\n=== Configuração gravada em .env ===")
    print("DISCORD_TOKEN: configurado")
    print(f"Gemini: {'ao menos uma chave cadastrada' if tem_gemini else 'SEM CHAVE — conversa generativa não funcionará'}")
    print("NARA_CONVERSA_ENABLED=true")
    print("NARA_CHAT_IA_ENABLED=" + ("true" if atualizacoes["TAVILY_API_KEY"] else "false"))
    print("Pesquisa web: habilitada" if atualizacoes["TAVILY_API_KEY"] else "Pesquisa web: desativada (adicione TAVILY_API_KEY para habilitar)")
    print("IA_ACOES_MODERACAO=false")
    print("\nPróximo passo: instale requirements.txt e execute python bot.py.")
    if not tem_gemini:
        print("Obtenha uma chave no Google AI Studio e execute este configurador novamente.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
