import pytest

from orientador import config
from orientador.rag import IndiceGuias

CHAVES = ["OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
          "ORIENTADOR_PROVEDOR", "ORIENTADOR_MODELO", "ORIENTADOR_EMBEDDINGS", "ORIENTADOR_TEMPERATURA"]


@pytest.fixture
def env(monkeypatch):
    for c in CHAVES:
        monkeypatch.delenv(c, raising=False)
    return monkeypatch


def test_sem_chave(env):
    assert config.provedor_ativo() is None
    assert "Nenhuma chave" in config.verificar_chave()


def test_placeholder_nao_conta_como_chave(env):
    env.setenv("OPENAI_API_KEY", "sk-...")
    assert config.provedor_ativo() is None


@pytest.mark.parametrize("var, provedor", [
    ("OPENAI_API_KEY", "openai"),
    ("GOOGLE_API_KEY", "gemini"),
    ("GEMINI_API_KEY", "gemini"),
    ("ANTHROPIC_API_KEY", "anthropic"),
])
def test_detecta_provedor(env, var, provedor):
    env.setenv(var, "chave-teste")
    assert config.provedor_ativo() == provedor
    assert config.verificar_chave() is None


def test_provedor_forcado(env):
    env.setenv("OPENAI_API_KEY", "chave-teste")
    env.setenv("GOOGLE_API_KEY", "chave-teste")
    env.setenv("ORIENTADOR_PROVEDOR", "gemini")
    assert config.provedor_ativo() == "gemini"


def test_provedor_forcado_sem_chave(env):
    env.setenv("ORIENTADOR_PROVEDOR", "anthropic")
    assert "vazia" in config.verificar_chave()


@pytest.mark.parametrize("var, classe", [
    ("OPENAI_API_KEY", "ChatOpenAI"),
    ("GOOGLE_API_KEY", "ChatGoogleGenerativeAI"),
    ("ANTHROPIC_API_KEY", "ChatAnthropic"),
])
def test_modelo_de_cada_provedor(env, var, classe):
    env.setenv(var, "chave-teste")
    assert type(config.carregar_modelo()).__name__ == classe


def test_anthropic_usa_embeddings_de_outro_provedor_se_houver(env):
    env.setenv("ANTHROPIC_API_KEY", "chave-teste")
    assert config.carregar_embeddings() is None
    env.setenv("GOOGLE_API_KEY", "chave-teste")
    env.setenv("ORIENTADOR_PROVEDOR", "anthropic")
    assert type(config.carregar_embeddings()).__name__ == "GoogleGenerativeAIEmbeddings"


def test_rag_sem_embeddings_busca_por_palavras():
    indice = IndiceGuias(None)
    docs = indice.buscar("Ciclo Básico Común sem vestibular", k=1)
    assert docs[0].metadata["universidade"] == "UBA"
    docs = indice.buscar("ingresso", universidades=["MIT"], k=2)
    assert docs and all(d.metadata["universidade"] == "MIT" for d in docs)
