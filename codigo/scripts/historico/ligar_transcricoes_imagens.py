"""Registro histórico: liga cada transcrição de imagem feita com IA à imagem original. Rodado uma vez.

Em 27/10/2026 as imagens foram transcritas com IA a partir de PDFs (nos livros em ePub, de um PDF
gerado na conversa com a IA). O resultado ficou em imagens_transcritas.csv (livro, página do PDF,
transcrição) e chunks_alterados.jsonl (chunks com as transcrições já inseridas). Este script, sem IA:
1. compara cada chunk alterado com a versão sem imagens e acha onde cada transcrição foi inserida
   (todas as alterações são só acréscimos);
2. lista as imagens de cada livro direto da fonte: no ePub, pela ordem do HTML, com a pergunta em que
   cada imagem aparece; no PDF, pelas imagens da página, com os mesmos filtros da triagem original
   (área de pelo menos 400 pt² e imagem que não se repete mais de duas vezes no livro);
3. escolhe, entre as imagens da mesma pergunta (ePub) ou da mesma página (PDF), a que tem o texto
   logo antes dela mais parecido com o texto antes do ponto de inserção. Empates são resolvidos pela
   ordem no documento. Uma figura do PDF montada com muitos pedaços (trigo q494) é registrada com
   todos os pedaços;
4. grava data/processed/transcricoes_imagens.csv, que substitui os dois arquivos acima.

Uso (precisa de beautifulsoup4 e pymupdf):
    python3 scripts/historico/ligar_transcricoes_imagens.py <pasta Embrapa> <saida.csv>
"""
import csv,json,zipfile,re,sys,difflib,hashlib,unicodedata,posixpath,urllib.parse,collections
from pathlib import Path
from xml.etree import ElementTree
import bs4
from bs4 import BeautifulSoup
import pymupdf
E=Path(sys.argv[1]); A=E/'codigo/data/processed/auxiliares'; R=E/'500PerguntasRespostas'
sys.path.insert(0,str(E/'codigo/src')); sys.path.insert(0,str(E/'codigo/scripts'))
from chunking import Q_A
import converter_para_txt as conv
L=lambda f:[json.loads(l) for l in open(f,encoding='utf-8')]
alt=L(A/'chunks_alterados.jsonl'); base={c['id']:c for c in L(A/'chunks_sem_imagens.jsonl')}
tr=list(csv.DictReader(open(A/'imagens_transcritas.csv',encoding='utf-8')))
fontes={r['arquivo_txt'][:-4]:r for r in csv.DictReader(open(R/'fontes.csv'))}
def norm(s):
    s=unicodedata.normalize('NFKD',s.lower()); s=''.join(ch for ch in s if ch.isalnum()); return s
# 1. insertion points
ins=[] # (id, offset, inserted_text)
for c in alt:
    x,y=base[c['id']]['resposta'],c['resposta']
    for o in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes():
        if o[0]=='insert': ins.append((c['id'],o[1],y[o[3]:o[4]]))
# map transcription -> insertion
rows=[]
for i,t in enumerate(tr):
    pref=t['livro'][5:]+'_'
    m=[(cid,off,txt) for cid,off,txt in ins if cid.startswith(pref) and t['transcricao'].strip() in txt]
    rows.append(dict(t=t,m=m))
print('transcricoes sem insercao:',[(r['t']['livro'],r['t']['pagina_pdf'],r['t']['transcricao'][:60]) for r in rows if len(r['m'])!=1])
# greedy sequential assignment per book
por_livro=collections.defaultdict(list)
for i,t in enumerate(tr): por_livro[t['livro']].append(i)
qnum=lambda cid:int(cid.rsplit('_q',1)[1])
assign={}
falhas=[]
for livro,idx in por_livro.items():
    pref=livro[5:]+'_'
    insl=sorted([x for x in ins if x[0].startswith(pref)],key=lambda x:(qnum(x[0]),x[1]))
    j=0
    for cid,off,txt in insl:
        rest=txt
        while j<len(idx) and tr[idx[j]]['transcricao'].strip() and tr[idx[j]]['transcricao'].strip() in rest:
            k=rest.index(tr[idx[j]]['transcricao'].strip())
            assign[idx[j]]=(cid,off)
            rest=rest[k+len(tr[idx[j]]['transcricao'].strip()):]
            j+=1
        if norm(rest): falhas.append((livro,cid,rest[:80]))
    if j!=len(idx): falhas.append((livro,'sobrou',len(idx)-j))
print('atribuidas',len(assign),'falhas',falhas)
# 2. images in epub with question + preceding text
def imagens_epub(caminho):
    out=[]
    with zipfile.ZipFile(caminho) as z:
        q=None; antes=[]
        for nome in conv.ordem_do_epub(z):
            sopa=BeautifulSoup(z.read(nome),'html.parser')
            corpo=sopa.body or sopa
            for el in corpo.find_all(['img','p','h1','h2','h3','h4','li','td','div']):
                if el.name=='img':
                    src=(el.get('src') or '').replace('\\','/')
                    caminho_img=posixpath.normpath(posixpath.join(posixpath.dirname(nome),urllib.parse.unquote(src)))
                    out.append(dict(q=q,img=caminho_img,antes=' '.join(antes[-3:]),hash=hashlib.sha256(z.read(caminho_img)).hexdigest() if caminho_img in z.namelist() else None))
                    continue
                if el.find(['p','div','li','td','h1','h2','h3','h4']): continue
                t=conv.limpar(el.get_text(' '))
                if not t: continue
                m=Q_A.match(t)
                if m: q=int(m.group(1)); antes=[]
                else: antes.append(t)
    return out
cache={}
res=[]
for i,t in enumerate(tr):
    cid,off=assign[i]; q=qnum(cid); f=fontes[t['livro']]
    anc=norm(base[cid]['resposta'][:off])[-60:]
    if f['formato']=='epub':
        if t['livro'] not in cache: cache[t['livro']]=imagens_epub(R/f['arquivo_fonte'])
        cands=[x for x in cache[t['livro']] if x['q']==q]
        res.append(dict(i=i,cid=cid,off=off,anc=anc,cands=cands,fmt='epub'))
    else:
        res.append(dict(i=i,cid=cid,off=off,anc=anc,cands=None,fmt='pdf'))
c=collections.Counter((r['fmt'], len(r['cands']) if r['cands'] is not None else -1) for r in res)
print(c)
print('img sem arquivo', sum(1 for v in cache.values() for x in v if x['hash'] is None))
def score(anc,antes):
    a=norm(antes)[-60:]
    if not a or not anc: return 0
    m=difflib.SequenceMatcher(None,anc,a,autojunk=False).find_longest_match(0,len(anc),0,len(a))
    return m.size
for r in res:
    if r['fmt']=='epub' and len(r['cands'])>1:
        sc=[score(r['anc'],x['antes']) for x in r['cands']]
        r['sc']=sc
def imagens_pdf_pagina(doc,pno):
    pg=doc[pno]; out=[]
    linhas=[]
    if pno>0:
        anterior=' '.join(l for l in doc[pno-1].get_text().split('\n') if l.strip())[-300:]
        linhas.append((-1e9,anterior))
    for b in pg.get_text('dict')['blocks']:
        if b['type']==0:
            for l in b['lines']:
                t=''.join(s['text'] for s in l['spans']).strip()
                if t: linhas.append((l['bbox'][1],t))
    for info in pg.get_image_info(xrefs=True):
        x=info['xref']
        if not x: continue
        y0=info['bbox'][1]
        antes=' '.join(t for y,t in sorted(linhas) if y<y0)[-300:]
        raw=doc.extract_image(x)
        out.append(dict(xref=x,bbox=[round(v,1) for v in info['bbox']],antes=antes,hash=hashlib.sha256(raw['image']).hexdigest(),ext=raw['ext'],w=raw['width'],h=raw['height']))
    return out
docs={}
for r in res:
    if r['fmt']!='pdf': continue
    t=tr[r['i']]; f=fontes[t['livro']]
    if t['livro'] not in docs: docs[t['livro']]=pymupdf.open(R/f['arquivo_fonte'])
    d=docs[t['livro']]; p=int(t['pagina_pdf'])
    r['cands1']=imagens_pdf_pagina(d,p-1)  # pagina_pdf conta a partir de 1
# filters for pdf candidates
rep={}
for livro,d in docs.items():
    cnt=collections.Counter()
    for pg in d:
        for x in {i[0] for i in pg.get_images(full=True)}: cnt[x]+=1
    rep[livro]=cnt
for r in res:
    if r['fmt']=='pdf':
        livro=tr[r['i']]['livro']
        r['cands']=[x for x in r['cands1'] if (x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1])>=400 and rep[livro][x['xref']]<=2]
# assignment per chunk
from itertools import groupby
final={}
duvidas=[]
grp=collections.defaultdict(list)
for r in res: grp[(r['cid'],r['fmt'], tr[r['i']]['pagina_pdf'] if r['fmt']=='pdf' else '')].append(r)
for k,rs in grp.items():
    rs.sort(key=lambda r:(r['off'],r['i']))
    usados=set()
    for r in rs:
        cands=r['cands']
        if not cands: duvidas.append((r['cid'],'sem candidata')); continue
        sc=[score(r['anc'],x['antes']) for x in cands]
        livres=[j for j in range(len(cands)) if j not in usados] or list(range(len(cands)))
        best=max(livres,key=lambda j:(sc[j],-j))
        usados.add(best)
        r['esc']=cands[best]; r['score']=sc[best]
        if len(cands)>1 and sorted(sc,reverse=True)[0:2].count(sc[best])>1 and len(rs)==1: duvidas.append((r['cid'],'empate',sc))
        if len(cands)>1 and sc[best]<20: duvidas.append((r['cid'],'score baixo',sc))
print('duvidas',duvidas)
# composite figure: many fragments tied -> take all
for r in res:
    if r['fmt']=='pdf' and len(r['cands'])>5:
        frag=sorted(r['cands'],key=lambda x:x['xref'])
        r['esc']=dict(xref='+'.join(str(x['xref']) for x in frag),hash=hashlib.sha256(''.join(x['hash'] for x in frag).encode()).hexdigest())
# prefix/suffix per row within each insertion
grp2=collections.defaultdict(list)
for r in res: grp2[(r['cid'],r['off'])].append(r)
txt_ins={(c,o):t for c,o,t in ins}
for k,rs in grp2.items():
    rs.sort(key=lambda r:r['i'])
    t=txt_ins[k]; pos=0
    for n,r in enumerate(rs):
        tt=tr[r['i']]['transcricao'].strip()
        a=t.index(tt,pos); r['prefixo']=t[pos:a]; pos=a+len(tt); r['sufixo']=''
        r['ordem']=n+1
    rs[-1]['sufixo']=t[pos:]
    assert ''.join(r['prefixo']+tr[r['i']]['transcricao'].strip()+r['sufixo'] for r in rs)==t
esc=lambda s:s.replace('\\','\\\\').replace('\n','\\n').replace('\t','\\t')
out=[]
for r in sorted(res,key=lambda r:(r['cid'].rsplit('_q',1)[0],qnum(r['cid']),r['off'],r['ordem'])):
    t=tr[r['i']]; f=fontes[t['livro']]; e=r['esc']
    imagem = e['img'] if r['fmt']=='epub' else f"pagina {t['pagina_pdf']}, xref {e['xref']}"
    out.append({'livro':t['livro'],'fonte':f['arquivo_fonte'],'imagem':imagem,'sha256_imagem':e['hash'] or '',
        'id_chunk':r['cid'],'posicao':r['off'],'ordem':r['ordem'],
        'ancora':base[r['cid']]['resposta'][max(0,r['off']-60):r['off']].replace('\n',' '),
        'prefixo':esc(r['prefixo']),'transcricao':t['transcricao'].strip(),'sufixo':esc(r['sufixo'])})
with open(sys.argv[2],'w',encoding='utf-8',newline='') as fo:
    w=csv.DictWriter(fo,fieldnames=list(out[0]),lineterminator='\n'); w.writeheader(); w.writerows(out)
print('linhas',len(out),'sem hash',[o['id_chunk'] for o in out if not o['sha256_imagem']], 'prefixos',collections.Counter(o['prefixo'] for o in out),'sufixos',collections.Counter(o['sufixo'] for o in out))
