"""Funções para transformar textos em vetores (embeddings) com o modelo E5.

Usado por scripts/indexar.py (codifica os chunks com "passage: ") e por scripts/buscar.py
(codifica a consulta com "query: ").
"""
# torch: biblioteca que roda o modelo; F tem a função de normalização dos vetores.
import torch
import torch.nn.functional as F
from torch import Tensor
# transformers: baixa e carrega o tokenizer e o modelo do Hugging Face.
from transformers import AutoTokenizer, AutoModel

# Modelo usado em todo o projeto (384 dimensões por vetor).
MODEL_NAME = "intfloat/multilingual-e5-small"


def load_model(model_name: str = MODEL_NAME):
    """Carrega o tokenizer e o modelo do Hugging Face Hub (fica em cache depois da primeira vez)."""
    # O tokenizer quebra o texto em tokens (pedaços de palavra) e converte cada um num número.
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # O modelo recebe esses números e devolve um vetor para cada token.
    model = AutoModel.from_pretrained(model_name)
    # Modo de avaliação: desliga o que só serve no treino (dropout), para o resultado ser sempre igual.
    model.eval()
    return tokenizer, model


def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    """Média dos vetores dos tokens de cada sequência, ignorando o padding."""
    # O modelo devolve um vetor por token. Para ter UM vetor por texto, tiramos a média deles.
    # attention_mask vale 1 nos tokens reais e 0 no padding (tokens vazios que completam os textos
    # curtos de um lote). Primeiro zeramos os vetores do padding...
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    # ...depois somamos e dividimos pelo número de tokens reais (não pelo tamanho do lote).
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def encode(texts: list[str], tokenizer, model, prefix: str,
           batch_size: int = 32, max_length: int = 512) -> Tensor:
    """
    Gera embeddings normalizados (L2) para uma lista de textos.

    prefix -- "query: " para consultas ou "passage: " para documentos, como o E5 exige
    """
    all_embeddings = []

    # Processa os textos em lotes (batch_size por vez) para não estourar a memória.
    for start in range(0, len(texts), batch_size):
        # 1. Põe o prefixo na frente de cada texto do lote ("passage: ..." ou "query: ...").
        batch_texts = [prefix + text for text in texts[start:start + batch_size]]
        # 2. Tokeniza: padding=True completa os textos curtos até o tamanho do maior do lote;
        #    truncation=True corta o que passar de max_length (512) tokens.
        batch = tokenizer(batch_texts, max_length=max_length, padding=True,
                          truncation=True, return_tensors="pt")

        # 3. Roda o modelo. no_grad: não guarda o que seria preciso para treinar (mais rápido).
        with torch.no_grad():
            outputs = model(**batch)

        # 4. Um vetor por texto: média dos vetores dos tokens (sem o padding).
        embeddings = average_pool(outputs.last_hidden_state, batch["attention_mask"])
        # 5. Normaliza cada vetor para ter tamanho 1. Assim, comparar dois vetores é só um
        #    produto escalar, que passa a ser igual à similaridade de cosseno.
        all_embeddings.append(F.normalize(embeddings, p=2, dim=1))

    # Junta os lotes numa matriz só: (número de textos) x 384.
    return torch.cat(all_embeddings, dim=0)
