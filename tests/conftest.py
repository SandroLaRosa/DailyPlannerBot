import sys
from pathlib import Path
 
# Adds Src/ to the path so that `from classes.event import ...`
# and `from modules.xxx import ...` resolve correctly from the Test/ folder
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))