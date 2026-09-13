"""Separate frozen recovery, new numerical runs, audit, and current publication."""
from pathlib import Path
import argparse, json, os, shutil, subprocess, sys, time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))


def run(args):
    print('RUN',*map(str,args),flush=True)
    subprocess.run(list(map(str,args)),cwd=ROOT,check=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage',choices=['restore','numeric','audit','diagnostics','paper','workbooks','all'])
    ap.add_argument('--source-root',help='Directory containing C题/附件; raw inputs are read only')
    ap.add_argument('--node',default=os.environ.get('CODEX_NODE_BIN',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')))
    ap.add_argument('--renderer',default=os.environ.get('DOCX_RENDERER',str(Path.home()/'.codex/plugins/cache/openai-primary-runtime/documents/26.905.11957/skills/documents/render_docx.py')))
    a=ap.parse_args()
    if a.source_root:os.environ['CUMCM_SOURCE_ROOT']=str(Path(a.source_root).resolve())
    phase=a.stage
    if phase in ('restore','all'):run([sys.executable,'scripts/unpack_frozen.py'])
    if phase=='numeric':
        from src.model.config import load_config
        from src.model.data import load_data
        from src.model.experiments import run_all
        cfg=load_config('config/final.yaml');cfg.update(json.loads((ROOT/'frozen/resolved_config.json').read_text()))
        target=ROOT/'outputs/recomputed_formal'
        if target.exists():raise SystemExit('outputs/recomputed_formal exists; preserve or move it before a fresh numerical run')
        (target/'frozen').mkdir(parents=True)
        cfg['output_root']='outputs/recomputed_formal';cfg['_output_root']=str(target)
        (target/'frozen/resolved_config.json').write_text(json.dumps({k:v for k,v in cfg.items() if not k.startswith('_')},indent=2))
        # Reuse the original January-selected configuration; never overwrite frozen answers.
        run_all(load_data(cfg),cfg,stage='official')
        run([sys.executable,'src/audit/audit_final.py','--frozen-dir',target/'frozen'])
        return
    if phase in ('diagnostics','all'):
        run([sys.executable,'scripts/contribution_experiments.py'])
        run([sys.executable,'scripts/summarize_revision.py'])
    if phase in ('audit','all'):
        run([sys.executable,'-m','unittest','discover','-s','tests','-v'])
        run([sys.executable,'src/audit/audit_final.py','--workbooks'])
    if phase=='workbooks':
        # Existing builder consumes exactly outputs/c_final_v1/frozen.
        runtime=Path(a.node).parent.parent/'node_modules'
        link=ROOT/'node_modules'
        if not link.exists():link.symlink_to(runtime,target_is_directory=True)
        run([a.node,'scripts/build_workbooks.mjs'])
        run([sys.executable,'src/audit/audit_final.py','--workbooks'])
    if phase in ('paper','all'):
        run([sys.executable,'scripts/summarize_revision.py'])
        run([sys.executable,'scripts/publication_charts.py'])
        run([sys.executable,'论文修订源文件/build.py'])
        source=ROOT/'论文修订源文件/C题论文_v3.docx'
        publication=ROOT/'publication';publication.mkdir(exist_ok=True)
        shutil.copy2(source,publication/'C题论文_实质改进版.docx')
        # Make installed Chinese and math fonts visible to bundled headless LO.
        # No fonts are copied into the submission package.
        if sys.platform=='darwin' and 'FONTCONFIG_FILE' not in os.environ:
            from xml.sax.saxutils import escape
            cache=ROOT/'work/fontconfig';cache.mkdir(parents=True,exist_ok=True)
            dirs=[Path('/Applications/Microsoft Excel.app/Contents/Resources/DFonts'),Path('/System/Library/Fonts/Supplemental'),Path.home()/'Library/Fonts']
            content='<?xml version="1.0"?><fontconfig>'+''.join('<dir>'+escape(str(p))+'</dir>' for p in dirs if p.exists())
            content+='<cachedir>'+escape(str(cache/'cache'))+'</cachedir>'
            for before,after in [('Liberation Serif','Times New Roman'),('PMingLiU','SimSun'),('Meiryo','SimSun')]:
                content+='<match target="pattern"><test name="family"><string>'+before+'</string></test><edit name="family" mode="assign" binding="strong"><string>'+after+'</string></edit></match>'
            content+='<alias><family>serif</family><prefer><family>Times New Roman</family><family>SimSun</family></prefer></alias><alias><family>宋体</family><prefer><family>SimSun</family></prefer></alias></fontconfig>'
            (cache/'fonts.conf').write_text(content)
            os.environ['FONTCONFIG_FILE']=str(cache/'fonts.conf')
        run([sys.executable,'scripts/build_ai_usage.py'])
        run([sys.executable,a.renderer,ROOT/'work/ai_usage/AI工具使用详情.docx','--output_dir',ROOT/'qa/ai_usage','--emit_pdf'])
        shutil.copy2(ROOT/'qa/ai_usage/AI工具使用详情.pdf',ROOT/'AI工具使用详情.pdf')
        began=time.perf_counter()
        run([sys.executable,a.renderer,publication/'C题论文_实质改进版.docx','--output_dir',ROOT/'qa/current_render','--emit_pdf'])
        shutil.copy2(ROOT/'qa/current_render/C题论文_实质改进版.pdf',publication/'C题论文_实质改进版.pdf')
        (publication/'render_timing.json').write_text(json.dumps({'document_render_seconds':time.perf_counter()-began}))
        run([sys.executable,'scripts/check_revision_delivery.py'])


if __name__=='__main__':main()
