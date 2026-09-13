"""Lossless column deduplication for the competition's support-file size limit.

All original CSV strings are preserved. The restored bytes must match SHA256;
this is packaging only and never rounds or changes model observations/results.
"""
from pathlib import Path
import csv,hashlib,json,lzma,io,shutil,tarfile,tempfile

def sha(data):return hashlib.sha256(data).hexdigest()

def pack(source,target):
    source=Path(source);target=Path(target);blobs=target/'columns';blobs.mkdir(parents=True,exist_ok=True)
    manifest={'format':'lossless-csv-columns-v1','files':[]}
    duplicates={'q3_decision_versions.csv','q4_3_decision_versions.csv','q3_S3_decisions.csv','q4_3_S3_decisions.csv','q3_S3_dispatch.csv','q4_3_S3_dispatch.csv'}
    for p in sorted(source.iterdir()):
        if not p.is_file() or p.name in duplicates:continue
        if p.suffix!='.csv':shutil.copy2(p,target/p.name);continue
        raw=p.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');newline='\r\n' if b'\r\n' in raw else '\n'
        reader=csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''));header=next(reader);cols=[[] for _ in header];count=0
        for row in reader:
            if len(row)!=len(header):raise ValueError(('Nonrectangular CSV',p.name))
            count+=1
            for col,val in zip(cols,row):
                if '\n' in val or '\r' in val:raise ValueError(('Multiline value',p.name))
                col.append(val)
        ids=[]
        for col in cols:
            data='\n'.join(col).encode('utf-8');key=sha(data);out=blobs/(key+'.xz')
            if not out.exists():out.write_bytes(lzma.compress(data,preset=6))
            ids.append(key)
        record=dict(name=p.name,sha256=sha(raw),bytes=len(raw),bom=bom,newline=newline,header=header,rows=count,columns=ids)
        # Verify the CSV dialect before recording a supposedly lossless manifest.
        if sha(reconstruct(record,cols))!=record['sha256']:raise ValueError(('CSV byte roundtrip failed',p.name))
        manifest['files'].append(record);print('Packed losslessly',p.name,flush=True)
    (target/'csv_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest

def reconstruct(record,cols):
    out=io.StringIO(newline='');writer=csv.writer(out,lineterminator=record['newline']);writer.writerow(record['header']);writer.writerows(zip(*cols))
    return out.getvalue().encode('utf-8-sig' if record['bom'] else 'utf-8')

def unpack(source,target):
    source=Path(source);target=Path(target);target.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'csv_manifest.json').read_text())
    solid={}
    if (source/'columns.tar.xz').exists():
        with tarfile.open(source/'columns.tar.xz','r:xz') as archive:
            for member in archive:
                if not member.isfile() or len(member.name)!=64:raise ValueError('Invalid column member')
                data=archive.extractfile(member).read()
                if sha(data)!=member.name:raise ValueError('Corrupt solid column')
                solid[member.name]=data
    for record in manifest['files']:
        cols=[]
        for key in record['columns']:
            data=solid[key] if solid else lzma.decompress((source/'columns'/(key+'.xz')).read_bytes())
            if sha(data)!=key:raise ValueError('Corrupt column: '+key)
            vals=data.decode('utf-8').split('\n') if record['rows'] else []
            if len(vals)!=record['rows']:raise ValueError('Wrong row count')
            cols.append(vals)
        raw=reconstruct(record,cols)
        if sha(raw)!=record['sha256']:raise ValueError('Corrupt CSV: '+record['name'])
        (target/record['name']).write_bytes(raw)
    for p in source.iterdir():
        if p.is_file() and p.name not in ['csv_manifest.json','columns.tar.xz'] and p.parent!=target:shutil.copy2(p,target/p.name)
    return len(manifest['files'])

def solidify(source,target):
    source=Path(source)
    manifest=json.loads((source/'csv_manifest.json').read_text())
    labels={}
    for r in manifest['files']:
        for label,key in zip(r['header'],r['columns']):labels.setdefault(key,label)
    keys=sorted(labels,key=lambda key:(labels[key],key))
    with lzma.open(target,'wb',format=lzma.FORMAT_XZ,filters=[{'id':lzma.FILTER_LZMA2,'preset':9,'dict_size':128*1024*1024}]) as dst:
        with tarfile.open(fileobj=dst,mode='w|') as archive:
            for key in keys:
                p=source/'columns'/(key+'.xz')
                raw=lzma.decompress(p.read_bytes());info=tarfile.TarInfo(p.stem);info.size=len(raw);info.mtime=0;archive.addfile(info,io.BytesIO(raw))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['pack','unpack']);ap.add_argument('source');ap.add_argument('target');a=ap.parse_args()
    (pack if a.operation=='pack' else unpack)(a.source,a.target)
