from datetime import datetime
import subprocess
from pathlib import Path
import os
doc_path=Path("./source/")

for p in doc_path.glob("**/*.md"):
    if p.stem=="index":
        continue
    m_time=subprocess.check_output(f'git log  --pretty=format:"%ad" --date unix -- {p} | head -1',shell=True)
    if not m_time:
        continue
    m_time=int(m_time.decode().strip())
    os.utime(p,(m_time,m_time))