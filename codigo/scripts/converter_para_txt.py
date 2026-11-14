"""Converte os livros da coleção 500 Perguntas 500 Respostas (ePub ou PDF) para txt, sem IA.

O script tem três passos, que rodam em sequência:

1. baixar: baixa cada livro listado em data/raw/fontes.csv pela URL da Infoteca, se o
   arquivo ainda não estiver na pasta, e confere o SHA-256. Se o hash ainda não estiver no CSV
   (primeira execução), ele é gravado lá.
2. converter: gera um txt por livro.
   - ePub → txt direto (sem passar por PDF): o ePub é um zip com páginas XHTML. A ordem de leitura
     vem do "spine" do arquivo OPF, e o texto de cada página é tirado com o BeautifulSoup, um
     bloco (parágrafo, título, item de lista) por vez, separados por linha em branco.
   - PDF → txt: `pdftotext` (Poppler), com as opções padrão, e depois junção das palavras que o
     livro quebra com hífen discricionário (U+00AD) no fim da linha.
3. comparar (opcional, com --comparar-com): compara os txt gerados com os de outra pasta (linhas
   diferentes) e, o que importa para o resto do pipeline, compara os pares pergunta-resposta que o
   src/chunking.py extrai de cada versão.

Os txt vão para data/raw/txt/, que é a entrada do src/chunking.py. Para conferir a
reprodução sem sobrescrever nada, gere numa pasta à parte e compare com a atual:
    python3 scripts/converter_para_txt.py --saida /tmp/txt --comparar-com data/raw/txt
Com as versões de txt/ferramentas.json, os 41 txt saem idênticos byte a byte. Com outra versão do
pdftotext, mudam só linhas do sumário dos PDFs, e os pares extraídos continuam idênticos.

Uso (a partir de codigo/):
    python3 scripts/converter_para_txt.py
    python3 scripts/converter_para_txt.py --sem-download      # usa só os arquivos já baixados
    python3 scripts/converter_para_txt.py --livros milho_2013 abacaxi_2013

Dependências: beautifulsoup4 (no requirements.txt) e o pdftotext do Poppler
(macOS: `brew install poppler`; Ubuntu: `apt install poppler-utils`).
"""

import argparse
import csv
import hashlib
import json
import posixpath
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import warnings
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import bs4
from bs4 import BeautifulSoup

# Deixa o Python achar os módulos de src/. Do chunking.py vêm os parsers, usados só no passo 3
# (comparar os pares extraídos de duas versões dos txt).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from chunking import CAP_A, extrair_introducao, parse_formato_a, parse_formato_b  # noqa: E402

# Caminhos, relativos à pasta codigo/.
CODIGO = Path(__file__).resolve().parent.parent
RAW = CODIGO / "data" / "raw"      # onde ficam epub/, PDFs/ e txt/
FONTES = RAW / "fontes.csv"        # lista dos livros: txt de saída, formato, arquivo fonte, URL, hash

# Elementos HTML que viram um bloco de texto próprio. Um bloco que tem outro bloco dentro (por
# exemplo, uma <div> com vários <p>) não é emitido inteiro: os blocos de dentro são emitidos um a um.
# Tabelas: cada linha (<tr>) vira um bloco, com as células separadas por espaço.
BLOCOS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "dt", "dd", "blockquote", "pre",
          "div", "section", "article", "header", "footer", "aside", "figcaption", "caption",
          "tr", "table", "ul", "ol", "dl", "figure", "body"}
CELULAS = {"td", "th"}
IGNORAR = {"script", "style", "head", "title", "nav"}


# ---------------------------------------------------------------------------------------------
# 1. baixar
# ---------------------------------------------------------------------------------------------

def sha256(caminho: Path) -> str:
    """Impressão digital (hash SHA-256) do arquivo. Se um único byte mudar, o hash muda."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        # Lê em blocos de 1 MB para não carregar o arquivo inteiro na memória.
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_fontes() -> list[dict]:
    """Lê o fontes.csv: uma linha (dicionário) por livro."""
    with open(FONTES, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def gravar_fontes(fontes: list[dict]):
    """Regrava o fontes.csv (usado só quando um hash novo foi registrado)."""
    with open(FONTES, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fontes[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(fontes)


def baixar(fontes: list[dict], sem_download: bool) -> bool:
    """Garante que cada fonte está na pasta e confere o hash. Devolve True se o CSV mudou."""
    mudou = False
    for f in fontes:
        destino = RAW / f["arquivo_fonte"]
        # Se o arquivo ainda não está na pasta, baixa da Infoteca.
        if not destino.exists():
            if sem_download:
                print(f"  falta {f['arquivo_fonte']} (rodando com --sem-download)")
                continue
            print(f"  baixando {f['arquivo_fonte']}")
            destino.parent.mkdir(parents=True, exist_ok=True)
            # Baixa para um arquivo ".part" e só renomeia no fim: se o download cair no meio,
            # não fica um arquivo pela metade com o nome certo.
            tmp = destino.with_suffix(destino.suffix + ".part")
            with urllib.request.urlopen(f["url"], timeout=120) as resp, open(tmp, "wb") as out:
                shutil.copyfileobj(resp, out)
            tmp.rename(destino)
        # Confere o hash: prova que o arquivo é exatamente o mesmo usado para gerar os txt.
        h = sha256(destino)
        if not f["sha256"]:
            f["sha256"] = h
            mudou = True
            print(f"  hash registrado: {f['arquivo_fonte']} {h[:12]}…")
        elif f["sha256"] != h:
            raise SystemExit(f"ERRO: {f['arquivo_fonte']} tem hash {h}, esperado {f['sha256']}. "
                             "O arquivo da Infoteca mudou ou o download veio corrompido.")
    return mudou


# ---------------------------------------------------------------------------------------------
# 2. converter
# ---------------------------------------------------------------------------------------------

def ordem_do_epub(z: zipfile.ZipFile) -> list[str]:
    """Caminhos (dentro do zip) das páginas XHTML, na ordem de leitura do spine."""
    # Nomes dos "espaços de nomes" XML usados pelo padrão ePub.
    ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container",
          "opf": "http://www.idpf.org/2007/opf"}
    # 1. O container.xml (sempre no mesmo lugar) diz onde está o arquivo OPF.
    container = ElementTree.fromstring(z.read("META-INF/container.xml"))
    opf_path = container.find(".//c:rootfile", ns).attrib["full-path"]
    opf = ElementTree.fromstring(z.read(opf_path))
    base = posixpath.dirname(opf_path)
    # 2. O manifesto do OPF liga cada id a um arquivo do zip.
    manifesto = {i.attrib["id"]: i.attrib["href"] for i in opf.find("opf:manifest", ns)}
    # 3. O spine lista os ids na ordem de leitura; traduzimos cada id para o caminho do arquivo.
    caminhos = []
    for item in opf.find("opf:spine", ns):
        href = manifesto[item.attrib["idref"]].split("#")[0]
        caminhos.append(posixpath.normpath(posixpath.join(base, urllib.parse.unquote(href))))
    return caminhos


QUEBRA = "\x00"  # marca de quebra de linha dentro de um bloco (<br> ou bloco dentro de célula)


def limpar(texto: str) -> str:
    """Junta os espaços em branco do HTML num espaço só. Tabulações e quebras marcadas ficam."""
    texto = texto.replace("\u00a0", " ")                 # espa\u00e7o insepar\u00e1vel -> espa\u00e7o comum
    texto = re.sub(r"[ \r\n]+", " ", texto)               # v\u00e1rias quebras/espa\u00e7os -> um espa\u00e7o
    texto = re.sub(r" *\x00[ \x00]*", QUEBRA, texto)      # espa\u00e7os em volta de uma quebra somem
    return texto.strip(" " + QUEBRA).replace(QUEBRA, "\n")  # tira as pontas; marca -> quebra de linha


def blocos_html(el) -> list[str]:
    """Texto do elemento, um item por bloco, na ordem do documento.

    Dentro de uma linha de tabela (<tr>), as células são separadas por espaço e um bloco dentro
    de uma célula (por exemplo, dois <p>) vira só uma quebra de linha. Um <br> vira quebra de linha.
    """
    saida = []                 # blocos de texto prontos
    corrente = []              # pedaços do bloco que está sendo montado
    em_linha_de_tabela = 0     # > 0 quando estamos dentro de um <tr>

    def descarregar():
        """Fecha o bloco atual: limpa os espaços e, se sobrou texto, guarda como um bloco."""
        t = limpar("".join(corrente))
        if t:
            saida.append(t)
        corrente.clear()

    def visitar(no):
        """Percorre a árvore do HTML (recursivamente), acumulando texto e fechando blocos."""
        nonlocal em_linha_de_tabela
        if isinstance(no, bs4.element.Comment):
            return
        if isinstance(no, bs4.element.NavigableString):
            corrente.append(str(no))
            return
        nome = (no.name or "").lower()
        if nome in IGNORAR:
            return
        if nome == "br":
            corrente.append(QUEBRA)
            return
        if nome == "hr":  # linha horizontal: vira "* * *", como nos txt originais
            descarregar()
            saida.append("* * *")
            return
        if nome in CELULAS:
            corrente.append(" ")       # células da mesma linha de tabela: separadas por espaço
        bloco = nome in BLOCOS
        # Ao ENTRAR num bloco: fecha o texto que vinha antes (dentro de tabela, só quebra a linha).
        if nome == "tr":
            descarregar()
            em_linha_de_tabela += 1
        elif bloco and em_linha_de_tabela:
            corrente.append(QUEBRA)
        elif bloco:
            descarregar()
        # Visita o que está dentro do elemento.
        for filho in no.children:
            visitar(filho)
        # Ao SAIR do bloco: fecha o texto dele (dentro de tabela, só quebra a linha).
        if nome == "tr":
            em_linha_de_tabela -= 1
            descarregar()
        elif bloco and em_linha_de_tabela:
            corrente.append(QUEBRA)
        elif bloco:
            descarregar()

    visitar(el)
    descarregar()
    return saida


def epub_para_txt(caminho: Path) -> str:
    """Texto do ePub inteiro: páginas na ordem de leitura, blocos separados por linha em branco."""
    partes = []
    # O ePub é um arquivo zip; abrimos sem descompactar no disco.
    with zipfile.ZipFile(caminho) as z:
        for nome in ordem_do_epub(z):
            # Lê a página XHTML e extrai os blocos de texto do <body>.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # aviso de XML lido como HTML
                sopa = BeautifulSoup(z.read(nome), "html.parser")
            corpo = sopa.body or sopa
            blocos = blocos_html(corpo)
            if blocos:
                partes.append("\n\n".join(blocos))
    # Páginas separadas por três linhas em branco.
    return "\n\n\n\n".join(partes) + "\n"


def versao_pdftotext() -> str:
    """Confere que o pdftotext está instalado e devolve a versão (gravada no ferramentas.json)."""
    if not shutil.which("pdftotext"):
        raise SystemExit("ERRO: pdftotext não encontrado. Instale o Poppler "
                         "(macOS: brew install poppler; Ubuntu: apt install poppler-utils).")
    r = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    return (r.stderr or r.stdout).splitlines()[0].strip()


def pdf_para_txt(caminho: Path) -> str:
    """Texto do PDF com o pdftotext (opções padrão); "-" manda a saída para o Python, não para arquivo."""
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(caminho), "-"],
                       capture_output=True, check=True)
    texto = r.stdout.decode("utf-8")
    # palavra quebrada com hífen discricionário no fim da linha: junta com a linha seguinte
    return re.sub("­\n(?=[^\n])", "", texto)


# ---------------------------------------------------------------------------------------------
# 3. comparar
# ---------------------------------------------------------------------------------------------

def pares(texto: str) -> dict:
    """Extrai de um txt o formato, os pares {número: (pergunta, resposta, capítulo)} e a
    introdução, com os mesmos parsers do src/chunking.py."""
    linhas = texto.split("\n")
    formato = "A" if any(CAP_A.match(l.strip()) for l in linhas) else "B"
    ps = parse_formato_a(linhas) if formato == "A" else parse_formato_b(linhas)
    return formato, {p["numero"]: (p["pergunta"], p["resposta"], p["capitulo"]["titulo"]) for p in ps}, \
        extrair_introducao(linhas, formato)


def comparar(nome: str, novo: str, atual_path: Path) -> dict:
    """Compara o txt recém-gerado (novo) com o de referência: linhas diferentes e, principalmente,
    pares pergunta-resposta iguais, diferentes ou que só existem numa das versões."""
    # Sem txt de referência para este livro: linha vazia no relatório.
    if not atual_path.exists():
        return {"arquivo": nome, "linhas_diferentes": "", "formato": "", "pares_atual": "",
                "pares_novo": "", "pares_iguais": "", "pares_diferentes": "", "so_no_atual": "",
                "so_no_novo": "", "introducao_igual": ""}
    atual = atual_path.read_text(encoding="utf-8")
    # Linhas que existem numa versão e não na outra (nos dois sentidos).
    la, ln = atual.split("\n"), novo.split("\n")
    sa, sn = set(la), set(ln)
    linhas_dif = sum(1 for l in la if l not in sn) + sum(1 for l in ln if l not in sa)
    # Pares extraídos de cada versão (é o que importa para o resto do pipeline).
    fa, pa, ia = pares(atual)
    fn, pn, inn = pares(novo)
    comuns = pa.keys() & pn.keys()   # números de pergunta presentes nas duas
    iguais = sum(1 for k in comuns if pa[k] == pn[k])
    return {"arquivo": nome, "linhas_diferentes": linhas_dif, "formato": f"{fa}->{fn}",
            "pares_atual": len(pa), "pares_novo": len(pn), "pares_iguais": iguais,
            "pares_diferentes": " ".join(str(k) for k in sorted(comuns) if pa[k] != pn[k]),
            "so_no_atual": " ".join(map(str, sorted(pa.keys() - pn.keys()))),
            "so_no_novo": " ".join(map(str, sorted(pn.keys() - pa.keys()))),
            "introducao_igual": ia == inn}


# ---------------------------------------------------------------------------------------------

def main():
    # Opções da linha de comando.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", type=Path, default=RAW / "txt",
                        help="pasta dos txt gerados (padrão: data/raw/txt)")
    parser.add_argument("--comparar-com", type=Path,
                        help="pasta com txt de referência para comparar (opcional)")
    parser.add_argument("--sem-download", action="store_true", help="não baixa o que faltar")
    parser.add_argument("--livros", nargs="*", help="só estes livros (ex.: milho_2013)")
    args = parser.parse_args()

    # Lê a lista de livros; com --livros, fica só com os pedidos ("500P_milho_2013.txt" -> "milho_2013").
    fontes = ler_fontes()
    if args.livros:
        fontes_sel = [f for f in fontes if f["arquivo_txt"][5:-4] in set(args.livros)]
    else:
        fontes_sel = fontes

    # Passo 1: garante que os arquivos estão na pasta e confere os hashes.
    print("1. baixar")
    if baixar(fontes_sel, args.sem_download):
        gravar_fontes(fontes)

    # Passo 2: converte cada livro e grava o txt.
    print("2. converter")
    # Anota as versões das ferramentas: com as mesmas versões, os txt saem idênticos byte a byte.
    precisa_pdf = any(f["formato"] == "pdf" for f in fontes_sel)
    ferramentas = {"python": sys.version.split()[0], "beautifulsoup4": bs4.__version__}
    if precisa_pdf:
        ferramentas["pdftotext"] = versao_pdftotext()
    args.saida.mkdir(parents=True, exist_ok=True)
    # Só compara se foi pedida uma pasta de referência diferente da de saída.
    mesma_pasta = args.comparar_com is None or args.saida.resolve() == args.comparar_com.resolve()
    relatorio = []
    for f in fontes_sel:
        fonte = RAW / f["arquivo_fonte"]
        if not fonte.exists():
            continue
        # ePub e PDF têm conversores diferentes; os dois devolvem o texto do livro.
        texto = epub_para_txt(fonte) if f["formato"] == "epub" else pdf_para_txt(fonte)
        (args.saida / f["arquivo_txt"]).write_text(texto, encoding="utf-8")
        if not mesma_pasta:
            relatorio.append(comparar(f["arquivo_txt"], texto, args.comparar_com / f["arquivo_txt"]))
        print(f"  {f['arquivo_txt']}")

    (args.saida / "ferramentas.json").write_text(json.dumps(ferramentas, indent=2, ensure_ascii=False) + "\n",
                                                 encoding="utf-8")
    if mesma_pasta:
        if args.comparar_com is not None:
            print("Saída e referência são a mesma pasta: comparação pulada.")
        return
    if not relatorio:
        print("Nenhum livro convertido.")
        return

    # Passo 3 (opcional): grava o comparacao.csv e mostra o resumo por livro.
    print("3. comparar com", args.comparar_com)
    with open(args.saida / "comparacao.csv", "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=list(relatorio[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(relatorio)
    tot_a = sum(r["pares_atual"] or 0 for r in relatorio)
    tot_i = sum(r["pares_iguais"] or 0 for r in relatorio)
    for r in relatorio:
        print(f"  {r['arquivo']:<55} {r['formato']:<5} pares iguais {r['pares_iguais']}/{r['pares_atual']}"
              f"  introdução igual {r['introducao_igual']}  linhas diferentes {r['linhas_diferentes']}")
    print(f"total: {tot_i} de {tot_a} pares idênticos aos atuais. Detalhes em {args.saida / 'comparacao.csv'}")
    print("ferramentas:", ferramentas)


if __name__ == "__main__":
    main()
