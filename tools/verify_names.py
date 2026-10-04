"""실제 명단 전체와 경계값에 대해 R5900 이름 조합 코드를 실행한다."""
from pathlib import Path
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS64,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from formats import big
import tdb

def main():
    root=Path(__file__).resolve().parent.parent
    d=(root/'work/test-build/SLUS_207.56').read_bytes()
    db=dict(big((root/'work/test-build/DB_DB.VIV').read_bytes()))['nhl2004.tdb']
    rows={}
    for table,key,row,off,width,s in tdb.strings(db):
        if table=='SPBT' and key in ('FNME','LNME'):
            rows.setdefault(row,{})[key]=db[off:off+width].split(b'\0')[0]
    cases=[(r['FNME'],r['LNME']) for r in rows.values()]
    cases += [(b'',b''),(b'A',b'B'*40),(b'',b'\x81\x80'*12),
              (b'\x81\x80'*7,b'\x81\x81'*7),(b'J',b'User'),(b'A',b'B'*17)]
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0x100000,0x200000);u.mem_write(0x107000,d[:0x180000])
    u.mem_write(0x2b7960,d[0x2b7960-0x107000:0x2b7a04-0x107000])
    u.mem_map(0x400000,0x100000)
    u.mem_write(0x40ce48,d[0x40ce48-0x107000:0x40cfd0-0x107000])
    u.mem_map(0x500000,0x100000)
    u.mem_write(0x56e288,d[0x56e288-0x107000:0x56e288-0x107000+128])
    xlat_table=dict(zip(d[0x56e288-0x107000:0x56e288-0x107000+53],d[0x56e2c0-0x107000:0x56e2c0-0x107000+53]))
    # 모든 명단과 2바이트 코드에서 경기 대문자화가 한글을 보존하는지 검사.
    upper_cases=[s for pair in cases for s in pair]
    upper_cases += [bytes((lead,trail)) for lead in range(129,144) for trail in range(128,256)]
    upper_cases += [b'abc XYZ MacLe 123',bytes(range(128,256))]
    for source in upper_cases:
        u.mem_write(0x280001,source+b'\0\xaa')
        u.reg_write(UC_MIPS_REG_A0,0x280001);u.reg_write(UC_MIPS_REG_RA,0x290000)
        u.emu_start(0x40ce48,0x290000,count=10000)
        assert bytes(u.mem_read(0x280001,len(source)+2))==source.upper()+b'\0\xaa',source
    xlat_cases=upper_cases+[bytes((v,)) for v in range(1,256)]
    for source in xlat_cases:
        expected=bytearray();i=0
        while i<len(source):
            if 129<=source[i]<=143 and i+1<len(source) and source[i+1]>=128:
                expected+=source[i:i+2];i+=2
            else:expected.append(xlat_table.get(source[i],source[i]));i+=1
        u.mem_write(0x280001,source+b'\0\xaa');u.reg_write(UC_MIPS_REG_A0,0x280001);u.reg_write(UC_MIPS_REG_RA,0x290000)
        u.emu_start(0x2b7960,0x290000,count=100000)
        assert bytes(u.mem_read(0x280001,len(source)+2))==bytes(expected)+b'\0\xaa',source
    def units(s):
        result=[];i=0
        while i<len(s):
            n=2 if 0x81<=s[i]<=0x8f else 1
            if i+n>len(s):break
            result.append(s[i:i+n]);i+=n
        return result
    for first,last in cases:
        prefix=first if len(first)+len(last)<19 else b''.join(units(first)[:1])
        expected=prefix+(b' ' if prefix and last else b'')
        for char in units(last):
            if len(expected)+len(char)>19:break
            expected+=char
        for wide in (False,True):
            u.mem_write(0x280001,first+b'\0');u.mem_write(0x281001,last+b'\0')
            u.mem_write(0x282000,b'\xaa'*128)
            for r,v in [(UC_MIPS_REG_A0,0x282002),(UC_MIPS_REG_A2,0x280001),
                        (UC_MIPS_REG_A3,0x281001),(UC_MIPS_REG_RA,0x290000),(UC_MIPS_REG_SP,0x2f0000)]:
                u.reg_write(r,v)
            u.emu_start(0x1f9940 if wide else 0x1f99a0,0x290000,count=10000)
            raw=expected+b'\0'
            if wide:
                out=''.join(chr(0x400+(c[0]-129)*128+c[1]-128) if len(c)==2 else chr(c[0]) for c in units(expected))
                raw=(out+'\0').encode('utf-16le')
            assert bytes(u.mem_read(0x282000,len(raw)+4))==b'\xaa\xaa'+raw+b'\xaa\xaa',(first,last,wide)
            assert u.reg_read(UC_MIPS_REG_V0)==len(expected)
    print('선수 이름 조합 및 경계 보호 검증:',len(cases),'사례 × 8비트/16비트 경로 통과')
    print('경기 이름 대문자화 한글 보존 검증:',len(upper_cases),'사례 통과')
    print('경기 표시 이름 악센트 변환 검증:',len(xlat_cases),'사례 통과')

if __name__=='__main__':main()
