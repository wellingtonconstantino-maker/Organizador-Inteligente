"""Constantino Software - interface unificada, navegacao de modulos destacada."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QLabel, QWidget, QHBoxLayout, QVBoxLayout
from modulo_geral import Main as Geral, quarantine_root
from modulo_cientifico import Main as Cientifico

class Constantino(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1480, 900)
        self.setMinimumSize(1020, 650)
        self.setWindowTitle('Constantino Software | Organizador Inteligente - Modulo Geral')
        root = QWidget(self)
        root.setStyleSheet('background-color: #eef3fa;')
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        banner = QWidget()
        banner.setObjectName('moduleBanner')
        banner.setStyleSheet('QWidget#moduleBanner {background-color:#0d3765;}')
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 11, 20, 11)
        self.module_title = QLabel('MODULO ATIVO: ARQUIVOS GERAIS')
        self.module_title.setStyleSheet('color:white; font-size:18px; font-weight:800; background:transparent;')
        self.module_hint = QLabel('Organizacao de fotografias e analise de arquivos')
        self.module_hint.setStyleSheet('color:#d5e9ff; font-size:12px; background:transparent;')
        banner_layout.addWidget(self.module_title)
        banner_layout.addStretch()
        banner_layout.addWidget(self.module_hint)
        layout.addWidget(banner)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.setStyleSheet('''
            QTabWidget::pane { border:0; background:#eef3fa; }
            QTabBar { background:#e6edf7; }
            QTabBar::tab { background:#dfe8f4; color:#365474; padding:15px 34px;
                           min-width:190px; font-size:15px; font-weight:700;
                           border-right:1px solid #c6d3e3; border-bottom:4px solid #c4d2e4; }
            QTabBar::tab:selected { background:#ffffff; color:#063d78;
                                    border-bottom:5px solid #1373d1; font-weight:900; }
            QTabBar::tab:hover:!selected { background:#c9dff5; color:#123f70; }
        ''')
        self.geral = Geral()
        self.cientifico = Cientifico()
        self.geral.setWindowFlags(Qt.WindowType.Widget)
        self.cientifico.setWindowFlags(Qt.WindowType.Widget)
        self.tabs.addTab(self.geral, '  ARQUIVOS GERAIS  ')
        self.tabs.addTab(self.cientifico, '  CIENTIFICO  ')
        self.tabs.currentChanged.connect(self.update_active_module)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)
        self.update_active_module(0)

    def update_active_module(self, index):
        if index == 0:
            self.module_title.setText('MODULO ATIVO: ARQUIVOS GERAIS')
            self.module_hint.setText('Fotografias, arquivos e duplicatas')
            self.setWindowTitle('Constantino Software | Organizador Inteligente - Arquivos Gerais')
        else:
            self.module_title.setText('MODULO ATIVO: CIENTIFICO')
            self.module_hint.setText('Artigos cientificos, referencias e duplicatas')
            self.setWindowTitle('Constantino Software | Organizador Inteligente - Cientifico')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    quarantine_root()
    window = Constantino()
    window.show()
    sys.exit(app.exec())
