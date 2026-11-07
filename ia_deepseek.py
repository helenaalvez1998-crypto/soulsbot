"""Adaptador DeepSeek para o agente da Nara, com saída neutra e ferramentas manuais.

A entrada é texto puro. Este adaptador nunca envia imagens, arquivos ou anexos.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

import requests

from deepseek_resilience import DeepSeekHTTPError, run_deepseek_call
from ia_nucleo import (
    Adaptador, ChamadaAgente, MensagemAgente, Registro, RespostaFerramenta,
)

log = logging.getLogger("nara.ia.deepseek")


class DeepSeekAdaptador(Adaptador):
    def __init__(self, api_key: str, modelo: str | None = None):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY não foi configurada.")
        self.api_key = api_key.strip()
        self.modelo = (modelo or os.getenv("DEEPSEEK_MODEL", "deepseek-flash")).strip() or "deepseek-flash"
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
        if not self.base_url.startswith("https://"):
            raise ValueError("DEEPSEEK_BASE_URL precisa usar HTTPS.")

    def close(self):
        return None  # requests não mantém Session global neste adaptador.

    def conteudo_usuario(self, texto: str) -> MensagemAgente:
        return MensagemAgente(role="user", texto=str(texto))

    def conteudo_funcoes(self, respostas: list) -> MensagemAgente:
        return MensagemAgente(role="tool_results", respostas_ferramentas=list(respostas))

    def parte_resposta(self, nome: str, resultado: dict, call_id: str | None = None) -> RespostaFerramenta:
        return RespostaFerramenta(id_chamada=str(call_id or f"tool_{nome}"), nome=nome, resultado=resultado)

    def ferramentas(self, registro: Registro) -> list[dict] | None:
        declaracoes = []
        for ferramenta in registro.ferramentas.values():
            properties = {}
            required = []
            for param in ferramenta.params:
                schema = {
                    "type": {"string": "string", "integer": "integer", "boolean": "boolean"}[param.tipo],
                    "description": param.descricao,
                }
                if param.opcoes:
                    schema["enum"] = list(param.opcoes)
                if param.tipo == "string":
                    schema["maxLength"] = param.max_len
                if param.tipo == "integer":
                    if param.minimo is not None:
                        schema["minimum"] = param.minimo
                    if param.maximo is not None:
                        schema["maximum"] = param.maximo
                properties[param.nome] = schema
                if param.obrigatorio:
                    required.append(param.nome)
            parameters = {"type": "object", "properties": properties}
            if required:
                parameters["required"] = required
            declaracoes.append({
                "type": "function",
                "function": {
                    "name": ferramenta.nome,
                    "description": ferramenta.descricao,
                    "parameters": parameters,
                },
            })
        return declaracoes or None

    def _messages(self, system: str, contents: list[MensagemAgente]) -> list[dict]:
        messages = [{"role": "system", "content": system}]
        for item in contents:
            if isinstance(item, dict):
                # Só para facilitar compatibilidade se algum módulo legado acrescentar conteúdo texto.
                role = item.get("role")
                if role == "user" and isinstance(item.get("content"), str):
                    messages.append({"role": "user", "content": item["content"]})
                continue
            if not isinstance(item, MensagemAgente):
                raise TypeError(f"Histórico incompatível com DeepSeek: {type(item).__name__}")
            if item.role == "user":
                messages.append({"role": "user", "content": item.texto})
            elif item.role == "assistant":
                assistant = {"role": "assistant", "content": item.texto or None}
                if item.chamadas:
                    assistant["tool_calls"] = [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.nome,
                                "arguments": json.dumps(call.argumentos or {}, ensure_ascii=False),
                            },
                        }
                        for call in item.chamadas
                    ]
                messages.append(assistant)
            elif item.role == "tool_results":
                for result in item.respostas_ferramentas:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result.id_chamada,
                        "content": json.dumps(result.resultado, ensure_ascii=False, default=str),
                    })
        return messages

    def normalizar_resposta(self, resposta: dict) -> MensagemAgente:
        try:
            message = resposta["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("A API DeepSeek retornou uma resposta fora do formato esperado.") from exc
        texto = message.get("content") or ""
        chamadas = []
        for index, tool_call in enumerate(message.get("tool_calls") or []):
            function = tool_call.get("function") or {}
            raw_args = function.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                if not isinstance(args, dict):
                    args = {}
            except (json.JSONDecodeError, TypeError, ValueError):
                log.warning("DeepSeek devolveu argumentos de ferramenta inválidos; chamada descartada.")
                continue
            chamadas.append(ChamadaAgente(
                id=str(tool_call.get("id") or f"deepseek_tool_{index}"),
                nome=str(function.get("name") or ""),
                argumentos=args,
            ))
        return MensagemAgente(role="assistant", texto=str(texto), chamadas=chamadas)

    def _gerar_sync(self, system: str, contents: list, tools: list[dict] | None):
        payload = {
            "model": self.modelo,
            "messages": self._messages(system, contents),
            "temperature": 0.2,
            "max_tokens": 4096,
            # Ferramentas em modo thinking possuem restrições de tool_choice; desabilitamos
            # thinking neste adaptador para priorizar chamadas estruturadas e economia.
            "thinking": {"type": "disabled"},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        url = self.base_url + "/chat/completions"

        def request():
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=(10, 65),
            )
            if not response.ok:
                raise DeepSeekHTTPError(response.status_code, response.text)
            try:
                return response.json()
            except ValueError as exc:
                raise RuntimeError("DeepSeek retornou JSON inválido.") from exc

        raw = run_deepseek_call(request)
        return self.normalizar_resposta(raw)

    def criar_gerador(self, system: str, registro: Registro):
        tools = self.ferramentas(registro)

        async def gerar(contents: list, usar_ferramentas: bool):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._gerar_sync, system, contents, tools if usar_ferramentas else None),
                    timeout=75,
                )
            except asyncio.TimeoutError as exc:
                # Timeout de API aciona o circuito como indisponibilidade.
                raise TimeoutError("DeepSeek demorou mais de 75 segundos para responder.") from exc

        return gerar


def deepseek_chat_text_sync(prompt: str, *, system: str = "Você é um assistente preciso.", temperature: float = 0.1) -> str:
    """Geração textual simples reutilizável por tradução/serviços sem tool calling."""
    adapter = DeepSeekAdaptador(os.getenv("DEEPSEEK_API_KEY", ""))
    payload = {
        "model": adapter.modelo,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 2048,
        "thinking": {"type": "disabled"},
    }
    def request():
        response = requests.post(
            adapter.base_url + "/chat/completions",
            headers={"Authorization": f"Bearer {adapter.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=(10, 45),
        )
        if not response.ok:
            raise DeepSeekHTTPError(response.status_code, response.text)
        return response.json()
    raw = run_deepseek_call(request)
    try:
        return str(raw["choices"][0]["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Resposta textual do DeepSeek veio em formato inválido.") from exc
