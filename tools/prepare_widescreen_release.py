"""ISO별 CRC와 명령 호환성을 검증하고 필수 와이드 동봉 파일을 생성한다."""
from pathlib import Path
import argparse,functools,hashlib,json,struct
import iso

ROOT=Path(__file__).resolve().parent.parent
FINGERPRINT='905c5758d5682cda7b675fc2c2891d13838110c70323e27dafc5c5cde8f419f2'
WORDS={0x12d188:0x08041c32,
       0x1070c8:0x3c013f40,0x1070cc:0x44811000,0x1070d0:0x46020842,
       0x1070d4:0xe6010020,0x1070d8:0x0804b464,0x1070dc:0,
       0x12d218:0x08041c38,
       0x1070e0:0x3c013faa,0x1070e4:0x3421aaab,0x1070e8:0x4481a000,
       0x1070ec:0x46140502,0x1070f0:0x0804b488,0x1070f4:0}

def generate(source,root=ROOT,update_manifest=True):
    source=Path(source);root=Path(root)
    index={n:(l,s) for n,l,s,r in iso.walk(source)}
    d=iso.read(*index['SLUS_207.56'],source)
    assert hashlib.sha256(d[0x12cff0-0x107000:0x12d310-0x107000]).hexdigest()==FINGERPRINT,'투영 코드 변경: 재분석 필요'
    assert d[0xc8:0xf8]==bytes(0x30),'와이드 보조 코드 영역이 사용 중임'
    assert struct.unpack_from('<I',d,0x12d188-0x107000)[0]==0xe6010020
    assert struct.unpack_from('<I',d,0x12d218-0x107000)[0]==0x46000506
    crc=functools.reduce(int.__xor__,struct.unpack('<'+'I'*(len(d)//4),d[:len(d)//4*4]),0)
    name=f'SLUS-20756_{crc:08X}.pnach'
    text=('gametitle=NHL 2004 Korean Patch\n\n[Widescreen 16:9]\n'
          'author=snake759494\n'
          'description=Hor+ 16:9. Restart after enabling or disabling.\n'
          'comment=3D horizontal projection x0.75; conservative wider culling. 2D HUD/menu art is stretched.\n'
          'gsaspectratio=16:9\n'
          '// Generated for this ELF CRC. Do not rename for another build.\n')
    text+=''.join(f'patch=1,EE,{a:08X},word,{v:08X}\n' for a,v in WORDS.items())
    folder=root/'patches';folder.mkdir(parents=True,exist_ok=True)
    path=folder/name;path.write_text(text,encoding='utf8',newline='\n')
    info={'name':name,'crc':f'{crc:08X}','size':path.stat().st_size,
          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'elf_sha256':hashlib.sha256(d).hexdigest(),'required_release_asset':True,
          'projection_multiplier':0.75,'culling_multiplier':4/3,
          'instruction_fingerprint':FINGERPRINT}
    if update_manifest:
        manifest=root/'release_manifest.json'
        m=json.loads(manifest.read_text('utf8')) if manifest.exists() else {}
        m['widescreen']=info;manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n','utf8')
    return path,info

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('iso',type=Path);args=p.parse_args()
    path,info=generate(args.iso);print(json.dumps(info,ensure_ascii=False,indent=2))
