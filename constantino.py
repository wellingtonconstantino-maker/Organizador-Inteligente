"""Constantino Software — interface única com os módulos Geral e Científico.
Integração inicial; comparação perceptual/de conteúdo não implementada.
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Qt
from modulo_geral import Main as Geral, quarantine_root
from modulo_cientifico import Main as Cientifico

class Constantino(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Constantino Software | Organizador Inteligente — integração 0.9.1 (teste)')
        self.resize(1480, 900)
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet('QTabBar::tab { padding: 11px 28px; font-size: 14px; font-weight: 600; }')
        self.geral = Geral()
        self.cientifico = Cientifico()
        self.geral.setWindowFlags(Qt.Widget)
        self.cientifico.setWindowFlags(Qt.Widget)
        self.tabs.addTab(self.geral, 'Arquivos gerais')
        self.tabs.addTab(self.cientifico, 'Científico')
        self.setCentralWidget(self.tabs)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    quarantine_root()
    w = Constantino()
    w.show()
    sys.exit(app.exec())
