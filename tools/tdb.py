"""EA TDB v8의 고정 길이 문자열 읽기. 수치/참조 필드는 그대로 둔다."""
import struct,json
from pathlib import Path

def tables(d):
    assert d[:5]==b'DB\0\x08\0'
    n=struct.unpack_from('<I',d,16)[0];base=24+n*8
    for i in range(n):
        name=d[24+i*8:28+i*8].decode('ascii');o=base+struct.unpack_from('<I',d,28+i*8)[0]
        size=struct.unpack_from('<I',d,o+8)[0];count=struct.unpack_from('<H',d,o+22)[0];nf=d[o+28]
        fields=[]
        for j in range(nf):
            p=o+40+j*16;typ,bit=struct.unpack_from('<II',d,p);key=d[p+8:p+12].decode('ascii');bits=struct.unpack_from('<I',d,p+12)[0]
            fields.append((key,typ,bit,bits))
        yield name,o,size,count,fields,o+40+nf*16

def strings(d):
    for name,o,size,count,fields,start in tables(d):
        for key,typ,bit,bits in fields:
            if typ!=0:continue
            assert bit%8==bits%8==0
            for row in range(count):
                off=start+row*size+bit//8;width=bits//8
                raw=d[off:off+width].split(b'\0')[0]
                yield name,key,row,off,width,raw.decode('cp1252',errors='replace')

def crc(d):
    c=0xffffffff
    for b in d:
        c^=b<<24
        for _ in range(8):c=((c<<1)^(0x04c11db7 if c&0x80000000 else 0))&0xffffffff
    return c

def patch_names(d,mapping,encode,teams=None,geography=None):
    out=bytearray(d);changed=0
    for table,key,row,off,width,s in strings(d):
        selected=mapping if table=='SPBT' and key in ('FNME','LNME') else teams if (table=='STEA' and key in ('FNME','SNME')) or (table=='SARE' and key in ('NAME','CITY')) else None
        if (table=='SPBT' and key=='CITY') or (table=='SSTT' and key=='NAME'):selected=geography
        if table=='SAWA' and key=='PLAY' and s:
            selected={s:'/'.join(' '.join(mapping[part] for part in full.split()) for full in s.strip().split('/'))}
        if not selected or s not in selected:continue
        value=encode(selected[s]);assert len(value)<width,(s,selected[s],width)
        out[off:off+width]=value+bytes(width-len(value));changed+=1
    ts=list(tables(d))
    # 다음 테이블의 priorCRC는 이전 테이블의 필드 정의와 레코드를 보호한다.
    for i,(_,o,*_) in enumerate(ts):
        end=ts[i+1][1] if i+1<len(ts) else len(d)-4
        before=struct.unpack_from('<I',d,end)[0]
        assert crc(d[o+40:end])==before,('원본 CRC 불일치',hex(o))
        if out[o+40:end]!=d[o+40:end]:struct.pack_into('<I',out,end,crc(out[o+40:end]))
    return bytes(out),changed

if __name__=='__main__':
    out=[]
    for p in Path('work/decoded/DB_DB.VIV').glob('*.tdb'):
        for table,field,row,off,width,s in strings(p.read_bytes()):
            if s:out.append({'file':p.name,'table':table,'field':field,'row':row,'offset':off,'width':width,'source':s})
    Path('translation/database.source.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
    print('문자열 필드',len(out))
    for p in sorted(set((x['file'],x['table'],x['field'],x['width']) for x in out)):
        samples=[x['source'] for x in out if (x['file'],x['table'],x['field'],x['width'])==p]
        print(p,len(samples),samples[:8])
