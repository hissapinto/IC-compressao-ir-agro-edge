"""Gera chunks (um por par pergunta-resposta) a partir dos txt da coleção 500 Perguntas 500 Respostas.

Uso (a partir de codigo/):
    python src/chunking.py                 # gera e divide os chunks longos (precisa do .venv)
    python src/chunking.py --sem-divisao   # só gera, sem tokenizer (biblioteca padrão)

Lê Embrapa/500PerguntasRespostas/txt/*.txt e PDFs/indice.csv; escreve chunks_sem_imagens.jsonl e
relatorio.csv em codigo/data/processed/auxiliares/. O chunks.jsonl final (com as transcrições
das imagens) não é sobrescrito por este script.

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

CODIGO = Path(__file__).resolve().parent.parent
RAW = CODIGO.parent / "500PerguntasRespostas"
TXT = RAW / "txt"
SAIDA = CODIGO / "data" / "processed" / "auxiliares"

FIM = re.compile(r"^(Mais alguma pergunta|Conheça outros títulos|Literatura (recomendada|consultada|citada)|(Notas|Referências?( bibliográficas)?|Índice( remissivo)?|Glossário)$)")
CAP_A = re.compile(r"^(?:•\s*)?Capítulo\s+(\d+)\s*•?$")
Q_A = re.compile(r"^(?:[a-z] )?(\d{1,3})\s*\)\s*(.*)$")  # aceita uma letra solta antes (ex.: "s 15)")
NUM = re.compile(r"^\d{1,3}$")
PERGUNTA_SEM_INTERROGACAO = re.compile(r"^(Qual|Quais|Como|O que|Que |Por que|Quando|Onde|Quanto|Quantos|Quantas) ")


def carregar_indice():
    """Metadados por nome de arquivo txt (cultura_ano), vindos do indice.csv."""
    meta = {}
    with open(RAW / "PDFs" / "indice.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            meta[Path(r["arquivo"]).stem] = r
    return meta


def juntar_linhas(linhas):
    """Junta linhas quebradas do PDF em parágrafos."""
    out = ""
    for l in linhas:
        l = l.strip()
        if not l:
            continue
        if not out:
            out = l
        elif out.endswith("-") and l[:1].islower():
            out = out + l
        elif l.startswith("•") or (out[-1] in ".:;!?" and l[:1].isupper()):
            out = out + "\n" + l
        else:
            out = out + " " + l
    return out


def parse_formato_a(linhas):
    """Livros vindos de epub: '• Capítulo N •' e perguntas 'N) texto'.

    No início de cada capítulo há uma lista só com as perguntas; ela termina em '•••'
    e depois as perguntas aparecem de novo, cada uma seguida da resposta.
    """
    pares, cap = [], None
    estado = "fora"  # fora | cabecalho | lista | corpo
    atual = None
    esperado = 1
    feitos, vistos = set(), {}

    def fechar():
        nonlocal atual
        if atual:
            atual["resposta"] = "\n".join(p for p in atual.pop("_linhas") if p.strip()).strip()
            pares.append(atual)
            atual = None

    for l in linhas:
        s = l.strip()
        m = CAP_A.match(s)
        if m:
            fechar()
            cap = {"num": int(m.group(1)), "titulo": None, "autores": []}
            estado = "cabecalho"
            vistos = {}
            continue
        if cap is None or not s:
            continue
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
            fechar()
            atual = {"numero": num, "pergunta": m.group(2).strip(), "capitulo": dict(cap), "_linhas": []}
            feitos.add(num)
            esperado = num + 1
        elif atual:
            atual["_linhas"].append(s)
    fechar()
    return sorted(pares, key=lambda p: p["numero"])


def parse_formato_b(linhas):
    """Livros vindos de PDF: número da pergunta sozinho na linha, com números de página,
    rodapés e quebras de página (\\f) no meio do texto."""
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
        if L[i].strip() != str(num):
            return None
        idx = proximas(i, 8)
        ant = anteriores(i, 6)
        antes_eh_pergunta = bool(ant) and L[ant[0]].strip().endswith("?")
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
    esperado_q, esperado_c = 1, 1
    i = 0

    def fechar():
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

    while i < n:
        s = L[i].strip()
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
        if cap is not None:
            if FIM.match(s):
                fechar()
                if esperado_q > 500:
                    break
            # se um número não for encontrado, tenta o seguinte para não travar o livro inteiro
            for num in (esperado_q, esperado_q + 1, esperado_q + 2):
                q = eh_pergunta(i, num)
                if q:
                    break
            if q:
                if atual and num == esperado_q + 1:
                    separar_pulada(esperado_q)
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
                i = max(q[-1], i) + 1
                continue
            if atual and s and not NUM.match(s):
                atual["_linhas"].append((i, s))
        i += 1
    fechar()
    return pares


def extrair_introducao(linhas, formato, max_chars=1500):
    """Texto da Introdução (entre o título 'Introdução' e o capítulo 1), dividido em
    partes de até max_chars respeitando parágrafos. Lista vazia se o livro não tiver."""
    L = [l.replace("\f", "").strip() for l in linhas]
    if formato == "A":
        fim = next((i for i, l in enumerate(L) if CAP_A.match(l)), None)
    else:
        fim = next((i for i, l in enumerate(linhas)
                    if "\f" in l and L[i] == "1" and i + 2 < len(L)
                    and not any(x.endswith("?") or ".." in x for x in L[i + 1:i + 4] if x)), None)
    if fim is None:
        return []
    inicio = max((i for i, l in enumerate(L[:fim]) if l == "Introdução"), default=None)
    if inicio is None:
        return []
    texto = juntar_linhas([l for l in L[inicio + 1:fim] if l and not NUM.match(l)])
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

PREFIXO = "passage: "
FIM_DE_FRASE = re.compile(r"(?<=[.!?;:])\s+")


def cabecalho(c: dict) -> str:
    """Parte do texto que se repete em todas as partes de um chunk dividido."""
    if c["tipo"] == "introducao":
        return f"{c['cultura']} | {c['capitulo']}\n"
    return f"{c['cultura']} | {c['capitulo']}\nPergunta: {c['pergunta']}\nResposta: "


def unidades(resposta: str) -> list[tuple[str, str]]:
    """Quebra a resposta em (trecho, separador que vinha antes dele): parágrafos e, dentro deles, frases."""
    saida = []
    for i, par in enumerate(resposta.split("\n")):
        for j, frase in enumerate(FIM_DE_FRASE.split(par)):
            if frase:
                saida.append((frase, "\n" if i and not j else " " if j else ""))
    return saida


def trechos_da_resposta(c: dict, n_tokens, limite: int) -> list[str]:
    """Divide a resposta em trechos que, junto com prefixo e cabeçalho, cabem no limite."""
    cab = cabecalho(c)
    cabe = lambda trecho: n_tokens(PREFIXO + cab + trecho) <= limite  # noqa: E731

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
        c = {**c, "id_original": c.get("id_original", c["id"])}
        if n_tokens(PREFIXO + c["texto"]) <= limite:
            saida.append({**c, "parte": 1, "total_partes": 1})
            continue
        partes = trechos_da_resposta(c, n_tokens, limite)
        for i, trecho in enumerate(partes, 1):
            saida.append({**c, "id": f"{c['id']}_p{i}", "parte": i, "total_partes": len(partes),
                          "resposta": trecho, "texto": cabecalho(c) + trecho})
    return saida


def contador_de_tokens(modelo: str):
    """n_tokens(texto) com o tokenizer do modelo de embedding (importa transformers só aqui)."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(modelo)
    return lambda t: len(tok(t, add_special_tokens=True)["input_ids"])


def main():
    parser = argparse.ArgumentParser(description="Gera os chunks a partir dos txt.")
    parser.add_argument("--modelo", default="intfloat/multilingual-e5-small", help="tokenizer usado na contagem")
    parser.add_argument("--limite", type=int, default=512, help="máximo de tokens por chunk")
    parser.add_argument("--sem-divisao", action="store_true", help="não divide os chunks longos")
    args = parser.parse_args()

    meta = carregar_indice()
    rel = []
    chunks = []
    for arq in sorted(TXT.glob("*.txt")):
        linhas = arq.read_text(encoding="utf-8").split("\n")
        formato = "A" if any(CAP_A.match(l.strip()) for l in linhas) else "B"
        pares = parse_formato_a(linhas) if formato == "A" else parse_formato_b(linhas)
        m = meta.get(arq.stem, {})
        cultura, ano = arq.stem.removeprefix("500P_").rsplit("_", 1)
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
            chunk["texto"] = f"{cultura} | {cap['titulo']}\nPergunta: {p['pergunta']}\nResposta: {p['resposta']}"
            chunks.append(chunk)
        vazias = sum(1 for p in pares if len(p["resposta"]) < 20)
        caps = sorted({p["capitulo"]["num"] for p in pares})
        faltam = sorted(set(range(1, 501)) - {p["numero"] for p in pares})
        rel.append({"arquivo": arq.name, "formato_txt": formato, "pares": len(pares),
                    "chunks_introducao": len(intro),
                    "capitulos": len(caps), "respostas_curtas": vazias,
                    "faltando": " ".join(map(str, faltam))})
    if not args.sem_divisao:
        n_antes = len(chunks)
        chunks = dividir_chunks(chunks, contador_de_tokens(args.modelo), args.limite)
        print(f"divisão em até {args.limite} tokens: {n_antes} -> {len(chunks)} chunks")
    with open(SAIDA / "chunks_sem_imagens.jsonl", "w", encoding="utf-8") as out:
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
