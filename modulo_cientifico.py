import csv, re, sys, unicodedata, hashlib, json, urllib.request, urllib.error, urllib.parse, time, os, subprocess
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QFont, QColor, QPainter, QPen, QBrush, QPixmap
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
 QPushButton,QFileDialog,QTableWidget,QTableWidgetItem,QLabel,QProgressBar,QMessageBox,
 QHeaderView,QCheckBox,QFrame,QSizePolicy)

EXTS={'.csv','.ris','.bib','.pdf'}
def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).casefold()
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]',' ',''.join(c for c in s if not unicodedata.combining(c)))).strip()
def doi(s):
    s=str(s or '')
    m=re.search(r'10\.\d{4,9}/[^\s<>"\']+',s,re.I)
    return m.group(0).rstrip('.,;:)]}') .lower() if m else ''
def year(s):
    m=re.search(r'(?:19|20)\d{2}',str(s or ''))
    return m.group(0) if m else ''
def record(title='',identifier='',yr='',authors='',journal='',source='',filename='',kind='',confidence=''):
    return dict(title=str(title or '').strip(),doi=doi(identifier),year=year(yr),
        authors=str(authors or '').strip(),journal=str(journal or '').strip(),
        source=str(source),file=str(filename),kind=kind,confidence=confidence,hash='')
def field(row,*names):
    d={norm(k):v for k,v in row.items() if k is not None}
    for n in names:
        v=d.get(norm(n))
        if v and str(v).strip():return v
    return ''
def read_text(path):
    data=path.read_bytes()
    for enc in ('utf-8-sig','cp1252','latin-1'):
        try:return data.decode(enc)
        except UnicodeDecodeError:pass
    return data.decode('utf-8',errors='replace')
def parse_csv(path):
    text=read_text(path)
    try: dialect=csv.Sniffer().sniff(text[:10000],delimiters=',;\t')
    except csv.Error:dialect=csv.excel
    out=[]
    for r in csv.DictReader(text.splitlines(),dialect=dialect):
        if not any(v for v in r.values()):continue
        out.append(record(field(r,'Title','Article Title','Document Title'),
            field(r,'DOI','DOI Link'),field(r,'Year','Publication Year','Published'),
            field(r,'Authors','Author Full Names','Author(s)'),
            field(r,'Source title','Journal','Publication Title','Source'),
            path.name,path,'CSV','Metadados importados'))
    return out
def parse_ris(path):
    out=[];d={}
    for line in read_text(path).splitlines():
        m=re.match(r'^([A-Z][A-Z0-9])\s{1,2}-\s?(.*)$',line)
        if not m:continue
        k,v=m.groups()
        if k=='TY':d={}
        elif k=='ER':
            def first(*keys):
                for k in keys:
                    if d.get(k):return d[k][0]
                return ''
            out.append(record(first('TI','T1','CT'),first('DO'),first('PY','Y1','DA'),
                '; '.join(d.get('AU',[]) or d.get('A1',[])),
                first('JO','JF','T2','JA'),path.name,path,'RIS','Metadados importados'))
            d={}
        else:d.setdefault(k,[]).append(v)
    return out
def bib_entries(text):
    pos=0
    while True:
        m=re.search(r'@([a-zA-Z]+)\s*([({])',text[pos:])
        if not m:break
        start=pos+m.end();op=m.group(2);cl='}' if op=='{' else ')'
        depth=1;quoted=False;escaped=False;i=start
        while i<len(text) and depth:
            c=text[i]
            if c=='"' and not escaped:quoted=not quoted
            if not quoted:
                if c==op:depth+=1
                elif c==cl:depth-=1
            escaped=(c=='\\' and not escaped)
            if c!='\\':escaped=False
            i+=1
        if depth==0 and m.group(1).lower() not in ('string','preamble','comment'):
            yield text[start:i-1]
        pos=max(i,start+1)
def parse_bib(path):
    out=[]
    for entry in bib_entries(read_text(path)):
        d={};start=entry.find(',');s=entry[start+1:] if start>=0 else entry;i=0
        while i<len(s):
            m=re.search(r'([\w-]+)\s*=\s*',s[i:])
            if not m:break
            k=m.group(1).lower();j=i+m.end()
            if j>=len(s):break
            if s[j] in '{"':
                op=s[j];cl='}' if op=='{' else '"';depth=1;j+=1;begin=j
                while j<len(s) and depth:
                    if s[j]==op and op=='{':depth+=1
                    elif s[j]==cl:depth-=1
                    j+=1
                val=s[begin:j-1]
            else:
                begin=j
                while j<len(s) and s[j]!=',':j+=1
                val=s[begin:j]
            d[k]=val.strip().replace('{','').replace('}','');i=j+1
        out.append(record(d.get('title'),d.get('doi'),d.get('year'),
            d.get('author'),d.get('journal') or d.get('journaltitle') or d.get('booktitle'),
            path.name,path,'BibTeX','Metadados importados'))
    return out
def plausible_title(s):
    s=re.sub(r'\s+',' ',str(s or '')).strip(' .')
    if len(s)<18 or len(s)>300:return ''
    if norm(s) in ('microsoft word','untitled','document','adobe indesign','research open access'):return ''
    if re.match(r'^(research\s+open\s+access|published by |original article|review article)',s,re.I):return ''
    if re.match(r'^(https?://|doi:|abstract\b|keywords\b|downloaded from\b)',s,re.I):return ''
    return s
def pdf_title_from_lines(text):
    lines=[re.sub(r'\s+',' ',x).strip() for x in text.splitlines()]
    lines=[x for x in lines if x]
    # PDF layout varies: only use a conservative candidate before "Abstract".
    for i,line in enumerate(lines[:35]):
        if re.match(r'^(abstract|researchgate|see discussions|article in|doi[: ]|downloaded from)',line,re.I):continue
        if re.search(r'10\.\d{4,9}/',line):continue
        candidate=plausible_title(line)
        if candidate and len(candidate.split())>=5 and not re.match(r'^\d|^www\.|^https?:',candidate):
            return candidate
    return ''
def parse_pdf(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    title='';authors='';identifier='';yr='';journal='';confidence='Não identificado';first='';candidates=[]
    try:
        from pypdf import PdfReader
        reader=PdfReader(str(path));meta=reader.metadata
        first='\n'.join((p.extract_text() or '') for p in reader.pages[:2])[:30000]
        candidates=list(dict.fromkeys(doi(m.group(0)) for m in re.finditer(r'10\.\d{4,9}/[^\s<>\"\']+',first[:18000],re.I)))[:8]
        identifier=candidates[0] if candidates else ''
        if meta:
            title=plausible_title(getattr(meta,'title',''))
            authors=str(getattr(meta,'author','') or '').strip()
            yr=year(str(getattr(meta,'creation_date','') or ''))
        if not title:title=pdf_title_from_lines(first)
        # Only infer year from near the beginning, not the bibliography.
        if not yr:yr=year(first[:1500])
        confidence='DOI encontrado no PDF' if identifier else ('Título provável — conferir' if title else 'Metadados insuficientes')
    except ImportError:
        confidence='Instale pypdf para extrair dados'
    except Exception as e:
        confidence='Falha de leitura do PDF: '+str(e)[:70]
    r=record(title,identifier,yr,authors,journal,path.name,path,'PDF',confidence)
    r['hash']=h.hexdigest();r['pdf_text']=first[:14000];r['doi_candidates']=candidates
    return [r]
def parse_file(path):
    return {'.csv':parse_csv,'.ris':parse_ris,'.bib':parse_bib,'.pdf':parse_pdf}[path.suffix.lower()](path)
def format_one_author(name):
    name=str(name).strip().strip('{}')
    if not name:return ''
    if ',' in name:
        surname,given=(x.strip() for x in name.split(',',1))
    else:
        bits=name.split()
        if len(bits)<2:return name.upper()
        surname=bits[-1];given=' '.join(bits[:-1])
        if len(bits)>2 and bits[-2].lower() in ('da','de','do','das','dos'):
            surname=' '.join(bits[-2:]);given=' '.join(bits[:-2])
    return f'{surname.upper()}, {given}' if given else surname.upper()
def authors_abnt(raw):
    raw=str(raw or '').strip()
    if not raw:return ''
    if ' and ' in raw: parts=re.split(r'\s+and\s+',raw,flags=re.I)
    elif ';' in raw:parts=raw.split(';')
    elif re.search(r'\b[A-Z][a-z]+,\s*[A-Z]',raw):parts=[raw]
    else:parts=[raw] # Avoid guessing comma-separated ambiguous author names.
    return '; '.join(format_one_author(p) for p in parts if p.strip())
def crossref_metadata(identifier):
    """Busca metadados pelo DOI; não modifica os arquivos locais."""
    url='https://api.crossref.org/works/'+urllib.parse.quote(identifier,safe='/')
    request=urllib.request.Request(url,headers={
        'User-Agent':'OrganizadorCientifico/0.5 (academic reference metadata lookup)',
        'Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=12) as response:
        msg=json.load(response)['message']
    title=(msg.get('title') or [''])[0]
    journal=(msg.get('container-title') or [''])[0]
    authors=[]
    for a in msg.get('author',[]):
        family=a.get('family','').strip()
        given=a.get('given','').strip()
        if family:authors.append(f'{family}, {given}' if given else family)
    yr=''
    for key in ('published','published-print','published-online','issued'):
        parts=msg.get(key,{}).get('date-parts',[])
        if parts and parts[0]:yr=str(parts[0][0]);break
    return dict(title=title,authors='; '.join(authors),year=yr,journal=journal,doi=doi(msg.get('DOI','')))

def crossref_by_title(title):
    """Aceita resultado apenas se o título tiver correspondência forte."""
    query=urllib.parse.urlencode({'query.title':title,'rows':3})
    request=urllib.request.Request('https://api.crossref.org/works?'+query,headers={
        'User-Agent':'OrganizadorCientifico/0.5 (academic reference metadata lookup)',
        'Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=12) as response:
        items=json.load(response)['message'].get('items',[])
    best=None;score=0
    for item in items:
        candidate=(item.get('title') or [''])[0]
        sim=SequenceMatcher(None,norm(title),norm(candidate)).ratio()
        if sim>score:best=item;score=sim
    if not best or score<0.92:return None
    identifier=doi(best.get('DOI',''))
    if not identifier:return None
    return crossref_metadata(identifier),score

def groups(records):
    # Somente hash idêntico ou DOI confirmado geram duplicata automática.
    # Títulos iguais sem DOI são apresentados para revisão, não excluídos.
    parent=list(range(len(records)))
    reasons={}
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b,why):
        ra,rb=root(a),root(b)
        if ra!=rb:parent[rb]=ra
        reasons[b]=why
    dois={};hashes={}
    for i,r in enumerate(records):
        if r.get('hash'):
            if r['hash'] in hashes:union(hashes[r['hash']],i,'PDF idêntico (SHA-256)')
            else:hashes[r['hash']]=i
        if r['doi'] and r.get('doi_verified'):
            if r['doi'] in dois:union(dois[r['doi']],i,'Mesmo DOI confirmado')
            else:dois[r['doi']]=i
    result=defaultdict(list)
    for i in range(len(records)):result[root(i)].append(i)
    for ids in result.values():
        if len(ids)>1:
            why='PDF idêntico (SHA-256)' if len({records[i].get('hash') for i in ids})==1 and records[ids[0]].get('hash') else 'Mesmo DOI confirmado'
            for i in ids:records[i]['duplicate_reason']=why
    return list(result.values())

class Worker(QThread):
    progress=Signal(int,int,str);completed=Signal(object,object,object)
    def __init__(self,files,online=True):super().__init__();self.files=files;self.online=online
    def run(self):
        records=[];errors=[]
        for n,p in enumerate(self.files,1):
            try:records.extend(parse_file(Path(p)))
            except Exception as e:errors.append(f'{p}: {e}')
            self.progress.emit(n,len(self.files),Path(p).name)
        if self.online:
            cache={};title_cache={}
            for i,r in enumerate(records,1):
                meta=None;method='';original_doi=r['doi']
                candidates=r.get('doi_candidates',[]) if r['kind']=='PDF' else ([original_doi] if original_doi else [])
                # Confirmar DOI comparando o título Crossref com o texto da primeira página.
                for candidate_doi in candidates:
                    if candidate_doi not in cache:
                        try:cache[candidate_doi]=crossref_metadata(candidate_doi)
                        except Exception:cache[candidate_doi]=None
                    candidate=cache[candidate_doi]
                    if not candidate or not candidate['title']:continue
                    title_norm=norm(candidate['title'])
                    extracted_norm=norm(r['title'])
                    page_norm=norm(r.get('pdf_text','')[:9500])
                    sim=SequenceMatcher(None,title_norm,extracted_norm).ratio() if extracted_norm else 0
                    # Presença do título no próprio artigo é evidência melhor que metadado PDF ruim.
                    in_page=(len(title_norm)>=22 and title_norm in page_norm)
                    if r['kind']!='PDF' or in_page or sim>=0.78:
                        meta=candidate;method='DOI verificado';r['doi']=candidate_doi;r['doi_verified']=True
                        break
                if not meta and r['title'] and len(norm(r['title']))>=25:
                    key=r['title']
                    if key not in title_cache:
                        try:title_cache[key]=crossref_by_title(key)
                        except Exception:title_cache[key]=None
                    hit=title_cache[key]
                    if hit:
                        candidate,similarity=hit
                        if original_doi and candidate['doi']!=original_doi:
                            r['confidence']='REVISAR: DOI extraído difere do resultado por título'
                        else:
                            meta=candidate;method='título (similaridade alta)';r['doi']=candidate['doi'];r['doi_verified']=True
                if meta:
                    for k in ('title','authors','year','journal'):
                        if meta.get(k):r[k]=meta[k]
                    r['confidence']='Crossref — '+method
                elif r['kind']=='PDF' and candidates:
                    r['doi']=''  # Evitar atribuir DOI de referências citadas.
                    r['confidence']='REVISAR: DOI não confirmado para este artigo'
                elif not r['confidence'].startswith('REVISAR'):
                    r['confidence']+=' | Crossref sem confirmação'
                self.progress.emit(i,len(records),'Verificando metadados: '+str(i))
        else:
            # Sem consulta externa, somente hashes idênticos são duplicatas automáticas.
            for r in records:r['doi_verified']=False
        self.completed.emit(records,groups(records),errors)

def logo_pixmap():
    """Ícone vetorial desenhado no Qt, sem arquivos de imagem externos."""
    pix=QPixmap(92,72);pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#e88a4b'),3))
    p.setBrush(QBrush(QColor('#f4a36b')))
    from PySide6.QtGui import QPolygonF
    from PySide6.QtCore import QPointF
    p.drawPolygon(QPolygonF([QPointF(8,17),QPointF(25,13),QPointF(44,21),QPointF(44,58),QPointF(24,49),QPointF(8,53)]))
    p.drawPolygon(QPolygonF([QPointF(48,21),QPointF(66,13),QPointF(84,17),QPointF(84,53),QPointF(66,49),QPointF(48,58)]))
    p.setBrush(QBrush(QColor('#145caa')));p.setPen(QPen(QColor('#ffffff'),2))
    p.drawPolygon(QPolygonF([QPointF(13,20),QPointF(27,18),QPointF(44,25),QPointF(44,54),QPointF(27,45),QPointF(13,47)]))
    p.drawPolygon(QPolygonF([QPointF(48,25),QPointF(65,18),QPointF(79,20),QPointF(79,47),QPointF(65,45),QPointF(48,54)]))
    p.setPen(QPen(QColor('#cde7ff'),1.4))
    for y in (28,35,42):
        p.drawLine(18,y,37,y+3);p.drawLine(55,y+3,74,y)
    p.end()
    return pix

STYLE = """
QMainWindow { background: #f1f4f9; }
QWidget { font-family: 'Segoe UI', Arial; font-size: 12px; color: #172b49; }
QFrame#hero { background: #fbfcfe; border-bottom: 1px solid #dbe4f0; }
QLabel#brand { color: #12396d; font-size: 18px; font-weight: 800; letter-spacing: 2px; }
QLabel#software { color: #1765b4; font-size: 11px; font-weight: 700; letter-spacing: 3px; }
QLabel#headline { color: #102c55; font-size: 25px; font-weight: 750; }
QLabel#subtitle { color: #596b85; font-size: 13px; }
QLabel#section { color: #233d61; font-size: 13px; font-weight: 700; }
QLabel#muted { color: #61728a; font-size: 11px; }
QLabel#credit { color: #6d7c91; font-size: 10px; }
QLabel#folderPath { background: white; border: 1px solid #d4deec; border-bottom: 2px solid #1976d2; border-radius: 7px; padding: 11px; color: #42516a; }
QPushButton { background: white; border: 1px solid #cbd8e9; border-radius: 7px; padding: 10px 16px; font-weight: 600; }
QPushButton:hover { background: #eaf3ff; border-color: #87b9ed; }
QPushButton:disabled { color: #9caabd; background: #f5f7fa; }
QPushButton#primary { background: #1466c5; color: white; border: 1px solid #1466c5; font-size: 14px; font-weight: 700; padding: 14px; }
QPushButton#primary:hover { background: #0d54a7; }
QPushButton#export { background: #e6f5ed; border: 1px solid #8ccdb0; color: #087548; font-weight: 700; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QProgressBar { border: 0; border-radius: 4px; background: #dce6f3; height: 9px; text-align: center; color: transparent; }
QProgressBar::chunk { border-radius: 4px; background: #1676cc; }
QTableWidget { background: white; alternate-background-color: #f6f9fd; border: 1px solid #dbe4ef; gridline-color: #e4ebf3; selection-background-color: #dceeff; selection-color: #173658; }
QHeaderView::section { background: #e9f1fb; color: #143b6d; font-weight: 800; border: 0; border-right: 1px solid #d0dfef; border-bottom: 2px solid #9abbe0; padding: 11px 7px; }
QTableCornerButton::section { background: #e9f1fb; border: 0; }
"""
class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Organizador Inteligente — Módulo Científico v0.6 | Constantino Software')
        self.resize(1450,850)
        self.setStyleSheet(STYLE)
        central=QWidget();self.setCentralWidget(central)
        layout=QVBoxLayout(central);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        hero=QFrame();hero.setObjectName('hero')
        h=QHBoxLayout(hero);h.setContentsMargins(22,5,22,5);h.setSpacing(14)
        brand=QWidget();brand.setFixedWidth(365)
        brandrow=QHBoxLayout(brand);brandrow.setContentsMargins(0,0,0,0);brandrow.setSpacing(8)
        logo=QLabel();logo.setFixedSize(116,98)
        asset_root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
        image=asset_root/'constantino_emblema.png'
        if image.exists():
            pix=QPixmap(str(image))
            logo.setPixmap(pix.scaled(116,98,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brandrow.addWidget(logo)
        brandtext=QLabel('Constantino\nSoftware')
        brandtext.setStyleSheet('color:#12396d;font-size:25px;font-weight:800;')
        brandtext.setMinimumWidth(225);brandrow.addWidget(brandtext,1)
        h.addWidget(brand)
        divider=QFrame();divider.setFrameShape(QFrame.Shape.VLine);h.addWidget(divider)
        heading=QVBoxLayout();heading.setSpacing(1)
        title_row=QHBoxLayout();title_row.setSpacing(11)
        title=QLabel('Organizador Inteligente');title.setObjectName('headline');title_row.addWidget(title)
        for kind,tip in [('artigo','Artigo'),('microscopio','Microscópio'),('esquadro','Esquadro'),('frasco','Laboratório'),('pesquisa','Pesquisa')]:
            icon=QLabel();icon.setFixedSize(28,28);icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            file=asset_root/'icones'/(kind+'.png')
            if file.exists():
                icon.setPixmap(QPixmap(str(file)).scaled(27,27,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            icon.setToolTip(tip+' (decorativo)');title_row.addWidget(icon)
        title_row.addStretch();heading.addLayout(title_row)
        sub=QLabel('Módulo Científico  •  Artigos e duplicatas')
        sub.setObjectName('subtitle');heading.addWidget(sub)
        h.addLayout(heading,1)
        layout.addWidget(hero)

        body=QWidget();b=QVBoxLayout(body);b.setContentsMargins(32,22,32,12);b.setSpacing(13)
        controls=QHBoxLayout();controls.setSpacing(10)
        self.folder=QPushButton('▱  Selecionar pasta');self.folder.clicked.connect(self.pick_folder);controls.addWidget(self.folder)
        self.add=QPushButton('＋  Adicionar arquivos');self.add.clicked.connect(self.pick);controls.addWidget(self.add)
        self.clear=QPushButton('Limpar seleção');self.clear.clicked.connect(self.reset);controls.addWidget(self.clear)
        controls.addStretch()
        self.recursive=QCheckBox('Incluir subpastas');self.recursive.setChecked(True);controls.addWidget(self.recursive)
        self.online=QCheckBox('Consultar Crossref pela internet');self.online.setChecked(True);controls.addWidget(self.online)
        b.addLayout(controls)
        label=QLabel('PASTA SELECIONADA');label.setObjectName('muted');b.addWidget(label)
        self.info=QLabel('Nenhuma pasta ou arquivo selecionado');self.info.setObjectName('folderPath')
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        b.addWidget(self.info)
        self.runbtn=QPushButton('⌕   Analisar pasta / arquivos   ·   sem excluir')
        self.runbtn.setObjectName('primary');self.runbtn.clicked.connect(self.scan);b.addWidget(self.runbtn)
        prog=QHBoxLayout();self.bar=QProgressBar();self.bar.setTextVisible(False)
        prog.addWidget(self.bar,1)
        self.percent=QLabel('0%');self.percent.setObjectName('section');prog.addWidget(self.percent)
        b.addLayout(prog)
        resulthead=QHBoxLayout()
        section=QLabel('Resultados da análise');section.setObjectName('section');resulthead.addWidget(section)
        resulthead.addStretch()
        safe=QLabel('Nenhum arquivo será alterado ou excluído');safe.setObjectName('muted');resulthead.addWidget(safe)
        b.addLayout(resulthead)
        self.summary=QLabel('Aguardando análise.');self.summary.setObjectName('muted');b.addWidget(self.summary)
        headers=['Situação','Justificativa','Título','Autores (ABNT)','DOI','Ano','Periódico','Origem','Tipo','Confiança','Arquivo']
        self.table=QTableWidget(0,len(headers));self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setMinimumHeight(42)
        for col,width in {0:95,1:160,3:190,4:155,5:70,6:135,7:115,8:60,9:145,10:115}.items():
            self.table.setColumnWidth(col,width)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.open_file)
        b.addWidget(self.table,1)
        self.export=QPushButton('▤  Exportar relatório CSV');self.export.setObjectName('export')
        self.export.clicked.connect(self.save);self.export.setEnabled(False)
        b.addWidget(self.export)
        layout.addWidget(body,1)
        footer=QFrame();footer.setStyleSheet('QFrame{background:#fbfcfe;border-top:1px solid #dbe4f0;}')
        f=QHBoxLayout(footer);f.setContentsMargins(24,9,24,9)
        self.status=QLabel('●  Pronto');self.status.setObjectName('muted');f.addWidget(self.status)
        f.addStretch()
        credit=QLabel('Idealizador e proprietário: Wellington L. Constantino   |   Software desenvolvido em Python   |   v0.9.1')
        credit.setObjectName('credit');f.addWidget(credit)
        layout.addWidget(footer)
        self.paths=[];self.folder_path=None;self.records=[];self.matches=[];self.report=[];self.row_files=[]
    def pick_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Selecione a pasta a analisar')
        if path:self.folder_path=Path(path);self.info.setText(path)
    def pick(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Selecionar arquivos científicos','','Artigos e referências (*.csv *.ris *.bib *.pdf)')
        self.paths=list(dict.fromkeys(self.paths+paths))
        self.info.setText(f'{len(self.paths)} arquivo(s) adicional(is)'+(f' + pasta {self.folder_path}' if self.folder_path else ''))
    def reset(self):
        self.paths=[];self.folder_path=None;self.records=[];self.matches=[];self.report=[];self.row_files=[]
        self.info.setText('Nenhuma pasta ou arquivo selecionado');self.table.setRowCount(0)
        self.bar.setValue(0);self.percent.setText('0%');self.export.setEnabled(False)
        self.summary.setText('Aguardando análise.');self.status.setText('●  Pronto')
    def scan(self):
        paths=list(self.paths)
        if self.folder_path:
            try:
                it=self.folder_path.rglob('*') if self.recursive.isChecked() else self.folder_path.iterdir()
                paths.extend(str(p) for p in it if p.is_file() and p.suffix.lower() in EXTS)
            except OSError as e:
                QMessageBox.warning(self,'Erro',str(e));return
        paths=list(dict.fromkeys(paths))
        if not paths:
            QMessageBox.information(self,'Seleção','Selecione uma pasta com arquivos compatíveis ou adicione arquivos.');return
        self.folder.setEnabled(False);self.add.setEnabled(False);self.clear.setEnabled(False)
        self.runbtn.setEnabled(False);self.export.setEnabled(False);self.bar.setValue(0)
        self.percent.setText('0%');self.status.setText('●  Analisando arquivos...')
        self.worker=Worker(paths,self.online.isChecked())
        self.worker.progress.connect(self.update_progress);self.worker.completed.connect(self.done);self.worker.start()
    def update_progress(self,n,total,name):
        pct=round(n/max(total,1)*100);self.bar.setValue(pct);self.percent.setText(f'{pct}%')
        self.summary.setText(f'Processando {n}/{total}: {name}')
    def done(self,records,grouped,errors):
        self.records=records;self.matches=grouped;self.report=[];self.row_files=[];self.table.setRowCount(0);dup=0
        for group_id,ids in enumerate(grouped,1):
            best=max(ids,key=lambda i:(bool(records[i]['doi']),bool(records[i]['authors']),
                bool(records[i]['journal']),len(records[i]['title']),records[i]['kind']!='PDF'))
            for i in ids:
                r=records[i];status='Preservar' if i==best else 'Duplicata';dup+=i!=best
                row=self.table.rowCount();self.table.insertRow(row);self.row_files.append(r['file'])
                abnt=authors_abnt(r['authors'])
                vals=[status,r.get('duplicate_reason','Registro individual'),r['title'] or 'Não identificado',
                    abnt or 'Não identificado',r['doi'] or 'Não identificado',r['year'],
                    r['journal'],r['source'],r['kind'],r['confidence'],r['file']]
                for col,val in enumerate(vals):
                    item=QTableWidgetItem(str(val))
                    item.setToolTip(str(val))
                    if col==0:
                        item.setForeground(QColor('#08764d') if status=='Preservar' else QColor('#9b5810'))
                        font=item.font();font.setBold(True);item.setFont(font)
                    self.table.setItem(row,col,item)
                self.report.append({'grupo':group_id,'situacao':status,'autores_abnt':abnt,**r})
        self.summary.setText(f'{len(records)} registros  |  {len(grouped)} grupos  |  {dup} possíveis excedentes  |  {sum(len(x)>1 for x in grouped)} grupos duplicados — conferir antes de qualquer ação')
        self.folder.setEnabled(True);self.add.setEnabled(True);self.clear.setEnabled(True)
        self.runbtn.setEnabled(True);self.export.setEnabled(True);self.status.setText('●  Análise concluída')
        self.bar.setValue(100);self.percent.setText('100%')
        if errors:QMessageBox.warning(self,'Avisos','Alguns arquivos não foram lidos:\n'+'\n'.join(errors[:15]))
    def open_file(self,row,col):
        if row>=len(self.row_files):return
        path=Path(self.row_files[row])
        if not path.is_file():
            QMessageBox.warning(self,'Arquivo não encontrado',str(path));return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            QMessageBox.warning(self,'Falha','Não foi possível abrir o arquivo.')
    def save(self):
        p,_=QFileDialog.getSaveFileName(self,'Salvar relatório','relatorio_duplicatas.csv','CSV (*.csv)')
        if not p:return
        fields=['grupo','situacao','duplicate_reason','title','authors','autores_abnt','doi','year','journal','source','file','kind','confidence','hash']
        with open(p,'w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',delimiter=';')
            writer.writeheader();writer.writerows(self.report)
        QMessageBox.information(self,'Concluído','Relatório salvo. Nenhum arquivo original foi alterado.')
if __name__=='__main__':
    app=QApplication(sys.argv);window=Main();window.show();sys.exit(app.exec())
