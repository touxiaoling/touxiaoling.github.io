from datetime import datetime
import subprocess
from pathlib import Path
import re
import yaml

def represent_none(self, _):
    return self.represent_scalar('tag:yaml.org,2002:null', '')
yaml.add_representer(type(None), represent_none)

doc_path=Path("./source/")

prog=re.compile(r"^---\n(?P<context>.*?)^---\n",flags=re.DOTALL|re.M)

for p in doc_path.glob("**/*.md"):
    if p.stem=="index":
        continue
    create_time=subprocess.check_output(f'git log  --pretty=format:"%ad" --date unix -- {p} | tail -1',shell=True)
    if not create_time:
        continue
    create_time=datetime.fromtimestamp(float(create_time))
    context=p.read_text()
    mdtrri:dict=yaml.load(prog.search(context,).group("context"),yaml.Loader)
    if "date" not in mdtrri:
        mdtrri["date"]=create_time    
        md_title=yaml.dump(mdtrri,Dumper=yaml.Dumper,sort_keys=False,allow_unicode=True)
        md_title="---\n"+md_title+"---\n"
        context_changed=prog.sub(md_title,context,count=1)
        p.write_text(context_changed)