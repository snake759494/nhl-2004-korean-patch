"""시험 빌드: DUMMY.PAD 공간 일부에 확장 파일 배치, ISO9660/UDF 동시 수정."""
from pathlib import Path
import struct,shutil,json,sys
import iso

def crc16(data):
    crc=0
    for b in data:
        crc^=b<<8
        for _ in range(8):crc=((crc<<1)^0x1021 if crc&0x8000 else crc<<1)&65535
    return crc

def main():
    root=Path(__file__).resolve().parent.parent
    src=root/'NHL 2004 (USA).iso';dst=root/'NHL 2004 (USA) (Korean TEST).iso'
    if len(sys.argv)>1:dst=root/sys.argv[1]
    index={p:(l,s,r) for p,l,s,r in iso.walk(src)}
    manifest=json.loads((root/'work/test-build/manifest.json').read_text(encoding='utf8'))
    updates={n:(root/'work/test-build'/n.replace('/','_')).read_bytes() for n in manifest}
    prefix=iso.read(0,568*2048,src)
    part=struct.unpack_from('<I',prefix,34*2048+188)[0]
    assert part==284
    mapping={};cursor=index['DUMMY.PAD'][0]
    for name,data in updates.items():
        old,size,rec=index[name]
        lba=old if len(data)<=size else cursor
        if lba==cursor:cursor+=(len(data)+2047)//2048
        mapping[name]=(lba,len(data))
    dl,ds,_=index['DUMMY.PAD'];used=(cursor-dl)*2048
    assert 0<used<ds
    mapping['DUMMY.PAD']=(cursor,ds-used)
    if not dst.exists():shutil.copyfile(src,dst)
    assert dst.stat().st_size==src.stat().st_size
    with dst.open('r+b') as f:
        # 재실행 시 파일 디렉터리는 원본 기준으로 복원한다.
        f.seek(0);f.write(prefix)
        for name,(lba,size) in mapping.items():
            old,oldsize,rec=index[name]
            f.seek(rec+2);f.write(struct.pack('<I',lba)+struct.pack('>I',lba)+struct.pack('<I',size)+struct.pack('>I',size))
            matches=[]
            for sector in range(309,567):
                e=bytearray(prefix[sector*2048:(sector+1)*2048])
                if struct.unpack_from('<H',e)[0]!=261:continue
                lea,lad=struct.unpack_from('<II',e,168);off=176+lea
                if lad<8 or struct.unpack_from('<I',e,off+4)[0]+part!=old:continue
                ads=bytearray();remaining=size;position=lba-part
                while remaining:
                    chunk=min(remaining,0x3ffff800);ads+=struct.pack('<II',chunk,position)
                    remaining-=chunk;position+=chunk//2048
                e[off:off+max(lad,len(ads))]=bytes(max(lad,len(ads)));e[off:off+len(ads)]=ads
                struct.pack_into('<I',e,172,len(ads));struct.pack_into('<QQ',e,56,size,(size+2047)//2048)
                bodylen=off+len(ads)-16;struct.pack_into('<HH',e,8,crc16(e[16:16+bodylen]),bodylen)
                e[4]=sum(e[i] for i in range(16) if i!=4)&255
                f.seek(sector*2048);f.write(e);matches.append(sector)
            assert len(matches)==1,(name,matches)
            if name in updates:f.seek(lba*2048);f.write(updates[name])
    for name,data in updates.items():
        l,s,r={p:(l,s,r) for p,l,s,r in iso.walk(dst)}[name]
        assert iso.read(l,s,dst)==data
    (root/'work/test-build/iso-map.json').write_text(json.dumps(mapping,indent=2))
    print('시험 ISO 구성 및 재추출 일치:',dst)

if __name__=='__main__':main()
