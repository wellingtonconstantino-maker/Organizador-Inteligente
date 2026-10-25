from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from constantino import QApplication, Constantino, quarantine_root
app=QApplication(sys.argv)
quarantine_root()
w=Constantino();w.show()
sys.exit(app.exec())
