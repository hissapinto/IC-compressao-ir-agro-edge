"""Gera chunks (um por par pergunta-resposta) a partir dos txt da coleção 500 Perguntas 500 Respostas.

Uso (a partir de codigo/):
    python src/chunking.py                 # gera e divide os chunks longos (precisa do .venv)
    python src/chunking.py --sem-divisao   # só gera, sem tokenizer (biblioteca padrão)

Lê codigo/data/raw/txt/*.txt e codigo/data/raw/indice.csv; escreve chunks_sem_divisao.jsonl e
relatorio.csv em codigo/data/processed/auxiliares/. O chunks.jsonl final não é sobrescrito por este
script: ele sai de scripts/dividir_chunks.py e scripts/filtrar_chunks.py.

Divisão: um chunk cujo texto, com o prefixo "passage: ", passa de --limite tokens do tokenizer do
modelo de embedding vira várias partes. Toda parte repete o cabeçalho (cultura | capítulo e a
pergunta) e leva um trecho da resposta, cortado em fim de parágrafo, de frase ou, em último caso,
de palavra. As partes ganham id "<id>_p1", "<id>_p2"... e os campos id_original, parte e
total_partes (presentes em todos os chunks; 1/1 quando não houve divisão).
"""
import argparse
import csv
import json
import re
from pathlib import Path

# ---------------------------------------------------------------- caminhos
# Tudo é relativo à pasta codigo/, então o script funciona de qualquer lugar.
CODIGO = Path(__file__).resolve().parent.parent
RAW = CODIGO / "data" / "raw"                          # dados brutos (txt e indice.csv)
TXT = RAW / "txt"                                      # entrada: um txt por livro
SAIDA = CODIGO / "data" / "processed" / "auxiliares"   # saída: chunks intermediários e relatório

# ---------------------------------------------------------------- padrões de texto (expressões regulares)
# FIM: títulos que marcam o fim das perguntas (referências, notas, índice...). O que vem depois
# não entra na resposta.
FIM = re.compile(r"^(Mais alguma pergunta|Conheça outros títulos|Literatura (recomendada|consultada|citada)|(Notas|Referências?( bibliográficas)?|Índice( remissivo)?|Glossário)$)")
# CAP_A: linha de capítulo nos livros de ePub, como "• Capítulo 5 •" (guarda o número).
CAP_A = re.compile(r"^(?:•\s*)?Capítulo\s+(\d+)\s*•?$")
# Q_A: pergunta nos livros de ePub, como "15) Qual a época...?" (guarda o número e o texto).
Q_A = re.compile(r"^(?:[a-z] )?(\d{1,3})\s*\)\s*(.*)$")  # aceita uma letra solta antes (ex.: "s 15)")
# NUM: linha só com um número de 1 a 3 dígitos (número de pergunta ou de página nos PDFs).
NUM = re.compile(r"^\d{1,3}$")
# PERGUNTA_SEM_INTERROGACAO: começo típico de pergunta, para aceitar as que o livro digitou sem "?".
PERGUNTA_SEM_INTERROGACAO = re.compile(r"^(Qual|Quais|Como|O que|Que |Por que|Quando|Onde|Quanto|Quantos|Quantas) ")


def carregar_indice():
    """Metadados por nome de arquivo txt (cultura_ano), vindos do indice.csv."""
    meta = {}
    with open(RAW / "indice.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # A chave é o nome do arquivo sem pasta nem extensão (ex.: "500P_soja_2019"),
            # que é igual ao nome do txt; o valor é a linha inteira (título, edição, URL...).
            meta[Path(r["arquivo"]).stem] = r
    return meta


def juntar_linhas(linhas):
    """Junta linhas quebradas do PDF em parágrafos."""
    # No PDF, cada linha da página vira uma linha do txt, então uma frase pode estar quebrada
    # em várias linhas. Aqui decidimos, linha a linha, como ela se liga à anterior.
    out = ""
    for l in linhas:
        l = l.strip()
        if not l:
            continue                       # linha vazia: ignora
        if not out:
            out = l                        # primeira linha: só começa o texto
        elif out.endswith("-") and l[:1].islower():
            out = out + l                  # palavra hifenizada no fim da linha: junta sem espaço
        elif l.startswith("•") or (out[-1] in ".:;!?" and l[:1].isupper()):
            out = out + "\n" + l           # item de lista ou frase nova: começa um parágrafo
        else:
            out = out + " " + l            # continuação da mesma frase: junta com espaço
    return out


def parse_formato_a(linhas):
    """Livros vindos de epub: '• Capítulo N •' e perguntas 'N) texto'.

    No início de cada capítulo há uma lista só com as perguntas; ela termina em '•••'
    e depois as perguntas aparecem de novo, cada uma seguida da resposta.
    """
    # O livro é lido linha a linha, como uma "máquina de estados": o estado diz em que parte do
    # capítulo estamos e, portanto, o que fazer com a linha.
    #   fora      antes do primeiro capítulo (sumário, apresentação): tudo é ignorado
    #   cabecalho logo depois de "Capítulo N": título e autores do capítulo
    #   lista     a lista inicial só com as perguntas do capítulo (ignorada)
    #   corpo     as perguntas de novo, agora cada uma seguida da resposta
    pares, cap = [], None
    estado = "fora"  # fora | cabecalho | lista | corpo
    atual = None          # par pergunta-resposta sendo montado
    esperado = 1          # próximo número de pergunta esperado (quando não há lista)
    feitos, vistos = set(), {}   # perguntas já extraídas / perguntas da lista do capítulo atual

    def fechar():
        """Termina o par atual: junta as linhas da resposta e guarda o par na lista."""
        nonlocal atual
        if atual:
            atual["resposta"] = "\n".join(p for p in atual.pop("_linhas") if p.strip()).strip()
            pares.append(atual)
            atual = None

    for l in linhas:
        s = l.strip()
        # Linha de capítulo: fecha o par anterior e começa um capítulo novo.
        m = CAP_A.match(s)
        if m:
            fechar()
            cap = {"num": int(m.group(1)), "titulo": None, "autores": []}
            estado = "cabecalho"
            vistos = {}
            continue
        # Antes do primeiro capítulo, ou linha vazia: ignora.
        if cap is None or not s:
            continue
        # Cabeçalho: a primeira linha é o título e as seguintes são os autores, até
        # aparecer a primeira pergunta (que abre a lista).
        if estado == "cabecalho":
            if Q_A.match(s):
                estado = "lista"
                vistos = {int(Q_A.match(s).group(1)): True}
                continue
            elif cap["titulo"] is None:
                cap["titulo"] = s
            else:
                cap["autores"].append(s)
            continue
        # Lista: só anota os números das perguntas do capítulo, para reconhecê-las no corpo.
        if estado == "lista":
            # a lista termina em '•••' ou quando uma pergunta da lista se repete
            m = Q_A.match(s)
            if s == "•••":
                estado = "corpo"
                continue
            if not (m and int(m.group(1)) in vistos):
                if m:
                    vistos[int(m.group(1))] = True
                continue
            estado = "corpo"
        # corpo
        if FIM.match(s):
            # referências/notas no fim de um capítulo ou do livro não entram na resposta
            fechar()
            if len(feitos) >= 500:
                break
            continue
        if s == "•••":
            # às vezes o separador vem entre a pergunta e a resposta: só fecha se já houver resposta
            if atual and atual["_linhas"]:
                fechar()
            continue
        # em alguns epubs os capítulos vêm fora de ordem, então vale qualquer número
        # da lista do capítulo que ainda não apareceu (evita confundir com itens "1)" das respostas)
        m = Q_A.match(s)
        num = int(m.group(1)) if m else None
        valido = m and num not in feitos and (num in vistos if vistos else num == esperado)
        if valido:
            # Pergunta nova: fecha a anterior e começa um par com o texto da pergunta.
            fechar()
            atual = {"numero": num, "pergunta": m.group(2).strip(), "capitulo": dict(cap), "_linhas": []}
            feitos.add(num)
            esperado = num + 1
        elif atual:
            # Qualquer outra linha é parte da resposta da pergunta atual.
            atual["_linhas"].append(s)
    fechar()
    # Ordena pelo número da pergunta (os capítulos podem ter vindo fora de ordem).
    return sorted(pares, key=lambda p: p["numero"])


def parse_formato_b(linhas):
    """Livros vindos de PDF: número da pergunta sozinho na linha, com números de página,
    rodapés e quebras de página (\\f) no meio do texto."""
    # L: as linhas sem o caractere de quebra de página (\f).
    # ff: True nas linhas que começam uma página nova (onde havia \f); os capítulos começam
    #     sempre numa página nova, então isso ajuda a reconhecê-los.
    L = [l.replace("\f", "").rstrip() for l in linhas]
    ff = ["\f" in l for l in linhas]
    n = len(L)

    def proximas(i, k):
        """Índices das próximas k linhas não vazias depois de i."""
        out, j = [], i + 1
        while j < n and len(out) < k:
            if L[j].strip():
                out.append(j)
            j += 1
        return out

    def anteriores(i, k):
        """Índices das k linhas não vazias antes de i, da mais próxima para a mais distante."""
        out, j = [], i - 1
        while j >= 0 and len(out) < k:
            if L[j].strip():
                out.append(j)
            j -= 1
        return out

    def eh_pergunta(i, num):
        """Devolve os índices das linhas da pergunta, ou None.

        Em geral o texto da pergunta vem depois do número; em algumas páginas o PDF
        extraiu o texto antes do número."""
        # A linha precisa ser exatamente o número esperado.
        if L[i].strip() != str(num):
            return None
        idx = proximas(i, 8)    # até 8 linhas depois do número
        ant = anteriores(i, 6)  # até 6 linhas antes do número
        antes_eh_pergunta = bool(ant) and L[ant[0]].strip().endswith("?")
        # Caso comum: a pergunta vem depois do número e termina na primeira linha com "?".
        for k, j in enumerate(idx):
            t = L[j].strip()
            if NUM.match(t):
                break
            if t.endswith(("?", "?)")):
                # se há uma frase terminada antes do '?', o que vem depois do número é a resposta
                # e o '?' é da pergunta seguinte; a pergunta certa é a que veio antes do número
                if antes_eh_pergunta and any(L[x].strip().endswith(".") for x in idx[:k]):
                    break
                return idx[: k + 1]
        # pergunta digitada sem '?' no livro: aceita se começar como pergunta e terminar em '.'
        if idx and PERGUNTA_SEM_INTERROGACAO.match(L[idx[0]].strip()):
            for k, j in enumerate(idx[:4]):
                if L[j].strip().endswith("."):
                    return idx[: k + 1]
        # Último caso: a pergunta veio ANTES do número. Volta linha a linha até o começo dela.
        if not antes_eh_pergunta:
            return None
        q = [ant[0]]
        for j in ant[1:]:
            t = L[j].strip()
            if NUM.match(t) or t[-1] in ".:;!?)" or t.startswith("•"):
                break
            q.append(j)
        return sorted(q)

    def eh_capitulo(i, num):
        """Devolve o índice da linha do título se a linha i abre o capítulo num, ou None.

        Um capítulo é o número sozinho no começo de uma página, seguido de um título que não
        parece pergunta, sumário ("..."), referência ("Disponível em") nem outro número."""
        if not ff[i] or L[i].strip() != str(num):
            return None
        idx = proximas(i, 1)
        if not idx:
            return None
        t = L[idx[0]].strip()
        if t.endswith("?") or ".." in t or t.startswith("Disponível") or NUM.match(t):
            return None
        return idx[0]

    pares, cap, atual = [], None, None
    esperado_q, esperado_c = 1, 1   # próximo número de pergunta e de capítulo esperados
    i = 0                           # linha atual

    def fechar():
        """Termina o par atual: junta as linhas da resposta em parágrafos e guarda o par."""
        nonlocal atual
        if atual:
            atual["resposta"] = juntar_linhas([t for _, t in atual.pop("_linhas")])
            pares.append(atual)
            atual = None

    def separar_pulada(num):
        """Quando o número de uma pergunta se perdeu (ex.: caiu dentro de uma tabela),
        o texto dela costuma ter ficado na resposta anterior: separa a partir da
        última linha terminada em '?'. A pergunta começa na primeira linha que não é
        continuação da anterior (a anterior termina em letra minúscula, vírgula ou hífen)."""
        nonlocal atual
        linhas_r = atual["_linhas"]
        # linhas curtas costumam ser células de tabela, não parte da pergunta
        continua = lambda t: len(t) >= 30 and (t[-1].islower() or t[-1] in ",-")
        for k in range(len(linhas_r) - 1, 0, -1):
            if not linhas_r[k][1].endswith("?"):
                continue
            ini = k
            while ini > 0 and k - ini < 5 and continua(linhas_r[ini - 1][1]):
                ini -= 1
            # perguntas com duas frases: "Qual ...? Como ...?"
            while ini > 1 and linhas_r[ini - 1][1].endswith("?") and k - ini < 5:
                ini -= 1
                while ini > 0 and k - ini < 5 and continua(linhas_r[ini - 1][1]):
                    ini -= 1
            if ini == 0 or not linhas_r[ini][1][:1].isupper():
                return
            pergunta = juntar_linhas([t for _, t in linhas_r[ini:k + 1]]).replace("\n", " ")
            resto = linhas_r[k + 1:]
            atual["_linhas"] = linhas_r[:ini]
            cap_atual = atual["capitulo"]
            fechar()
            atual = {"numero": num, "pergunta": pergunta, "capitulo": cap_atual, "_linhas": resto}
            return

    # Percorre o livro linha a linha. Em cada linha, testa nesta ordem: começo de capítulo,
    # fim das perguntas, pergunta nova; senão, a linha é parte da resposta atual.
    while i < n:
        s = L[i].strip()
        # 1. Começo de capítulo?
        j = eh_capitulo(i, esperado_c)
        if j is not None:
            fechar()
            # título: linhas até a primeira em branco; depois autores até a próxima em branco
            titulo, k = [], j
            while k < n and L[k].strip():
                titulo.append(L[k].strip())
                k += 1
            autores = []
            while k < n and not L[k].strip():
                k += 1
            while k < n and L[k].strip() and not NUM.match(L[k].strip()):
                autores.append(L[k].strip())
                k += 1
            cap = {"num": esperado_c, "titulo": " ".join(titulo), "autores": autores}
            esperado_c += 1
            i = k
            continue
        # Antes do primeiro capítulo (sumário, apresentação), nada é extraído.
        if cap is not None:
            # 2. Fim das perguntas (referências, notas...)? Fecha o par; depois da 500, para.
            if FIM.match(s):
                fechar()
                if esperado_q > 500:
                    break
            # 3. Pergunta nova?
            # se um número não for encontrado, tenta o seguinte para não travar o livro inteiro
            for num in (esperado_q, esperado_q + 1, esperado_q + 2):
                q = eh_pergunta(i, num)
                if q:
                    break
            if q:
                # Pulou um número: tenta recuperar a pergunta perdida de dentro da resposta anterior.
                if atual and num == esperado_q + 1:
                    separar_pulada(esperado_q)
                # Pergunta que veio antes do número: tira essas linhas da resposta anterior.
                if atual and q[0] < i:
                    atual["_linhas"] = [(x, t) for x, t in atual["_linhas"] if x < q[0]]
                fechar()
                atual = {
                    "numero": num,
                    "pergunta": juntar_linhas([L[x] for x in q]).replace("\n", " "),
                    "capitulo": dict(cap),
                    "_linhas": [],
                }
                esperado_q = num + 1
                i = max(q[-1], i) + 1   # continua depois da última linha da pergunta
                continue
            # 4. Senão, a linha é parte da resposta (números soltos, como os de página, ficam de fora).
            #    Guarda o índice junto, para poder cortar a resposta depois, se preciso.
            if atual and s and not NUM.match(s):
                atual["_linhas"].append((i, s))
        i += 1
    fechar()
    return pares


def extrair_introducao(linhas, formato, max_chars=1500):
    """Texto da Introdução (entre o título 'Introdução' e o capítulo 1), dividido em
    partes de até max_chars respeitando parágrafos. Lista vazia se o livro não tiver."""
    L = [l.replace("\f", "").strip() for l in linhas]
    # 1. Acha onde a introdução termina: na primeira linha de capítulo (ePub) ou, no PDF, no
    #    "1" sozinho no começo de uma página que não é seguido de pergunta nem de sumário.
    if formato == "A":
        fim = next((i for i, l in enumerate(L) if CAP_A.match(l)), None)
    else:
        fim = next((i for i, l in enumerate(linhas)
                    if "\f" in l and L[i] == "1" and i + 2 < len(L)
                    and not any(x.endswith("?") or ".." in x for x in L[i + 1:i + 4] if x)), None)
    if fim is None:
        return []
    # 2. Acha onde ela começa: a última linha "Introdução" antes do capítulo 1 (a primeira
    #    costuma ser a do sumário).
    inicio = max((i for i, l in enumerate(L[:fim]) if l == "Introdução"), default=None)
    if inicio is None:
        return []
    # 3. Junta as linhas em parágrafos (sem números de página).
    texto = juntar_linhas([l for l in L[inicio + 1:fim] if l and not NUM.match(l)])
    # 4. Agrupa parágrafos inteiros em partes de até max_chars caracteres.
    partes, atual = [], ""
    for par in texto.split("\n"):
        if atual and len(atual) + len(par) > max_chars:
            partes.append(atual)
            atual = par
        else:
            atual = f"{atual}\n{par}" if atual else par
    if atual:
        partes.append(atual)
    return partes


# ---------------------------------------------------------------- divisão por tokens

# O E5 aceita no máximo 512 tokens. Os chunks maiores são divididos em partes que cabem no limite.
# A contagem inclui o prefixo "passage: ", que é posto na hora de codificar (ver src/embeddings.py).
PREFIXO = "passage: "
# Espaço depois de . ! ? ; ou : (onde dá para cortar uma frase).
FIM_DE_FRASE = re.compile(r"(?<=[.!?;:])\s+")


def cabecalho(c: dict) -> str:
    """Parte do texto que se repete em todas as partes de um chunk dividido."""
    if c["tipo"] == "introducao":
        return f"{c['cultura']} | {c['capitulo']}\n"
    return f"{c['cultura']} | {c['capitulo']}\nPergunta: {c['pergunta']}\nResposta: "


def unidades(resposta: str) -> list[tuple[str, str]]:
    """Quebra a resposta em (trecho, separador que vinha antes dele): parágrafos e, dentro deles, frases."""
    # O separador guarda como o trecho se ligava ao anterior, para remontar o texto igual:
    # "\n" na primeira frase de um parágrafo novo, " " entre frases e "" no começo da resposta.
    saida = []
    for i, par in enumerate(resposta.split("\n")):
        for j, frase in enumerate(FIM_DE_FRASE.split(par)):
            if frase:
                saida.append((frase, "\n" if i and not j else " " if j else ""))
    return saida


def trechos_da_resposta(c: dict, n_tokens, limite: int) -> list[str]:
    """Divide a resposta em trechos que, junto com prefixo e cabeçalho, cabem no limite."""
    cab = cabecalho(c)
    # cabe(trecho): True se prefixo + cabeçalho + trecho ficam dentro do limite de tokens.
    cabe = lambda trecho: n_tokens(PREFIXO + cab + trecho) <= limite  # noqa: E731

    # 1. Quebra a resposta em pedaços que cabem sozinhos: frases e, se uma frase for grande
    #    demais, grupos de palavras.
    pedacos = []
    for trecho, sep in unidades(c["resposta"]):
        if cabe(trecho):
            pedacos.append((trecho, sep))
            continue
        # frase sozinha maior que o limite: corta por palavras
        atual = ""
        for palavra in trecho.split(" "):
            teste = f"{atual} {palavra}" if atual else palavra
            if atual and not cabe(teste):
                pedacos.append((atual, sep))
                sep, atual = " ", palavra
            else:
                atual = teste
        if atual:
            pedacos.append((atual, sep))

    # 2. Junta os pedaços em ordem, enchendo cada parte o máximo possível: quando o próximo
    #    pedaço não cabe mais, fecha a parte e começa outra.
    partes, atual = [], ""
    for trecho, sep in pedacos:
        teste = atual + sep + trecho if atual else trecho
        if atual and not cabe(teste):
            partes.append(atual)
            atual = trecho
        else:
            atual = teste
    if atual:
        partes.append(atual)
    return partes


def dividir_chunks(chunks: list[dict], n_tokens, limite: int = 512) -> list[dict]:
    """Aplica a divisão a uma lista de chunks. n_tokens(texto) conta tokens com os especiais."""
    saida = []
    for c in chunks:
        # Todo chunk ganha id_original (o id antes da divisão), que liga as partes à pergunta.
        c = {**c, "id_original": c.get("id_original", c["id"])}
        # Cabe no limite: passa inteiro, como parte 1 de 1.
        if n_tokens(PREFIXO + c["texto"]) <= limite:
            saida.append({**c, "parte": 1, "total_partes": 1})
            continue
        # Não cabe: vira várias partes. Cada parte copia os metadados, ganha id "<id>_pN" e
        # leva só um trecho da resposta, com o cabeçalho (cultura, capítulo, pergunta) repetido.
        partes = trechos_da_resposta(c, n_tokens, limite)
        for i, trecho in enumerate(partes, 1):
            saida.append({**c, "id": f"{c['id']}_p{i}", "parte": i, "total_partes": len(partes),
                          "resposta": trecho, "texto": cabecalho(c) + trecho})
    return saida


def filtrar_chunks(chunks: list[dict], manter_introducao: bool = False, ids_excluidos=()) -> list[dict]:
    """Seleciona o corpus usado na indexação, sem apagar nada dos arquivos de origem.

    Por padrão (decisão do orientador) ficam só os pares pergunta-resposta vindos de texto:
    saem as introduções (tipo = introducao) e os pares de ids_excluidos (respostas que dependem de
    imagem). A decisão é sempre tomada pelo id_original, então as partes de um chunk dividido saem ou
    ficam juntas.
    """
    # 1. Monta o conjunto de id_original que ficam de fora: a lista recebida + as introduções.
    fora = set(ids_excluidos)
    for c in chunks:
        if not manter_introducao and c.get("tipo") == "introducao":
            fora.add(c.get("id_original", c["id"]))
    # 2. Mantém só os chunks cujo id_original não está nesse conjunto (a ordem não muda).
    return [c for c in chunks if c.get("id_original", c["id"]) not in fora]


def contador_de_tokens(modelo: str):
    """n_tokens(texto) com o tokenizer do modelo de embedding (importa transformers só aqui)."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(modelo)
    # Devolve uma função: recebe um texto e diz quantos tokens ele tem (com os especiais do modelo).
    return lambda t: len(tok(t, add_special_tokens=True)["input_ids"])


def main():
    # 1. Opções da linha de comando.
    parser = argparse.ArgumentParser(description="Gera os chunks a partir dos txt.")
    parser.add_argument("--modelo", default="intfloat/multilingual-e5-small", help="tokenizer usado na contagem")
    parser.add_argument("--limite", type=int, default=512, help="máximo de tokens por chunk")
    parser.add_argument("--sem-divisao", action="store_true", help="não divide os chunks longos")
    args = parser.parse_args()

    # 2. Metadados dos livros (título, edição, URL) e listas que vão sendo preenchidas.
    meta = carregar_indice()
    rel = []      # uma linha do relatorio.csv por livro
    chunks = []   # todos os chunks de todos os livros
    # 3. Processa cada txt, em ordem alfabética (para a saída ser sempre igual).
    for arq in sorted(TXT.glob("*.txt")):
        linhas = arq.read_text(encoding="utf-8").split("\n")
        # Descobre o formato: se há "• Capítulo N •", veio de ePub (A); senão, de PDF (B).
        formato = "A" if any(CAP_A.match(l.strip()) for l in linhas) else "B"
        # Extrai os pares pergunta-resposta com o parser do formato.
        pares = parse_formato_a(linhas) if formato == "A" else parse_formato_b(linhas)
        m = meta.get(arq.stem, {})
        # Cultura e ano vêm do nome do arquivo: "500P_soja_2019" -> ("soja", "2019").
        cultura, ano = arq.stem.removeprefix("500P_").rsplit("_", 1)
        # 4. Chunks de introdução (ficam de fora do corpus final, mas o corpus completo os guarda).
        intro = extrair_introducao(linhas, formato)
        for k, parte in enumerate(intro, 1):
            chunk = {
                "id": f"{cultura}_{ano}_intro{k:02d}",
                "tipo": "introducao",
                "cultura": cultura,
                "titulo_livro": m.get("titulo"),
                "ano": int(ano),
                "edicao": m.get("edicao"),
                "capitulo_num": 0,
                "capitulo": "Introdução",
                "autores_capitulo": [],
                "numero_pergunta": None,
                "pergunta": None,
                "resposta": parte,
                "formato_origem": m.get("formato_original"),
                "url_origem": m.get("url_origem"),
                "arquivo_txt": arq.name,
                "texto": f"{cultura} | Introdução\n{parte}",
            }
            chunks.append(chunk)
        # 5. Um chunk por par pergunta-resposta, com os metadados do livro e do capítulo.
        for p in pares:
            cap = p["capitulo"]
            chunk = {
                "id": f"{cultura}_{ano}_q{p['numero']:03d}",
                "tipo": "pergunta_resposta",
                "cultura": cultura,
                "titulo_livro": m.get("titulo"),
                "ano": int(ano),
                "edicao": m.get("edicao"),
                "capitulo_num": cap["num"],
                "capitulo": cap["titulo"],
                "autores_capitulo": cap["autores"],
                "numero_pergunta": p["numero"],
                "pergunta": p["pergunta"],
                "resposta": p["resposta"],
                "formato_origem": m.get("formato_original"),
                "url_origem": m.get("url_origem"),
                "arquivo_txt": arq.name,
            }
            # "texto" é o que vira vetor: cultura e capítulo dão contexto à pergunta e à resposta.
            chunk["texto"] = f"{cultura} | {cap['titulo']}\nPergunta: {p['pergunta']}\nResposta: {p['resposta']}"
            chunks.append(chunk)
        # 6. Conferência do livro para o relatório: respostas curtas demais (suspeitas),
        #    número de capítulos e números de pergunta que não foram encontrados.
        vazias = sum(1 for p in pares if len(p["resposta"]) < 20)
        caps = sorted({p["capitulo"]["num"] for p in pares})
        faltam = sorted(set(range(1, 501)) - {p["numero"] for p in pares})
        rel.append({"arquivo": arq.name, "formato_txt": formato, "pares": len(pares),
                    "chunks_introducao": len(intro),
                    "capitulos": len(caps), "respostas_curtas": vazias,
                    "faltando": " ".join(map(str, faltam))})
    # 7. Sem --sem-divisao, já divide os chunks longos aqui (o mesmo que o dividir_chunks.py faz).
    if not args.sem_divisao:
        n_antes = len(chunks)
        chunks = dividir_chunks(chunks, contador_de_tokens(args.modelo), args.limite)
        print(f"divisão em até {args.limite} tokens: {n_antes} -> {len(chunks)} chunks")
    # 8. Grava os chunks (um JSON por linha) e o relatório em data/processed/auxiliares/.
    nome = "chunks_sem_divisao.jsonl" if args.sem_divisao else "chunks_completo.jsonl"
    with open(SAIDA / nome, "w", encoding="utf-8") as out:
        for chunk in chunks:
            out.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    with open(SAIDA / "relatorio.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rel[0]))
        w.writeheader()
        w.writerows(rel)
    for r in rel:
        print(r)
    print("pares:", sum(r["pares"] for r in rel), "| chunks de introdução:", sum(r["chunks_introducao"] for r in rel))


if __name__ == "__main__":
    main()
