import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from orientador.dados import carregar_base
from orientador.modelo_falso import ModeloFalso
from orientador.rag import IndiceGuias
from orientador.schemas import Classificacao, PerfilAcademico


@pytest.fixture(scope="session")
def base():
    return carregar_base()


@pytest.fixture(scope="session")
def indice():
    return IndiceGuias(DeterministicFakeEmbedding(size=64))


def perfil_fake(texto: str) -> PerfilAcademico:
    return PerfilAcademico(
        nome="fake", ano_conclusao=2027, pontos_fortes=["a"], pontos_de_atencao=["b"],
        areas_recomendadas=["c"], resumo="perfil gerado pelo modelo falso",
    )


@pytest.fixture
def modelo_com(request):

    def _criar(classificacoes: dict[str, Classificacao], respostas=("ok",)):
        def classificar(texto: str) -> Classificacao:
            texto = texto.rsplit("Human: ", 1)[-1]
            for trecho, cls in classificacoes.items():
                if trecho in texto:
                    return cls
            return Classificacao(intencao="outro")

        return ModeloFalso.criar(
            roteiro={"Classificacao": classificar, "PerfilAcademico": perfil_fake},
            respostas=respostas,
        )

    return _criar
