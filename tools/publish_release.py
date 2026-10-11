"""매 릴리즈에 xdelta와 해당 빌드의 와이드 패치를 함께 첨부한다."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from prepare_widescreen_release import generate,ROOT

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--iso',required=True,type=Path)
    ap.add_argument('--xdelta',required=True,type=Path)
    ap.add_argument('--notes',required=True,type=Path)
    ap.add_argument('--tag',required=True)
    ap.add_argument('--title',required=True)
    ap.add_argument('--publish',action='store_true',help='검증 후 GitHub에 실제 게시')
    a=ap.parse_args();m=json.loads((ROOT/'release_manifest.json').read_text('utf8'))
    assert m['version']==a.tag,'manifest 버전과 태그 불일치'
    assert a.xdelta.name==m['asset'] and a.xdelta.stat().st_size==m['asset_size']
    assert hashlib.sha256(a.xdelta.read_bytes()).hexdigest()==m['asset_sha256']
    h=hashlib.sha256()
    with a.iso.open('rb') as f:
        while block:=f.read(8*1024*1024):h.update(block)
    assert h.hexdigest()==m['result_iso_sha256'],'결과 ISO 해시 불일치'
    patch,info=generate(a.iso,update_manifest=False)
    assert info==m['widescreen'],'와이드 manifest 갱신 필요'
    notes=a.notes.read_text('utf8')
    assert patch.name in notes and '16:9' in notes and '비활성화' in notes
    print('배포 검사 통과:',a.xdelta.name,patch.name)
    if not a.publish:return
    repo='snake759494/nhl-2004-korean-patch'
    found=subprocess.run(['gh','release','view',a.tag,'--repo',repo],capture_output=True).returncode==0
    if found:
        current=json.loads(subprocess.check_output(['gh','release','view',a.tag,'--repo',repo,'--json','assets']))
        existing={x['name']:x for x in current['assets']}
        for file in (a.xdelta,patch):
            if file.name in existing:
                assert existing[file.name]['digest']=='sha256:'+hashlib.sha256(file.read_bytes()).hexdigest(),'기존 동봉 파일과 해시 불일치'
            else:subprocess.run(['gh','release','upload',a.tag,str(file),'--repo',repo],check=True)
        subprocess.run(['gh','release','edit',a.tag,'--repo',repo,'--notes-file',str(a.notes),'--title',a.title,'--prerelease=false','--latest'],check=True)
    else:
        subprocess.run(['gh','release','create',a.tag,str(a.xdelta),str(patch),'--repo',repo,'--target','main','--title',a.title,'--notes-file',str(a.notes),'--latest'],check=True)

if __name__=='__main__':main()
