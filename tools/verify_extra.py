"""추가 번역의 바이트 경계, 이름 포인터, 중첩 자료, 이미지 검증."""
import json,re,struct
from pathlib import Path
from formats import big
import iso,elf_text,display_text,art_audit,art_text

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'work/test-build'

def main():
    chars=(OUT/'characters.txt').read_text('utf8')
    def encode(s):
        return b''.join(bytes((129+chars.index(c)//128,128+chars.index(c)%128)) if c in chars else c.encode('cp1252') for c in s)
    def decode(d):
        out='';i=0
        while i<len(d):
            if 129<=d[i]<=143:
                assert i+1<len(d) and d[i+1]>=128
                n=(d[i]-129)*128+d[i+1]-128;assert n<len(chars)
                out+=chars[n];i+=2
            else:out+=bytes([d[i]]).decode('cp1252');i+=1
        return out
    index={p:(l,s) for p,l,s,r in iso.walk()}
    original=(ROOT/'work/SLUS_207.56').read_bytes();patched=(OUT/'SLUS_207.56').read_bytes()
    changes=json.loads((OUT/'changes.json').read_text('utf8'));relocs={};count=0
    for c in changes:
        if 'korean' not in c:continue
        at=int(c.get('new_address',c['address']),16)-0x107000
        value=encode(c['korean'])+b'\0';assert patched[at:at+len(value)]==value,c
        if 'new_address' in c:relocs[int(c['address'],16)]=int(c['new_address'],16)
        count+=1
    shoff=struct.unpack_from('<I',original,32)[0];shnum=struct.unpack_from('<H',original,48)[0];refs=0
    for si in range(shnum):
        sec=struct.unpack_from('<10I',original,shoff+si*40)
        if sec[1]!=1 or not sec[2]&2 or sec[2]&4:continue
        for off in range(sec[4],sec[4]+sec[5]-3,4):
            old=struct.unpack_from('<I',original,off)[0]
            if old in relocs:
                assert struct.unpack_from('<I',patched,off)[0]==relocs[old];refs+=1
    mapping=json.loads((ROOT/'translation/credits.ko.json').read_text('utf8'));texts=0
    for path in ('DB/DB.VIV','DB/TUNING.VIV'):
        source=dict(big(iso.read(*index[path])));actual=dict(big((OUT/path.replace('/','_')).read_bytes()))
        for n,d in actual.items():
            if n.startswith('credits_'):
                assert d==display_text.credits(source[n],mapping,encode)
                assert all(len(line)<128 for line in d.splitlines());decode(d);texts+=1
            elif n.startswith('online_') and n.endswith('.txt'):
                assert len(d.splitlines())<1500 and max(map(len,d.splitlines()))<60
                assert any('\uac00'<=c<='\ud7a3' for c in decode(d));texts+=1
            elif n.startswith('DraftPlayers'):
                decoded=decode(d)
                for line in decoded.splitlines():
                    if line and not line.startswith('//') and ':' in line:
                        name=line.split(':',1)[1].strip()
                        assert not re.search('[A-Za-z]',name),line
    nested=0
    for path in ('PRELOAD.VIV','FPRELOAD.VIV'):
        for n,d in big((OUT/path).read_bytes()):
            if n.upper() in ('DB/TUNING.VIV','UGI/OVERLAY.VIV','FE/FE_ART.VIV','FE/OV_ART.VIV'):
                assert d==(OUT/n.upper().replace('/','_')).read_bytes(),(path,n);nested+=1
    images=0
    preview=ROOT/'work/audit/art';preview.mkdir(parents=True,exist_ok=True)
    for path in ('FE/FE_ART.VIV','FE/OV_ART.VIV'):
        src=dict(big(iso.read(*index[path])));dst=dict(big((OUT/path.replace('/','_')).read_bytes()))
        for n,d in dst.items():
            if n in art_text.LABELS:
                im=art_audit.decode(d);assert im.size==art_audit.decode(src[n]).size
                assert d!=src[n];im.save(preview/('ko-'+n+'.png'));images+=1
            else:assert d==src[n],n
    result={'elf_texts':count,'relocated_name_pointers':refs,'text_files':texts,'nested_copies':nested,'text_images':images,'glyphs':len(chars)}
    (OUT/'extra-verification.json').write_text(json.dumps(result,indent=2),'utf8')
    print('추가 번역 검증 통과:',result)

if __name__=='__main__':main()
