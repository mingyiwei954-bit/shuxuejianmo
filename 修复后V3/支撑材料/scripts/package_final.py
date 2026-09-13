from pathlib import Path
from datetime import datetime
import hashlib,json,lzma,shutil,zipfile,tempfile,os
import re
from freeze_codec import pack,solidify
ROOT=Path(__file__).resolve().parents[1];FINAL=ROOT/'outputs/c_final_v1'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    v=json.loads((FINAL/'final_validation_v3.json').read_text())
    if v['status']!='PASS':raise RuntimeError('Refusing to package failed current run')
    source=[]
    for folder in ['src','scripts','tests','paper','config']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:source.append(dict(path=str(p.relative_to(ROOT)),sha256=digest(p)))
    (FINAL/'evidence/active_source_hashes.json').write_text(json.dumps(source,ensure_ascii=False,indent=2))
    provenance=json.loads((FINAL/'evidence/source_provenance.json').read_text())
    original=[r for r in provenance if r.get('kind')=='original_input']
    for r in original:
        source_root=os.environ.get('CUMCM_SOURCE_ROOT',json.loads((ROOT/'config/final.yaml').read_text())['source_root'])
        if digest(Path(source_root)/r['path'])!=r['sha256']:raise RuntimeError('Original input changed: '+r['path'])
    (FINAL/'evidence/source_provenance.json').write_text(json.dumps(original+[dict(kind='current_source',**r) for r in source],ensure_ascii=False,indent=2))
    cache=ROOT/'work/packed_frozen';manifest=cache/'csv_manifest.json';solid=ROOT/'work/columns_solid.tar.xz';tag=ROOT/'work/columns_solid_manifest.sha256'
    duplicates={'q3_decision_versions.csv','q4_3_decision_versions.csv','q3_S3_decisions.csv','q4_3_S3_decisions.csv','q3_S3_dispatch.csv','q4_3_S3_dispatch.csv'}
    expected={p.name:digest(p) for p in (FINAL/'frozen').glob('*.csv') if p.name not in duplicates}
    valid=manifest.exists() and {r['name']:r['sha256'] for r in json.loads(manifest.read_text())['files']}==expected
    if not valid:pack(FINAL/'frozen',cache)
    if not solid.exists() or not tag.exists() or tag.read_text()!=digest(manifest):
        solidify(cache,solid);tag.write_text(digest(manifest))
    with tempfile.TemporaryDirectory(prefix='v3-package-') as td:
        stage=Path(td)
        for folder in ['src','scripts','tests','paper','config']:
            shutil.copytree(ROOT/folder,stage/folder,ignore=shutil.ignore_patterns('__pycache__'))
        for folder in ['audit','evidence','workbooks','charts','logs','research']:
            shutil.copytree(FINAL/folder,stage/folder)
        # Full research trajectories are in the common lossless column archive.
        for p in (stage/'research').glob('*_ipm.csv.xz'):p.unlink()
        for name in ['run_pipeline.sh','requirements.txt']:shutil.copy2(ROOT/name,stage/name)
        shutil.copy2(FINAL/'paper/AI工具使用详情.pdf',stage/'AI工具使用详情.pdf');shutil.copy2(FINAL/'final_validation_v3.json',stage/'final_validation_v3.json')
        (stage/'frozen').mkdir()
        shutil.copy2(manifest,stage/'frozen/csv_manifest.json');shutil.copy2(solid,stage/'frozen/columns.tar.xz')
        for p in (FINAL/'frozen').iterdir():
            if not p.is_file() or p.name in duplicates:continue
            if p.suffix!='.csv':shutil.copy2(p,stage/'frozen'/p.name)
        (stage/'README.md').write_text('''# V3闭环修订支撑材料

原始输入为官方C题及附件，未修改观测。先在config/final.yaml配置source_root（其下应含C题/附件），或设置CUMCM_SOURCE_ROOT。运行run_pipeline.sh即可重建；运行环境需Python及requirements.txt、Node与@oai/artifact-tool，DOCX转PDF使用Codex文档运行时。对冻结结果只读检查可先执行scripts/unpack_frozen.py。

frozen保存全精度结果，CSV按列去重后固实XZ压缩，未舍入任何数字。csv_manifest保存每份CSV的原始SHA256；unpack_frozen将逐字节恢复并校验，另恢复重复S3轨迹及正式子账本，输出到outputs/c_final_v1/frozen，随后可运行src/audit/audit_final.py --workbooks。主结果S3与S0/S1/S2共享参考日前承诺；所有年度状态来自一月可核验启动账本。训练配置见resolved_config，不能用未解析默认值替代。

论文费用按取消退原价保留50%违约费、交付物理区间价解释；同路径逐次与不退款费用另列。不声称其他结算解释下最优。历史场景为预测分布，非伪造的实际数据。未宣称团队已经完成提交签核。
''')
        for p in stage.rglob('*'):
            if p.is_file() and p.suffix in ['.log','.md','.json','.txt'] and not p.is_relative_to(stage/'frozen'):
                content=p.read_text(encoding='utf-8')
                content=re.sub('/'+'Users/[^/\\s\\"\\x27]+','<LOCAL_HOME>',content)
                p.write_text(content,encoding='utf-8')
        entries=[dict(path=str(p.relative_to(stage)),bytes=p.stat().st_size,sha256=digest(p)) for p in stage.rglob('*') if p.is_file()]
        (stage/'SHA256SUMS.json').write_text(json.dumps(dict(generated_at=datetime.now().astimezone().isoformat(),files=entries),ensure_ascii=False,indent=2))
        with zipfile.ZipFile(FINAL/'支撑材料.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in stage.rglob('*'):
                if p.is_file():z.write(p,str(p.relative_to(stage)))
    size=(FINAL/'支撑材料.zip').stat().st_size
    if size>20_000_000:raise RuntimeError(f'Support archive exceeds 20MB: {size}')
    files=[dict(path=str(p.relative_to(FINAL)),bytes=p.stat().st_size,sha256=digest(p)) for p in FINAL.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json' and 'qa' not in p.relative_to(FINAL).parts]
    (FINAL/'SHA256SUMS.json').write_text(json.dumps(dict(generated_at=datetime.now().astimezone().isoformat(),files=files,archive_bytes=size),ensure_ascii=False,indent=2));print('Packaged',size,'bytes',flush=True)
if __name__=='__main__':main()
