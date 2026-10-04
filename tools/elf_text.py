"""검토한 화면 표시용 실행 파일 문자열만 제자리 교체한다."""
import struct

NAME_REGIONS=[(0x4bd7c8,0x4bd948),(0x4bda10,0x4bdc50),(0x4be3a0,0x4be5a0),(0x4bfc08,0x4c0318),(0x4fde58,0x4fe040)]
def patch(d,mapping,encode,offsets=None):
    out=bytearray(d);changes=[]
    for en,kr in mapping.items():
        source=en.encode('cp1252')+b'\0';value=encode(kr)+b'\0';pos=0;found=0
        while True:
            i=d.find(source,pos)
            if i<0:break
            pos=i+len(source)
            if i and d[i-1]!=0:continue
            limit=(i+len(source)+7)//8*8
            assert not any(d[i+len(source):limit]),(en,hex(i))
            assert len(value)<=limit-i,(en,kr,len(value),limit-i)
            out[i:limit]=value+bytes(limit-i-len(value));found+=1
            changes.append({'address':hex(i+0x107000),'source':en,'korean':kr})
        assert found,en
    relocations={}
    for lo,hi in NAME_REGIONS:
        selected=sorted((int(address,16),item) for address,item in (offsets or {}).items() if lo<=int(address,16)<hi)
        if not selected:continue
        packed=bytearray()
        for i,item in selected:
            en=item['source'];kr=item['korean'];source=en.encode('cp1252')+b'\0'
            assert d[i:i+len(source)]==source
            new=lo+len(packed)
            relocations[i+0x107000]=new+0x107000
            packed+=encode(kr)+b'\0';packed+=bytes(-len(packed)%2)
            changes.append({'address':hex(i+0x107000),'new_address':hex(new+0x107000),'source':en,'korean':kr})
        assert len(packed)<=hi-lo,(hex(lo),len(packed),hi-lo)
        out[lo:hi]=packed+bytes(hi-lo-len(packed))
    # 이름은 포인터 목록으로 참조된다. 실행 명령이 아닌 적재 데이터만 갱신한다.
    shoff=struct.unpack_from('<I',d,32)[0];shnum=struct.unpack_from('<H',d,48)[0]
    refs={old:0 for old in relocations}
    for si in range(shnum):
        sec=struct.unpack_from('<10I',d,shoff+si*40)
        if sec[1]!=1 or not sec[2]&2 or sec[2]&4:continue
        for off in range(sec[4],sec[4]+sec[5]-3,4):
            old=struct.unpack_from('<I',d,off)[0]
            if old not in relocations:continue
            assert not any(lo<=off<hi for lo,hi in NAME_REGIONS)
            struct.pack_into('<I',out,off,relocations[old]);refs[old]+=1
    assert all(refs.values()),[hex(old) for old,count in refs.items() if not count]
    for address,item in (offsets or {}).items():
        i=int(address,16);en=item['source'];kr=item['korean']
        if i+0x107000 in relocations:continue
        source=en.encode('cp1252')+b'\0';value=encode(kr)+b'\0'
        assert d[i:i+len(source)]==source,(address,en)
        limit=(i+len(source)+7)//8*8
        assert not any(d[i+len(source):limit]),(address,en)
        assert len(value)<=limit-i,(address,en,kr,len(value),limit-i)
        assert out[i:limit]==d[i:limit],('중복 교체',address,en)
        out[i:limit]=value+bytes(limit-i-len(value))
        changes.append({'address':hex(i+0x107000),'source':en,'korean':kr})
    return bytes(out),changes
