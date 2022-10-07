from datetime import datetime
from importlib.resources import contents
import subprocess
from pathlib import Path
import os
doc_path=Path("./source/")

for p in doc_path.glob("**/*.md"):
    if p.stem=="index":
        continue
    change_info=subprocess.check_output(f'git log --pretty=format:"%cs | %s" -- {p} ',shell=True)
    change_info=change_info.decode().split("\n")
    change_log = '''\n## 修改历史
|  时间  | 修改内容 |
| ---- | --- |\n'''
    for i_change in change_info:
        change_log+=i_change+"\n"
    print(change_log)
    # context=p.read_text()+change_log
    # p.write_text(context)