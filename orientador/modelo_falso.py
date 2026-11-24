"""Chat model falso para testes: texto em ciclo e saída estruturada roteirizada."""

from __future__ import annotations

from itertools import cycle
from typing import Any, Callable

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import Field


class ModeloFalso(GenericFakeChatModel):
    roteiro: dict[str, Callable[[str], Any]] = Field(default_factory=dict)
    chamadas: list[str] = Field(default_factory=list)

    @classmethod
    def criar(cls, roteiro=None, respostas=("resposta do modelo falso",)) -> "ModeloFalso":
        return cls(messages=cycle([AIMessage(r) for r in respostas]), roteiro=roteiro or {})

    def with_structured_output(self, schema, **kwargs):
        nome = schema.__name__

        def _executar(prompt_value):
            self.chamadas.append(nome)
            texto = prompt_value.to_string() if hasattr(prompt_value, "to_string") else str(prompt_value)
            if nome not in self.roteiro:
                raise KeyError(f"ModeloFalso sem roteiro para {nome}")
            return self.roteiro[nome](texto)

        return RunnableLambda(_executar)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.chamadas.append("texto")
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
