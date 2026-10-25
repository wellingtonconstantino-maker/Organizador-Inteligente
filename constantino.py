"""Constantino Software — interface unificada e identificação inequívoca do módulo."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QMainWindow,QTabWidget
from modulo_geral import Main as Geral,quarantine_root
from modulo_cientifico import Main as Cientifico

class Constantino(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1480,900)
        self.tabs=QTabWidget(self)
        self.tabs.setDocumentMode(False)
        self.tabs.setStyleSheet('''
        QTabWidget::pane {border:0;border-top:3px solid #1a65b9;}
        QTabBar::tab {background:#e6ebf3;color:#435a74;padding:14px 34px;
          font:700 15px 'Segoe UI';border:1px solid #c7d5e8;margin-right:5px;min-width:175px;}
        QTabBar::tab:selected {background:#155db5;color:white;border:2px solid #0e4a93;}
        QTabBar::tab:hover:!selected {background:#d0e2f8;color:#163e6e;}
        ''')
        self.geral=Geral();self.cientifico=Cientifico()
        for w in (self.geral,self.cientifico):w.setWindowFlags(Qt.Widget)
        self.tabs.addTab(self.geral,'  MÓDULO GERAL  ')
        self.tabs.addTab(self.cientifico,'  MÓDULO CIENTÍFICO  ')
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.update_title)
        self.update_title(0)
    def update_title(self,index):
        self.setWindowTitle('Constantino Software | '+('MÓDULO GERAL — Arquivos e fotografias' if index==0 else 'MÓDULO CIENTÍFICO — Artigos e referências')+' | v0.10.0 beta')

if __name__=='__main__':
    app=QApplication(sys.argv)
    quarantine_root()
    window=Constantino();window.show()
    sys.exit(app.exec())
