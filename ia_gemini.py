"""Adaptador do Gemini para o agente multi-provedor da Nara.

Mantém o histórico de ferramentas em MensagemAgente neutra. A conversa direta aceita imagens
inline explicitamente autorizadas pelo cog; anexos nunca entram no histórico persistido.
"""
from __future__ import annotations

import asyncio
import uuid

from ia_nucleo import (
    Adaptador, ChamadaAgente, MensagemAgente, Registro, RespostaFerramenta,
)
from gemini_resilience import run_gemini_call, mark_gemini_unavailable

_TIPOS = {"string": "STRING", "integer": "INTEGER", "boolean": "BOOLEAN"}


class GeminiAdaptador(Adaptador):
    def __init__(self, api_key: str, modelo: str, provider: str = "primary"):
        if not api_key:
            raise ValueError("Chave do projeto Gemini não foi configurada.")
        if provider not in {"primary", "backup", "tertiary"}:
            raise ValueError("provider deve ser primary ou backup.")
        self.provider = provider
        from google import genai
        from google.genai import types
        self.types = types
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
        self.modelo = modelo

    def close(self):
        close = getattr(self.client, "close", None)
        if callable(close):
            close()

    def conteudo_usuario(self, texto: str):
        return MensagemAgente(role="user", texto=str(texto))

    def conteudo_funcoes(self, respostas: list):
        return MensagemAgente(role="tool_results", respostas_ferramentas=list(respostas))

    def parte_resposta(self, nome: str, resultado: dict, call_id: str | None = None):
        return RespostaFerramenta(id_chamada=str(call_id or f"gemini_{uuid.uuid4().hex}"), nome=nome, resultado=resultado)

    def ferramentas(self, registro: Registro):
        t = self.types
        declaracoes = []
        for f in registro.ferramentas.values():
            props = {}
            for p in f.params:
                props[p.nome] = t.Schema(
                    type=getattr(t.Type, _TIPOS[p.tipo]), description=p.descricao,
                    enum=list(p.opcoes) if p.opcoes else None,
                )
            parametros = t.Schema(
                type=t.Type.OBJECT, properties=props,
                required=[p.nome for p in f.params if p.obrigatorio],
            ) if props else None
            declaracoes.append(t.FunctionDeclaration(name=f.nome, description=f.descricao, parameters=parametros))
        return [t.Tool(function_declarations=declaracoes)] if declaracoes else None

    def _google_contents(self, contents: list):
        t = self.types
        converted = []
        for item in contents:
            if not isinstance(item, MensagemAgente):
                raise TypeError(f"Histórico incompatível com Gemini: {type(item).__name__}")
            if item.role == "user":
                converted.append(t.Content(role="user", parts=[t.Part(text=item.texto)]))
            elif item.role == "assistant":
                # Preserva assinatura e estrutura do Gemini quando o histórico veio dele.
                if item.nativo is not None:
                    converted.append(item.nativo)
                    continue
                parts = []
                if item.texto:
                    parts.append(t.Part(text=item.texto))
                for call in item.chamadas:
                    parts.append(t.Part.from_function_call(name=call.nome, args=call.argumentos or {}))
                converted.append(t.Content(role="model", parts=parts))
            elif item.role == "tool_results":
                parts = [
                    t.Part.from_function_response(name=result.nome, response=result.resultado)
                    for result in item.respostas_ferramentas
                ]
                converted.append(t.Content(role="user", parts=parts))
        return converted

    def normalizar_resposta(self, response) -> MensagemAgente:
        candidates = getattr(response, "candidates", None) or []
        content = getattr(candidates[0], "content", None) if candidates else None
        parts = list(getattr(content, "parts", None) or [])
        text = "".join(
            str(part.text) for part in parts
            if getattr(part, "text", None) and not getattr(part, "thought", False)
        ).strip()
        calls = []
        for index, part in enumerate(parts):
            fc = getattr(part, "function_call", None)
            if fc:
                calls.append(ChamadaAgente(
                    id=f"gemini_{self.provider}_{uuid.uuid4().hex}_{index}",
                    nome=str(fc.name),
                    argumentos=dict(fc.args or {}),
                ))
        return MensagemAgente(role="assistant", texto=text, chamadas=calls, nativo=content)

    def _gerar_sync(self, system: str, contents: list, tools):
        t = self.types
        cfg = t.GenerateContentConfig(
            system_instruction=system,
            tools=tools,
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True) if tools else None,
        )
        response = run_gemini_call(lambda: self.client.models.generate_content(
            model=self.modelo, contents=self._google_contents(contents), config=cfg
        ), provider=self.provider)
        return self.normalizar_resposta(response)

    def _conversar_sync(self, system: str, texto: str, max_tokens: int, imagens=None) -> str:
        """Chamada única, sem ferramentas e sem histórico: custo mínimo e previsível."""
        t = self.types
        cfg = t.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=int(max_tokens),
            temperature=0.9,
        )
        parts = [t.Part(text=str(texto))]
        for imagem in (imagens or []):
            dados, mime = imagem
            parts.append(t.Part.from_bytes(data=dados, mime_type=mime))
        response = run_gemini_call(lambda: self.client.models.generate_content(
            model=self.modelo, contents=[t.Content(role="user", parts=parts)], config=cfg
        ), provider=self.provider)
        return self.normalizar_resposta(response).texto

    async def conversar(self, system: str, texto: str, max_tokens: int = 320, imagens=None) -> str:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._conversar_sync, system, texto, max_tokens, imagens), timeout=40,
            )
        except asyncio.TimeoutError as exc:
            mark_gemini_unavailable(self.provider, "timeout na conversa (40s)")
            raise TimeoutError("O Gemini demorou mais de 40 segundos para responder.") from exc

    def criar_gerador(self, system: str, registro: Registro):
        tools = self.ferramentas(registro)

        async def gerar(contents: list, usar_ferramentas: bool):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._gerar_sync, system, contents, tools if usar_ferramentas else None),
                    timeout=70,
                )
            except asyncio.TimeoutError as exc:
                mark_gemini_unavailable(self.provider, "timeout na geração com ferramentas (70s)")
                raise TimeoutError("O Gemini demorou mais de 70 segundos para responder.") from exc

        return gerar
