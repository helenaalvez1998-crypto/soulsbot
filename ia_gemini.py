"""Adaptador do Gemini (google-genai) para o agente da Nara.

Usa chamada de função MANUAL: o modelo pede a ferramenta, o código valida/executa em ia_nucleo.Registro
e devolve o resultado. A chamada automática do SDK fica desligada de propósito, porque as ferramentas
são assíncronas e passam por checagem de permissão e confirmação.
"""
from __future__ import annotations

import asyncio

from ia_nucleo import Adaptador, Registro

_TIPOS = {"string": "STRING", "integer": "INTEGER", "boolean": "BOOLEAN"}


class GeminiAdaptador(Adaptador):
    def __init__(self, api_key: str, modelo: str):
        from google import genai
        from google.genai import types
        self.types = types
        self.client = genai.Client(api_key=api_key)
        self.modelo = modelo

    # ---- montagem de conteúdos
    def conteudo_usuario(self, texto: str, imagens: list | None = None):
        partes = [self.types.Part(text=texto)]
        for dados, mime in imagens or []:
            partes.append(self.types.Part.from_bytes(data=dados, mime_type=mime))
        return self.types.Content(role="user", parts=partes)

    def conteudo_funcoes(self, respostas: list):
        return self.types.Content(role="user", parts=respostas)

    def parte_resposta(self, nome: str, resultado: dict):
        return self.types.Part.from_function_response(name=nome, response=resultado)

    # ---- declaração das ferramentas
    def ferramentas(self, registro: Registro):
        t = self.types
        declaracoes = []
        for f in registro.ferramentas.values():
            props = {}
            for p in f.params:
                props[p.nome] = t.Schema(
                    type=getattr(t.Type, _TIPOS[p.tipo]),
                    description=p.descricao,
                    enum=list(p.opcoes) if p.opcoes else None,
                )
            parametros = t.Schema(
                type=t.Type.OBJECT, properties=props,
                required=[p.nome for p in f.params if p.obrigatorio],
            ) if props else None
            declaracoes.append(t.FunctionDeclaration(name=f.nome, description=f.descricao, parameters=parametros))
        return [t.Tool(function_declarations=declaracoes)] if declaracoes else None

    # ---- chamada ao modelo (bloqueante; rode em thread)
    def _gerar_sync(self, system: str, contents: list, tools):
        t = self.types
        cfg = t.GenerateContentConfig(
            system_instruction=system,
            tools=tools,
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True) if tools else None,
        )
        return self.client.models.generate_content(model=self.modelo, contents=contents, config=cfg)

    def criar_gerador(self, system: str, registro: Registro):
        tools = self.ferramentas(registro)

        async def gerar(contents: list, usar_ferramentas: bool):
            return await asyncio.to_thread(self._gerar_sync, system, contents, tools if usar_ferramentas else None)

        return gerar
