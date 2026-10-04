"""부분 번역 출력 검증용. 완성 배포본을 생성하는 빌더가 아니다."""
from pathlib import Path
import struct,json,shutil,re
from formats import big,pack_big
from texts import entries
from codepatch import patch
import kfont,iso,tdb,fng,elf_text,display_text,art_text,names as player_names

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'NHL 2004 (USA).iso'
OUTPUT=ROOT/'NHL 2004 (USA) (Korean TEST).iso'

def main():
    ko=json.loads((ROOT/'translation/ko.json').read_text(encoding='utf-8'))
    boot=json.loads((ROOT/'translation/boot.ko.json').read_text(encoding='utf-8'))
    names=player_names.load(ROOT)
    teams=json.loads((ROOT/'translation/teams.ko.json').read_text(encoding='utf8'))
    short_names=json.loads((ROOT/'translation/scoreboard.ko.json').read_text(encoding='utf8'))
    overrides=json.loads((ROOT/'translation/overrides.json').read_text(encoding='utf8'))
    fng_ko=json.loads((ROOT/'translation/fng.ko.json').read_text(encoding='utf8'))
    elf_ko=json.loads((ROOT/'translation/elf_text.ko.json').read_text(encoding='utf8'))
    elf_offsets=json.loads((ROOT/'translation/elf_offsets.ko.json').read_text(encoding='utf8'))
    cities=json.loads((ROOT/'translation/cities.ko.json').read_text(encoding='utf8'))
    credits=json.loads((ROOT/'translation/credits.ko.json').read_text(encoding='utf8'))
    agreement=(ROOT/'translation/online_agreement.ko.txt').read_text(encoding='utf8')
    privacy='이곳에는 개인정보 관련 내용이 많이 있습니다!'
    ko.update(teams)
    ko.update(short_names)
    geography={**ko,**teams,**cities,'NY':'뉴욕','Phillipines':'필리핀'}
    chars=sorted(set(''.join(geography.values())+''.join(boot)+''.join(names.values())+''.join(fng_ko.values())+''.join(elf_ko.values())+''.join(x['korean'] for x in elf_offsets.values())+''.join(credits.values())+agreement+privacy+''.join(v for m in overrides.values() for v in m.values()))-set(chr(i) for i in range(256)))
    assert len(chars)<=1920,'2바이트 코드 공간 초과'
    def encode(s):
        out=bytearray()
        for c in s:
            if c in chars:
                i=chars.index(c);out.extend((0x81+i//128,0x80+i%128))
            else:out+=c.encode('cp1252')
        return bytes(out)
    def textfile(d,name):
        src=entries(d);base=16+4*len(src) if d[:4]==b'\xfe'*4 else 0
        out=bytearray(d[:base]+bytes(4*len(src)))
        for i,s in enumerate(src):
            struct.pack_into('<I',out,base+i*4,len(out));out+=encode(overrides.get(name,{}).get(str(i),ko.get(s,s)))+b'\0'
        return bytes(out)
    def bootfile(d):
        base=struct.unpack_from('<I',d,16)[0];count=struct.unpack_from('<I',d,base+12)[0]
        assert len(boot)==count
        out=bytearray(d[:base+16]+bytes(count*4))
        for i,s in enumerate(boot):
            struct.pack_into('<I',out,base+16+4*i,len(out)-base)
            for c in s:out+=struct.pack('<H',0x400+chars.index(c) if c in chars else ord(c))
            out+=b'\0\0'
        out+=bytes(-len(out)%4);struct.pack_into('<I',out,base+4,len(out)-base)
        return bytes(out)
    local=pack_big([(n,textfile(d,n) if n.endswith('.ENG') else bootfile(d) if n=='PS2_LOCALE_ENGLISH.loc' else d) for n,d in big((ROOT/'work/FE_LOCAL.VIV').read_bytes())])
    fonts=[]
    for n,d in big((ROOT/'work/FE_FE_FONTS.VIV').read_bytes()):
        f,preview=kfont.build(d,chars,ROOT/'NanumSquareNeo-dEb.ttf');fonts.append((n,f))
        preview.save(ROOT/'work'/('ko-'+n+'.png'))
    gamefonts=pack_big([(n,kfont.build_legacy(d,chars,ROOT/'NanumSquareNeo-dEb.ttf')[0] if d[:4]==b'FNTS' else d) for n,d in big((ROOT/'work/UGI_UGIALL.VIV').read_bytes())],2048)
    index={p:(l,s) for p,l,s,r in iso.walk(SOURCE)}
    characs=pack_big([(n,kfont.build_legacy(d,chars,ROOT/'NanumSquareNeo-dEb.ttf')[0] if d[:4]==b'FNTS' else d) for n,d in big(iso.read(*index['GAMEDATA/CHARACS.VIV'],SOURCE))],4)
    preload=pack_big([(n,local if n.lower()=='fe/local.viv' else gamefonts if n.lower()=='ugi/ugiall.viv' else characs if n.lower()=='gamedata/characs.viv' else d) for n,d in big((ROOT/'work/PRELOAD.VIV').read_bytes())],4)
    preload=preload[:4]+struct.pack('<I',len(preload))+preload[8:]
    elf,changes=patch((ROOT/'work/SLUS_207.56').read_bytes(),chars,short_names)
    elf,text_changes=elf_text.patch(elf,elf_ko,encode,elf_offsets);changes.extend(text_changes)
    updates={'SLUS_207.56':elf,'FE/LOCAL.VIV':local,'FE/FE_FONTS.VIV':pack_big(fonts,2048),'PRELOAD.VIV':preload}
    updates['UGI/UGIALL.VIV']=gamefonts
    updates['GAMEDATA/CHARACS.VIV']=characs
    total=0
    def database_archive(source):
      nonlocal total
      db=[]
      for n,d in big(source):
        if n in ('nhl2004.tdb','nhl2004PC.tdb','nhlawards.tdb'):
            d,count=tdb.patch_names(d,names,encode,teams,geography);total+=count
        elif n in ('DraftPlayersFirstName.txt','DraftPlayersLastName.txt'):
            def replace_name(m):
                name=m[2].decode('cp1252');assert name in names,name
                value=encode(names[name]);assert len(value)<16,(name,names[name])
                return m[1]+value
            d=re.sub(rb'(?m)^([^/\r\n][^:\r\n]*:[ \t]*)([^\s]+)',replace_name,d)
        elif n.startswith('credits_') and n.endswith('.txt'):
            d=display_text.credits(d,credits,encode)
        elif n=='online_agreement.txt':d=display_text.agreement(agreement,encode)
        elif n=='online_privacy.txt':d=display_text.agreement(privacy,encode)
        db.append((n,d))
      return pack_big(db,2048)
    updates['DB/DB.VIV']=database_archive((ROOT/'work/DB_DB.VIV').read_bytes())
    updates['DB/TUNING.VIV']=database_archive(iso.read(*index['DB/TUNING.VIV'],SOURCE))
    for path in ['FE/FE_ART.VIV','FE/OV_ART.VIV']:
        updates[path],count=art_text.archive(iso.read(*index[path],SOURCE),ROOT/'NanumSquareNeo-dEb.ttf')
        print('문자 이미지 번역:',path,count)
    # 언어 테이블 조회에 실패할 때 표시되는 FNG 내부 UTF-16 문구.
    fng_mapping={**ko,**fng_ko};fng_count=0
    def screen_archive(d):
        nonlocal fng_count
        values=[];changed=False
        for name,data in big(d):
            new=data
            if name.lower()=='db/tuning.viv':new=updates['DB/TUNING.VIV']
            elif name.upper() in ('FE/FE_ART.VIV','FE/OV_ART.VIV'):new=updates[name.upper()]
            elif name.lower().endswith('.fng'):
                new,count=fng.patch(data,fng_mapping,chars);fng_count+=count
            elif name.lower() in ('fe/feng.viv','fe/online.viv','fe/playnow.viv','fe/custom.viv','ugi/overlay.viv'):
                new=screen_archive(data)
            changed|=new!=data;values.append((name,new))
        if not changed:return d
        result=pack_big(values,4)
        # 사전 읽기 컨테이너는 파일 크기가 리틀 엔디언이다.
        if int.from_bytes(d[4:8],'little')==len(d):result=result[:4]+struct.pack('<I',len(result))+result[8:]
        return result
    index={p:(l,s) for p,l,s,r in iso.walk(SOURCE)}
    for path in ['FE/FENG.VIV','FE/FENG_PAL.VIV','FE/ONLINE.VIV','FE/PLAYNOW.VIV','FE/CUSTOM.VIV','UGI/OVERLAY.VIV','FPRELOAD.VIV']:
        updates[path]=screen_archive(iso.read(*index[path],SOURCE))
    updates['PRELOAD.VIV']=screen_archive(updates['PRELOAD.VIV'])
    print('화면 파일 직접 표시 문자열:',fng_count)
    print('선수 이름/성 변경 필드:',total)
    outdir=ROOT/'work/test-build';outdir.mkdir(exist_ok=True)
    for n,d in updates.items():(outdir/n.replace('/','_')).write_bytes(d)
    (outdir/'changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
    (outdir/'characters.txt').write_text(''.join(chars),encoding='utf-8')
    (outdir/'manifest.json').write_text(json.dumps(list(updates),indent=2),encoding='utf8')
    print(json.dumps({n:len(d) for n,d in updates.items()},indent=2))

if __name__=='__main__':main()
