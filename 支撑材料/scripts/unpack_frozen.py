from pathlib import Path
import lzma,shutil,csv,json
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'config/final.yaml').read_text())
FINAL=ROOT/cfg['output_root'];F=FINAL/'frozen';F.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'frozen'
if not SOURCE.exists():SOURCE=F
if (SOURCE/'csv_manifest.json').exists():
    from freeze_codec import unpack
    unpack(SOURCE,F)
for p in SOURCE.iterdir():
    if p.name.endswith('.csv.xz'):
        with lzma.open(p,'rb') as src,(F/p.with_suffix('').name).open('wb') as dst:shutil.copyfileobj(src,dst)
    elif p.is_file() and p.parent!=F and p.name not in ['csv_manifest.json','columns.tar.xz']:shutil.copy2(p,F/p.name)
for folder in ['workbooks','evidence','charts','research']:
    if (ROOT/folder).exists():shutil.copytree(ROOT/folder,FINAL/folder,dirs_exist_ok=True)
for mode in ['q3','q4_3']:
    shutil.copy2(F/f'{mode}_dispatch.csv',F/f'{mode}_S3_dispatch.csv')
    with (F/'decision_versions.csv').open(encoding='utf-8-sig',newline='') as src,(F/f'{mode}_S3_decisions.csv').open('w',encoding='utf-8-sig',newline='') as dst:
        r=csv.DictReader(src);w=csv.DictWriter(dst,fieldnames=r.fieldnames);w.writeheader();w.writerows(row for row in r if row['mode']==mode)
    shutil.copy2(F/f'{mode}_S3_decisions.csv',F/f'{mode}_decision_versions.csv')
print('Frozen CSVs restored')
for p in F.glob('research_*_dispatch.csv'):
    name=p.name.removeprefix('research_').removesuffix('_dispatch.csv')+'.csv.xz'
    with p.open('rb') as src,lzma.open(FINAL/'research'/name,'wb') as dst:shutil.copyfileobj(src,dst)
