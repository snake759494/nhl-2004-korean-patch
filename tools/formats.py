"""NHL 2004 자료 조사: BIGF, RefPack."""
import struct

def unpack(d):
    if d[:2] != b'\x10\xfb': return d
    size=int.from_bytes(d[2:5],'big'); p=5; out=bytearray()
    while True:
        c=d[p];p+=1
        if c>=0xfc:
            out+=d[p:p+(c&3)];break
        if c>=0xe0:
            n=((c&31)+1)*4;out+=d[p:p+n];p+=n;continue
        if c>=0xc0:
            a,b,e=d[p:p+3];p+=3
            lit=c&3;count=((c&12)<<6)+e+5;dist=((c&16)<<12)+(a<<8)+b+1
        elif c>=0x80:
            a,b=d[p:p+2];p+=2
            lit=a>>6;count=(c&63)+4;dist=((a&63)<<8)+b+1
        else:
            a=d[p];p+=1
            lit=c&3;count=((c&28)>>2)+3;dist=((c&96)<<3)+a+1
        out+=d[p:p+lit];p+=lit
        for _ in range(count): out.append(out[-dist])
    assert len(out)==size,(len(out),size)
    return bytes(out)

def big(d):
    assert d[:4]==b'BIGF'
    n=struct.unpack_from('>I',d,8)[0];p=16;out=[]
    if struct.unpack_from('>I',d,12)[0]==16+80*n:
        for i in range(n):
            p=16+80*i;off,size=struct.unpack_from('>II',d,p)
            name=d[p+12:p+80].split(b'\0')[0].decode('ascii')
            out.append((name,unpack(d[off:off+size])))
        return out
    for _ in range(n):
        off,size=struct.unpack_from('>II',d,p);end=d.index(0,p+8)
        name=d[p+8:end].decode('ascii');p=end+1
        out.append((name,unpack(d[off:off+size])))
    return out

def pack_literal(d):
    out=bytearray(b'\x10\xfb'+len(d).to_bytes(3,'big'));p=0
    while len(d)-p>=4:
        n=min(112,(len(d)-p)//4*4);out.append(0xe0+n//4-1);out+=d[p:p+n];p+=n
    out.append(0xfc+len(d)-p);out+=d[p:]
    assert unpack(out)==d
    return bytes(out)

def pack(d):
    """RefPack LZ 토큰 생성. 압축 해제 왕복을 매번 확인한다."""
    out=bytearray(b'\x10\xfb'+len(d).to_bytes(3,'big'));history={};p=0;start=0
    def add(pos):
        key=d[pos:pos+3]
        if len(key)<3:return
        h=history.setdefault(key,[]);h.append(pos)
        if len(h)>32:del h[:16]
    def literals(end):
        nonlocal start
        while end-start>=4:
            n=min(112,(end-start)//4*4);out.append(0xe0+n//4-1);out.extend(d[start:start+n]);start+=n
    while p<len(d):
        best=0;dist=0
        for q in reversed(history.get(d[p:p+3],[])):
            gap=p-q
            if gap>131072:break
            limit=min(1028,len(d)-p);n=3
            if best>=limit:break
            if best>=3 and d[q+best]!=d[p+best]:continue
            while n<limit and d[q+n]==d[p+n]:n+=1
            if n>best and (n>=5 or n>=4 and gap<=16384 or gap<=1024):best=n;dist=gap
        if best<3:add(p);p+=1;continue
        literals(p);lit=p-start;gap=dist-1
        if best<=10 and dist<=1024:
            out.extend(((gap>>8)<<5|(best-3)<<2|lit,gap&255))
        elif best<=67 and dist<=16384:
            out.extend((0x80|best-4,lit<<6|gap>>8,gap&255))
        else:
            out.extend((0xc0|(gap>>16)<<4|((best-5)>>8)<<2|lit,(gap>>8)&255,gap&255,(best-5)&255))
        out.extend(d[start:p])
        for k in range(p,p+best):add(k)
        p+=best;start=p
    literals(len(d));out.append(0xfc+len(d)-start);out.extend(d[start:])
    assert unpack(out)==d
    return bytes(out)

def pack_big(entries,align=128,compressed=True):
    table_size=16+sum(9+len(n.encode('ascii')) for n,d in entries)
    out=bytearray((table_size+align-1)//align*align);table=bytearray()
    for name,d in entries:
        if compressed:d=pack(d)
        table+=struct.pack('>II',len(out),len(d))+name.encode('ascii')+b'\0'
        out+=d;out+=bytes((-len(out))%align)
    out[:16]=b'BIGF'+struct.pack('>III',len(out),len(entries),table_size)
    out[16:16+len(table)]=table
    return bytes(out)

if __name__=='__main__':
    from pathlib import Path
    for f in Path('work').glob('*.VIV'):
        for name,d in big(f.read_bytes()):
            out=Path('work/decoded')/f.name/name
            out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(d)
            print(f.name,name,len(d),d[:40].hex())
