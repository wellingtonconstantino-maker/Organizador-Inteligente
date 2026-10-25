"""Constantino Software - Organizador Geral v0.9.1 (layout corrigido e quarentena em lote)."""
import csv
import hashlib
import os
import sys
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
 QVBoxLayout, QHBoxLayout, QFileDialog, QCheckBox, QProgressBar, QTableWidget,
 QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QMessageBox, QGridLayout, QDialog, QDialogButtonBox, QAbstractItemView)

EXTENSIONS = {
 'Músicas': {'.mp3','.wav','.wave','.flac','.ogg','.oga','.opus','.aac','.m4a','.wma','.aiff','.aif'},
 'Fotografias': {'.jpg','.jpeg','.png','.heic','.heif','.tif','.tiff','.webp','.bmp','.gif','.dng','.cr2','.nef','.arw','.raw'},
 'Vídeos': {'.mp4','.mkv','.avi','.mov','.wmv','.webm','.mpeg','.mpg','.m4v','.flv'},
 'HQs': {'.cbr','.cbz','.cb7','.cbt'},
 'Documentos': {'.pdf','.doc','.docx','.txt','.odt','.rtf','.epub','.xls','.xlsx','.ppt','.pptx'},
 'Compactados': {'.zip','.rar','.7z','.tar','.gz','.bz2','.xz'}
}
def category(path):
    ext=path.suffix.lower()
    for name,extensions in EXTENSIONS.items():
        if ext in extensions:return name
    return 'Outros'
def human(n):
    for unit in ('B','KB','MB','GB','TB'):
        if n<1024 or unit=='TB':return f'{n:.1f} {unit}' if unit!='B' else f'{int(n)} B'
        n/=1024

def quarantine_root():
    """Persistent writable quarantine, separate from installed program files."""
    root=(Path(os.environ['LOCALAPPDATA']) / 'Constantino Software' if sys.platform == 'win32' and os.environ.get('LOCALAPPDATA') else Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local'/'share'))) / 'constantino-software') / 'Quarentena_Constantino'
    root.mkdir(parents=True,exist_ok=True)
    return root

def safe_move(src,dst,expected):
    """Move com validação de conteúdo inclusive entre unidades."""
    if src.stat().st_dev == dst.parent.stat().st_dev:
        src.rename(dst)
    else:
        temp=dst.with_name(dst.name+".parcial")
        try:
            shutil.copy2(src,temp)
            if digest(temp)!=expected:raise ValueError("falha de integridade durante cópia")
            temp.replace(dst)
            src.unlink()
        finally:
            if temp.exists():temp.unlink()

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

class Scanner(QThread):
    progress=Signal(int,int,str)
    completed=Signal(object,object,object)
    def __init__(self,folder,recursive):super().__init__();self.folder=Path(folder);self.recursive=recursive
    def run(self):
        files=[];errors=[]
        try:
            if self.recursive:
                for root,dirs,names in os.walk(self.folder,followlinks=False):
                    dirs[:]=[d for d in dirs if d not in ('.constantino_quarentena','Quarentena_Constantino') and not (Path(root)/d).is_symlink()]
                    for name in names:
                        p=Path(root)/name
                        if not p.is_symlink():files.append(p)
            else:
                files=[p for p in self.folder.iterdir() if p.is_file() and not p.is_symlink()]
        except OSError as e:errors.append(str(e))
        rows=[];by_size=defaultdict(list)
        for i,p in enumerate(files,1):
            try:
                size=p.stat().st_size
                r={'path':str(p),'name':p.name,'category':category(p),'ext':p.suffix.lower() or '(sem extensão)',
                   'size':size,'status':'Sem duplicata identificada','group':'','sha256':''}
                by_size[size].append(len(rows));rows.append(r)
            except OSError as e:errors.append(f'{p}: {e}')
            self.progress.emit(i,max(1,len(files)),p.name)
        candidates=[(size,ids) for size,ids in by_size.items() if len(ids)>1]
        total=sum(len(ids) for _,ids in candidates);processed=0;groups=0
        for size,ids in candidates:
            hashes=defaultdict(list)
            for idx in ids:
                try:
                    h=digest(rows[idx]['path']);rows[idx]['sha256']=h;hashes[h].append(idx)
                except OSError as e:errors.append(f"{rows[idx]['path']}: {e}")
                processed+=1;self.progress.emit(processed,max(1,total),'Comparando arquivos de mesmo tamanho')
            for ids2 in hashes.values():
                if len(ids2)>1:
                    groups+=1
                    for j,idx in enumerate(sorted(ids2,key=lambda x:rows[x]['path'].casefold())):
                        rows[idx]['status']='Preservar' if j==0 else 'Duplicata'
                        rows[idx]['group']=str(groups)
        self.completed.emit(rows,errors,groups)

STYLE='''
QMainWindow {background:#f1f4f9;} QWidget {font-family:'Segoe UI',Arial;font-size:12px;color:#18304f;}
QFrame#hero {background:#fcfdff;border-bottom:1px solid #dce5f1;}
QLabel#brand {color:#12396d;font-size:18px;font-weight:800;letter-spacing:2px;}
QLabel#heading {color:#102c55;font-size:25px;font-weight:800;}
QLabel#muted {color:#62738c;font-size:11px;}
QLabel#cardNum {font-size:21px;font-weight:800;color:#154d89;}
QLabel#cardName {font-size:12px;font-weight:700;color:#294a70;}
QFrame#tile {background:white;border:1px solid #d9e3f0;border-radius:10px;}
QPushButton {background:white;border:1px solid #c9d7e9;border-radius:7px;padding:10px 16px;font-weight:600;}
QPushButton:hover {background:#eaf3ff;} QPushButton:disabled {color:#a0adbe;}
QPushButton#primary {background:#1667c6;color:white;border-color:#1667c6;font-weight:800;font-size:14px;padding:13px;}
QPushButton#export {background:#e7f6ee;color:#087448;border:1px solid #a4d8bd;}
QPushButton#review {background:#fff1e6;color:#9b3c14;border:1px solid #f1c2a2;font-weight:800;}
QPushButton#review:disabled {background:#f6f6f6;color:#a0adbe;}
QLineEdit,QComboBox {background:white;border:1px solid #c9d7e9;border-radius:6px;padding:8px;}
QProgressBar {background:#dce6f3;border:0;border-radius:4px;height:9px;}
QProgressBar::chunk {background:#1680c9;border-radius:4px;}
QTableWidget {background:white;alternate-background-color:#f6f9fd;gridline-color:#e5ebf3;border:1px solid #dce5f1;}
QHeaderView::section {background:#e8f1fb;color:#143b6d;font-weight:800;border:0;border-right:1px solid #d4e0ee;border-bottom:2px solid #9bbde1;padding:7px 6px;}
'''
class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('Organizador Inteligente — Módulo Geral v0.9.1 | Constantino Software')
        self.resize(1450,850);self.setStyleSheet(STYLE);self.folder=None;self.rows=[];self.errors=[];self.visible=[]
        center=QWidget();self.setCentralWidget(center);layout=QVBoxLayout(center);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        hero=QFrame();hero.setObjectName('hero');hl=QHBoxLayout(hero);hl.setContentsMargins(22,5,22,5);hl.setSpacing(14)
        # Símbolo isolado + texto real (não depende de imagem com texto cortado).
        brand=QWidget();brand.setFixedWidth(365)
        brandrow=QHBoxLayout(brand);brandrow.setContentsMargins(0,0,0,0);brandrow.setSpacing(8)
        logo=QLabel();logo.setFixedSize(116,98)
        image=Path(getattr(sys,'_MEIPASS',Path(__file__).parent)) / 'constantino_emblema.png'
        if image.exists():
            pix=QPixmap(str(image))
            logo.setPixmap(pix.scaled(116,98,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brandrow.addWidget(logo)
        brandtext=QLabel('Constantino\nSoftware')
        brandtext.setStyleSheet('color:#12396d;font-size:25px;font-weight:800;')
        brandtext.setMinimumWidth(225)
        brandrow.addWidget(brandtext,1)
        hl.addWidget(brand)
        sep=QFrame();sep.setFrameShape(QFrame.Shape.VLine);hl.addWidget(sep)
        titles=QVBoxLayout();titles.setSpacing(1);title_row=QHBoxLayout();title_row.setSpacing(11);name=QLabel('Organizador Inteligente');name.setObjectName('heading');title_row.addWidget(name);
        for kind,tip in [('musica','Música'),('hq','HQ'),('foto','Foto'),('pdf','PDF'),('cd','CD')]:
            icon=QLabel();icon.setFixedSize(28,28);icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            file=Path(getattr(sys,'_MEIPASS',Path(__file__).parent)) / 'icones' / (kind+'.png')
            if file.exists():icon.setPixmap(QPixmap(str(file)).scaled(27,27,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            icon.setToolTip(tip+' (decorativo)');title_row.addWidget(icon)
        title_row.addStretch();titles.addLayout(title_row)
        desc=QLabel('Módulo Geral  •  Arquivos e duplicatas');desc.setObjectName('muted');titles.addWidget(desc)
        hl.addLayout(titles,1);layout.addWidget(hero)
        body=QWidget();b=QVBoxLayout(body);b.setContentsMargins(30,9,30,7);b.setSpacing(6)
        controls=QHBoxLayout();controls.setSpacing(9)
        self.choose=QPushButton('Selecionar pasta / HD');self.choose.clicked.connect(self.select_folder);controls.addWidget(self.choose)
        self.clearbtn=QPushButton('Limpar pesquisa');self.clearbtn.setToolTip('Limpar resultados e seleção sem apagar arquivos');self.clearbtn.clicked.connect(self.clear_search);controls.addWidget(self.clearbtn)
        self.recursive=QCheckBox('Incluir subpastas');self.recursive.setChecked(True);controls.addWidget(self.recursive)
        self.pathlabel=QLineEdit();self.pathlabel.setReadOnly(True);self.pathlabel.setPlaceholderText('Nenhuma pasta selecionada')
        self.pathlabel.setMinimumWidth(180);controls.addWidget(self.pathlabel,1)
        self.scanbtn=QPushButton('Analisar arquivos e identificar duplicatas');self.scanbtn.setObjectName('primary');self.scanbtn.clicked.connect(self.scan);controls.addWidget(self.scanbtn)
        b.addLayout(controls)
        extras=QHBoxLayout()
        self.deepbtn=QPushButton('Pesquisa profunda (fotos, PDF e CBZ)');self.deepbtn.clicked.connect(self.deep_scan);extras.addWidget(self.deepbtn)
        self.photosbtn=QPushButton('Organizar fotografias por ano');self.photosbtn.clicked.connect(self.organize_photos);extras.addWidget(self.photosbtn)
        self.undobtn=QPushButton('Desfazer organização das fotos');self.undobtn.clicked.connect(self.undo_photos);extras.addWidget(self.undobtn)
        b.addLayout(extras)
        pr=QHBoxLayout();self.bar=QProgressBar();self.bar.setTextVisible(False);pr.addWidget(self.bar,1);self.percent=QLabel('0%');pr.addWidget(self.percent);b.addLayout(pr)
        metrics=QHBoxLayout();self.metrics={}
        for key in ('Arquivos identificados','Categorias','Duplicatas excedentes','Espaço recuperável'):
            frame=QFrame();frame.setObjectName('tile');frame.setFixedHeight(59);v=QVBoxLayout(frame);v.setContentsMargins(12,5,12,5);v.setSpacing(0);lab=QLabel(key);lab.setObjectName('cardName');v.addWidget(lab)
            num=QLabel('—');num.setObjectName('cardNum');v.addWidget(num);metrics.addWidget(frame,1);self.metrics[key]=num
        b.addLayout(metrics)
        # Resumo por categoria removido da tela para priorizar a tabela.
        self.categoryline=QLabel();self.categoryline.hide()
        filt=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Pesquisar nos resultados: nome, extensão ou caminho...');self.search.textChanged.connect(self.filter);filt.addWidget(self.search,1)
        self.categoryfilter=QComboBox();self.categoryfilter.addItem('Todas as categorias');self.categoryfilter.currentTextChanged.connect(self.filter);filt.addWidget(self.categoryfilter)
        self.statusfilter=QComboBox();self.statusfilter.addItems(['Todos os arquivos','Duplicatas','Preservar','Sem duplicata identificada']);self.statusfilter.currentTextChanged.connect(self.filter);filt.addWidget(self.statusfilter)
        self.extensionsbtn=QPushButton('Extensões: 0 tipos');self.extensionsbtn.setToolTip('Ver quantidade de PDFs, CBRs, MP3s, JPGs e todas as demais extensões');self.extensionsbtn.setEnabled(False);self.extensionsbtn.clicked.connect(self.show_extensions);filt.addWidget(self.extensionsbtn)
        b.addLayout(filt)
        headers=['Situação','Categoria','Extensão','Nome do arquivo','Tamanho','Grupo','Caminho completo']
        self.table=QTableWidget(0,len(headers));self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        for col,width in {0:165,1:120,2:90,4:105,5:65,6:330}.items():self.table.setColumnWidth(col,width)
        self.table.verticalHeader().setDefaultSectionSize(27);self.table.setMinimumHeight(390);self.table.cellDoubleClicked.connect(self.open_file)
        b.addWidget(self.table,1)
        self.summary=QLabel('');self.summary.hide()
        actions=QHBoxLayout()
        self.export=QPushButton('▤  Exportar relatório CSV');self.export.setObjectName('export');self.export.setEnabled(False);self.export.clicked.connect(self.save);actions.addWidget(self.export,1)
        self.review=QPushButton('Enviar duplicatas à quarentena (em lote)');self.review.setObjectName('review');self.review.setEnabled(False);self.review.clicked.connect(self.batch_quarantine);actions.addWidget(self.review,1)
        self.restorebtn=QPushButton('Restaurar da quarentena');self.restorebtn.clicked.connect(self.restore_quarantine);actions.addWidget(self.restorebtn,1)
        self.openquarantine=QPushButton('Abrir quarentena');self.openquarantine.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(quarantine_root()))));actions.addWidget(self.openquarantine)
        b.addLayout(actions)
        layout.addWidget(body,1)
        footer=QFrame();footer.setStyleSheet('background:#fbfcfe;border-top:1px solid #dce5f1;');fl=QHBoxLayout(footer);fl.setContentsMargins(24,8,24,8)
        self.status=QLabel('●  Pronto');fl.addWidget(self.status);fl.addStretch()
        credit=QLabel('Idealizador e proprietário: Wellington L. Constantino   |   Software desenvolvido em Python   |   v0.9.1')
        credit.setAlignment(Qt.AlignmentFlag.AlignRight);credit.setObjectName('muted');fl.addWidget(credit);layout.addWidget(footer)
    def clear_search(self):
        if getattr(self,'worker',None) is not None and self.worker.isRunning():
            QMessageBox.information(self,'Aguarde','A análise ainda está em andamento.');return
        if getattr(self,'deepworker',None) is not None and self.deepworker.isRunning():
            QMessageBox.information(self,'Aguarde','A pesquisa profunda ainda está em andamento.');return
        self.reset_results();self.folder=None;self.pathlabel.clear()

    def deep_scan(self):
        if not self.folder:
            QMessageBox.information(self,'Pasta','Selecione uma pasta primeiro.');return
        from analise_profunda import DeepWorker
        self.deepbtn.setEnabled(False)
        self.status.setText('● Pesquisa profunda em andamento...')
        self.deepworker=DeepWorker(self.folder)
        self.deepworker.progress.connect(lambda n,t:(self.bar.setValue(round(100*n/max(t,1))),self.percent.setText(f'{round(100*n/max(t,1))}%')))
        self.deepworker.completed.connect(self.deep_done)
        self.deepworker.start()

    def deep_done(self,results,errors):
        self.deepbtn.setEnabled(True)
        self.status.setText(f'● Pesquisa profunda: {len(results)} pares para revisão; {len(errors)} erros')
        dlg=QDialog(self);dlg.setWindowTitle('Pesquisa profunda — candidatos, sem exclusão');dlg.resize(1100,650)
        lay=QVBoxLayout(dlg)
        lay.addWidget(QLabel(f'{len(results)} pares potencialmente equivalentes. Nenhum arquivo será movido ou excluído.'))
        table=QTableWidget(len(results),4);table.setHorizontalHeaderLabels(['Classificação','Arquivo 1','Arquivo 2','Evidência'])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for i,row in enumerate(results):
            for j,val in enumerate(row):table.setItem(i,j,QTableWidgetItem(str(val)))
        lay.addWidget(table)
        export=QPushButton('Exportar candidatos CSV')
        def save_deep():
            path,_=QFileDialog.getSaveFileName(dlg,'Salvar relatório','pesquisa_profunda.csv','CSV (*.csv)')
            if path:
                with open(path,'w',newline='',encoding='utf-8-sig') as out:
                    w=csv.writer(out,delimiter=';');w.writerow(['classificacao','arquivo1','arquivo2','evidencia']);w.writerows(results)
        export.clicked.connect(save_deep);lay.addWidget(export)
        if errors:lay.addWidget(QLabel(f'{len(errors)} arquivos não puderam ser examinados.'))
        dlg.exec()

    def organize_photos(self):
        if not self.folder:
            QMessageBox.information(self,'Pasta','Selecione uma pasta primeiro.');return
        from organizar_fotos import plan,execute
        try:rows=plan(self.folder)
        except OSError as e:QMessageBox.warning(self,'Erro',str(e));return
        if not rows:QMessageBox.information(self,'Fotografias','Nenhuma fotografia encontrada.');return
        from collections import Counter
        counts=Counter(dst.parent.name for _,dst,_ in rows)
        approx=sum(source!='EXIF' for _,_,source in rows)
        detail='\n'.join(f'{y}: {n} foto(s)' for y,n in sorted(counts.items()))
        answer=QMessageBox.question(self,'Prévia — organização de fotografias',
            f'{len(rows)} fotografias serão MOVIDAS para Fotografias organizadas/ANO.\n'
            f'{approx} usarão a data de modificação (não EXIF).\n\n{detail}\n\n'
            'As pastas de músicas e HQs não serão alteradas. Confirmar?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        manifest,done,errors=execute(self.folder,rows)
        self.reset_results()
        QMessageBox.information(self,'Organização concluída',f'{len(done)} fotografias movidas; {len(errors)} falhas.\nManifesto: {manifest}\nUse Desfazer organização para restaurar.')

    def undo_photos(self):
        from organizar_fotos import undo
        path,_=QFileDialog.getOpenFileName(self,'Escolher manifesto de organização',self.folder or str(Path.home()),'Manifesto CSV (manifesto_organizacao_*.csv)')
        if not path:return
        if QMessageBox.question(self,'Desfazer organização','Restaurar fotografias aos caminhos originais?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        try:done,errors=undo(path)
        except Exception as e:QMessageBox.warning(self,'Erro',str(e));return
        self.reset_results();QMessageBox.information(self,'Restauração',f'{len(done)} fotografias restauradas; {len(errors)} falhas.')

    def reset_results(self):
        # Limpa somente os resultados da consulta anterior; não altera arquivos nem quarentena.
        self.rows=[]
        self.errors=[]
        self.visible=[]
        self.extension_counts=Counter()
        self.table.setRowCount(0)
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.categoryfilter.blockSignals(True)
        self.categoryfilter.clear()
        self.categoryfilter.addItem('Todas as categorias')
        self.categoryfilter.blockSignals(False)
        self.statusfilter.blockSignals(True)
        self.statusfilter.setCurrentIndex(0)
        self.statusfilter.blockSignals(False)
        for metric in self.metrics.values():
            metric.setText('—')
        self.bar.setValue(0)
        self.percent.setText('0%')
        self.extensionsbtn.setText('Extensões: 0 tipos')
        self.extensionsbtn.setEnabled(False)
        self.export.setEnabled(False)
        self.review.setEnabled(False)
        self.categoryline.clear()
        self.summary.clear()
        self.status.setText('●  Pronto para nova análise')

    def select_folder(self):
        path=QFileDialog.getExistingDirectory(self,'Selecione uma pasta ou unidade')
        if path:
            self.reset_results()
            self.folder=path
            self.pathlabel.setText(path)
    def scan(self):
        if not self.folder:QMessageBox.information(self,'Pasta','Selecione primeiro uma pasta ou HD.');return
        self.scanbtn.setEnabled(False);self.choose.setEnabled(False);self.export.setEnabled(False);self.review.setEnabled(False)
        self.status.setText('●  Analisando...');self.worker=Scanner(self.folder,self.recursive.isChecked())
        self.worker.progress.connect(self.update);self.worker.completed.connect(self.done);self.worker.start()
    def update(self,n,total,name):
        pct=round(100*n/max(total,1));self.bar.setValue(pct);self.percent.setText(f'{pct}%');self.summary.setText(f'Processando {n}/{total}: {name}')
    def done(self,rows,errors,groups):
        self.rows=rows;self.errors=errors;self.scanbtn.setEnabled(True);self.choose.setEnabled(True);self.export.setEnabled(True)
        copies=[r for r in rows if r['status']=='Duplicata'];cats=Counter(r['category'] for r in rows)
        self.metrics['Arquivos identificados'].setText(str(len(rows)));self.metrics['Categorias'].setText(str(len(cats)))
        self.metrics['Duplicatas excedentes'].setText(str(len(copies)))
        self.metrics['Espaço recuperável'].setText(human(sum(r['size'] for r in copies)))
        self.extension_counts=Counter(r['ext'].upper().lstrip('.') if r['ext']!='(sem extensão)' else '(SEM EXTENSÃO)' for r in rows)
        self.extensionsbtn.setText(f'Extensões: {len(self.extension_counts)} tipos');self.extensionsbtn.setEnabled(True)
        parts=[]
        for cat,n in sorted(cats.items(),key=lambda x:-x[1]):
            ext=Counter(r['ext'].upper().lstrip('.') for r in rows if r['category']==cat)
            parts.append(f"{cat} ({n}): "+'  ·  '.join(f'{e}: {v}' for e,v in ext.most_common(9)))
        self.categoryline.setText('\n'.join(parts) if parts else 'Nenhum arquivo encontrado.')
        self.categoryfilter.blockSignals(True);self.categoryfilter.clear();self.categoryfilter.addItem('Todas as categorias')
        self.categoryfilter.addItems(sorted(cats));self.categoryfilter.blockSignals(False)
        self.filter();self.bar.setValue(100);self.percent.setText('100%')
        self.summary.setText(f'{len(rows)} arquivos  |  {groups} grupos de duplicatas  |  {len(copies)} duplicatas excedentes  |  {len(errors)} erros de leitura')
        self.status.setText('●  Análise concluída');self.review.setEnabled(bool(copies))
        if errors:QMessageBox.warning(self,'Avisos',f'{len(errors)} arquivo(s) não puderam ser lidos. O relatório CSV inclui os erros em arquivo separado.')
    def show_extensions(self):
        counts=getattr(self,'extension_counts',Counter())
        dlg=QDialog(self);dlg.setWindowTitle('Arquivos por extensão — contagem completa');dlg.resize(470,570)
        layout=QVBoxLayout(dlg)
        layout.addWidget(QLabel(f'{sum(counts.values())} arquivos classificados em {len(counts)} tipos de extensão.'))
        table=QTableWidget(len(counts),2);table.setHorizontalHeaderLabels(['Extensão','Quantidade'])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(1,135)
        for i,(ext,n) in enumerate(sorted(counts.items(),key=lambda x:(-x[1],x[0]))):
            table.setItem(i,0,QTableWidgetItem(ext));table.setItem(i,1,QTableWidgetItem(str(n)))
        layout.addWidget(table)
        close=QPushButton('Fechar');close.clicked.connect(dlg.accept);layout.addWidget(close)
        dlg.exec()

    def filter(self,*args):
        search=self.search.text().casefold().strip();cat=self.categoryfilter.currentText();status=self.statusfilter.currentText()
        visible=[r for r in self.rows if (cat=='Todas as categorias' or r['category']==cat) and
            (status=='Todos os arquivos' or r['status']==status) and
            (not search or search in (r['name']+' '+r['ext']+' '+r['path']).casefold())]
        self.table.setRowCount(len(visible));self.visible=visible
        for i,r in enumerate(visible):
            values=[r['status'],r['category'],r['ext'],r['name'],human(r['size']),r['group'],r['path']]
            for j,val in enumerate(values):
                item=QTableWidgetItem(str(val));item.setToolTip(str(val))
                if j==0:
                    f=item.font();f.setBold(True);item.setFont(f)
                    item.setForeground(QColor('#a35a0d') if val=='Duplicata' else QColor('#087448'))
                self.table.setItem(i,j,item)
    def open_file(self,row,col):
        if row>=len(self.visible):return
        p=Path(self.visible[row]['path'])
        if p.exists():QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
    def batch_quarantine(self):
        copies=[r for r in self.rows if r['status']=='Duplicata']
        if not copies:return
        answer=QMessageBox.question(self,'Quarentena automática',
            f'Foram identificadas {len(copies)} duplicatas digitais comprovadas, totalizando {human(sum(r["size"] for r in copies))}.\n\n'
            'O programa verificará novamente o SHA-256 de cada cópia e do original preservado.\n'
            'Somente cópias comprovadas serão movidas para a quarentena.\n\n'
            'Deseja executar a operação em lote?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        groups=defaultdict(list)
        for r in self.rows:
            if r['group']:groups[r['group']].append(r)
        valid=[];failures=[]
        for r in copies:
            keepers=[x for x in groups[r['group']] if x['status']=='Preservar']
            try:
                if len(keepers)!=1:raise ValueError('original não localizado')
                keep=keepers[0]
                if Path(r['path']).is_symlink() or Path(keep['path']).is_symlink():raise ValueError('link simbólico')
                if Path(r['path']).resolve()==Path(keep['path']).resolve():raise ValueError('mesmo caminho')
                if Path(r['path']).stat().st_size!=r['size'] or Path(keep['path']).stat().st_size!=r['size']:
                    raise ValueError('tamanho alterado')
                if digest(r['path'])!=r['sha256'] or digest(keep['path'])!=r['sha256']:
                    raise ValueError('hash diferente')
                valid.append(r)
            except (OSError,ValueError) as e:failures.append(f'{r["path"]}: {e}')
        if not valid:
            QMessageBox.warning(self,'Nenhuma cópia movida','A validação não confirmou cópias seguras.');return
        base=quarantine_root()
        quarantine=base/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
        try:quarantine.mkdir(parents=True,exist_ok=False)
        except OSError as e:QMessageBox.warning(self,'Erro',str(e));return
        manifest=quarantine/'manifesto.csv';moved=[]
        for r in valid:
            src=Path(r['path']);dst=quarantine/(uuid.uuid4().hex+'_'+src.name)
            try:
                # Grava o registro antes de mover, para permitir recuperação após interrupções.
                entry={'original':str(src),'quarentena':str(dst),'sha256':r['sha256'],
                       'tamanho':r['size'],'grupo':r['group']}
                with manifest.open('a',newline='',encoding='utf-8-sig' if not manifest.exists() else 'utf-8') as f:
                    writer=csv.DictWriter(f,fieldnames=list(entry),delimiter=';')
                    if f.tell()==0:writer.writeheader()
                    writer.writerow(entry);f.flush();os.fsync(f.fileno())
                # Entre unidades, copia e verifica SHA-256 antes de retirar a origem.
                safe_move(src,dst,r["sha256"])
                moved.append(entry)
            except OSError as e:failures.append(f'{src}: {e}')
        self.review.setEnabled(False)
        self.summary.setText('Quarentena concluída. Execute nova análise para atualizar os resultados.')
        QMessageBox.information(self,'Resultado da quarentena',
            f'{len(moved)} cópias movidas; {len(failures)} falhas.\n\nManifesto: {manifest}\n\n'
            'Os arquivos continuam ocupando espaço até exclusão definitiva.')

    def restore_quarantine(self):
        manifest_name,_=QFileDialog.getOpenFileName(self,'Selecionar manifesto da quarentena',
            str(quarantine_root()), 'Manifesto CSV (manifesto.csv)')
        if not manifest_name:return
        manifest=Path(manifest_name)
        if manifest.name!='manifesto.csv':
            QMessageBox.warning(self,'Manifesto','Selecione um arquivo chamado manifesto.csv.');return
        try:
            with manifest.open('r',encoding='utf-8-sig',newline='') as f:
                entries=list(csv.DictReader(f,delimiter=';'))
        except (OSError,csv.Error) as e:QMessageBox.warning(self,'Erro',str(e));return
        candidates=[];skipped=[]
        for r in entries:
            try:
                src=Path(r['quarentena']);dst=Path(r['original'])
                if src.parent.resolve()!=manifest.parent.resolve():raise ValueError('arquivo fora da quarentena')
                if not src.is_file() or src.is_symlink():raise ValueError('arquivo indisponível')
                if dst.exists():raise ValueError('destino já existe; não sobrescrever')
                if digest(src)!=r['sha256']:raise ValueError('hash diferente')
                candidates.append((src,dst))
            except (OSError,KeyError,ValueError) as e:skipped.append(str(e))
        if not candidates:
            QMessageBox.information(self,'Restauração','Nenhum arquivo elegível para restaurar.');return
        if QMessageBox.question(self,'Confirmar restauração',
            f'Restaurar {len(candidates)} arquivo(s) aos caminhos originais?\n'
            f'{len(skipped)} item(ns) serão ignorados por segurança.',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        restored=0
        for src,dst in candidates:
            try:
                dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists():raise FileExistsError(str(dst))
                safe_move(src,dst,digest(src));restored+=1
            except OSError as e:skipped.append(str(e))
        QMessageBox.information(self,'Restauração',f'{restored} arquivo(s) restaurado(s); {len(skipped)} ignorado(s).\nO manifesto foi preservado.')

    def review_duplicates(self):
        copies=[r for r in self.rows if r['status']=='Duplicata']
        if not copies:return
        dlg=QDialog(self);dlg.setWindowTitle('Revisar duplicatas — nenhuma exclusão definitiva');dlg.resize(1060,650)
        v=QVBoxLayout(dlg)
        intro=QLabel(f'{len(copies)} duplicatas identificadas ({human(sum(r["size"] for r in copies))}).\n'
                     'Selecione as cópias que deseja mover para uma pasta de quarentena. O arquivo preservado nunca será selecionado.\n'
                     'A quarentena não é exclusão definitiva; o relatório permite restaurar manualmente os arquivos.')
        intro.setWordWrap(True);v.addWidget(intro)
        table=QTableWidget(len(copies),5);table.setHorizontalHeaderLabels(['Mover?','Nome','Tamanho','Grupo','Caminho original'])
        table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch)
        for col,width in {0:80,1:250,2:90,3:70}.items():table.setColumnWidth(col,width)
        for i,r in enumerate(copies):
            check=QTableWidgetItem('');check.setFlags(Qt.ItemFlag.ItemIsUserCheckable|Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(Qt.CheckState.Unchecked);table.setItem(i,0,check)
            for j,value in enumerate([r['name'],human(r['size']),r['group'],r['path']],1):
                item=QTableWidgetItem(str(value));item.setToolTip(str(value));table.setItem(i,j,item)
        v.addWidget(table)
        row=QHBoxLayout();allbtn=QPushButton('Marcar todas as cópias');nonebtn=QPushButton('Desmarcar todas')
        allbtn.clicked.connect(lambda:[table.item(i,0).setCheckState(Qt.CheckState.Checked) for i in range(len(copies))])
        nonebtn.clicked.connect(lambda:[table.item(i,0).setCheckState(Qt.CheckState.Unchecked) for i in range(len(copies))])
        row.addWidget(allbtn);row.addWidget(nonebtn);row.addStretch();v.addLayout(row)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Mover selecionadas para quarentena')
        buttons.accepted.connect(dlg.accept);buttons.rejected.connect(dlg.reject);v.addWidget(buttons)
        if dlg.exec()!=QDialog.DialogCode.Accepted:return
        selected=[r for i,r in enumerate(copies) if table.item(i,0).checkState()==Qt.CheckState.Checked]
        if not selected:
            QMessageBox.information(self,'Nenhuma seleção','Nenhuma cópia foi selecionada.');return
        if QMessageBox.question(self,'Confirmar movimentação',
            f'Mover {len(selected)} duplicatas ({human(sum(r["size"] for r in selected))}) para quarentena?\n\n'
            'Os arquivos preservados não serão movidos. A operação será registrada em relatório.',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        # Revalidar os hashes antes de movimentar. Não confiar apenas na análise anterior.
        by_group=defaultdict(list)
        for r in self.rows:
            if r['group']:by_group[r['group']].append(r)
        valid=[];failed=[]
        for r in selected:
            originals=[x for x in by_group[r['group']] if x['status']=='Preservar']
            try:
                if len(originals)!=1:raise ValueError('original preservado não encontrado')
                keep=originals[0]
                if not Path(keep['path']).is_file() or not Path(r['path']).is_file():raise ValueError('arquivo ausente')
                if digest(keep['path'])!=r['sha256'] or digest(r['path'])!=r['sha256']:
                    raise ValueError('conteúdo mudou desde a análise')
                valid.append(r)
            except (OSError,ValueError) as e:failed.append(f'{r["path"]}: {e}')
        if not valid:
            QMessageBox.warning(self,'Nada movido','Não foi possível validar as cópias. Faça uma nova análise.');return
        quarantine=Path(self.folder)/'.constantino_quarentena'/datetime.now().strftime('%Y%m%d_%H%M%S')
        quarantine.mkdir(parents=True,exist_ok=True)
        logpath=quarantine/'manifesto.csv';moved=[]
        for r in valid:
            try:
                src=Path(r['path']);dest=quarantine/(uuid.uuid4().hex+'_'+src.name)
                # Quarentena na mesma unidade, evitando cópia entre discos.
                src.rename(dest)
                moved.append({'original':str(src),'quarentena':str(dest),'sha256':r['sha256'],
                              'tamanho':r['size'],'grupo':r['group']})
            except OSError as e:failed.append(f'{r["path"]}: {e}')
        with logpath.open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=['original','quarentena','sha256','tamanho','grupo'],delimiter=';')
            writer.writeheader();writer.writerows(moved)
        QMessageBox.information(self,'Quarentena concluída',
            f'{len(moved)} arquivo(s) movido(s) para quarentena.\nFalhas: {len(failed)}.\n\nManifesto: {logpath}\n\n'
            'Nenhum arquivo foi excluído definitivamente. Faça nova análise para atualizar a tabela.')
        self.review.setEnabled(False)
        self.summary.setText('Arquivos enviados para quarentena. Execute nova análise para atualizar os resultados.')
    def save(self):
        path,_=QFileDialog.getSaveFileName(self,'Salvar relatório','relatorio_organizador_geral.csv','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.DictWriter(f,fieldnames=['status','category','ext','name','size','group','sha256','path'],delimiter=';')
                w.writeheader();w.writerows(self.rows)
            if self.errors:
                with open(str(Path(path).with_name(Path(path).stem+'_erros.csv')),'w',newline='',encoding='utf-8-sig') as f:
                    w=csv.writer(f,delimiter=';');w.writerow(['erro']);w.writerows([[e] for e in self.errors])
            QMessageBox.information(self,'Concluído','Relatório exportado. Nenhum arquivo foi modificado.')
        except OSError as e:QMessageBox.warning(self,'Erro ao salvar',str(e))
if __name__=='__main__':
    app=QApplication(sys.argv);quarantine_root();window=Main();window.show();sys.exit(app.exec())
