"""시험 출력 코드/폰트/언어 테이블의 자동 검증."""
import json,struct,re
from pathlib import Path
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS64,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_RA
from formats import big
from texts import entries
import tdb,names

def main():
    root=Path(__file__).resolve().parent.parent
    d=(root/'work/test-build/SLUS_207.56').read_bytes()
    chars=(root/'work/test-build/characters.txt').read_text(encoding='utf8')
    preloaded=dict(big((root/'work/test-build/PRELOAD.VIV').read_bytes()))
    assert preloaded['ugi/ugiall.viv']==(root/'work/test-build/UGI_UGIALL.VIV').read_bytes()
    assert preloaded['FE/local.viv']==(root/'work/test-build/FE_LOCAL.VIV').read_bytes()
    assert preloaded['gamedata/characs.viv']==(root/'work/test-build/GAMEDATA_CHARACS.VIV').read_bytes()
    cases=[(b'ABC',100,'ABC'),(b'ABC',3,'AB'),(b'',1,''),(b'\x81\x80Z',100,chr(1024)+'Z'),(b'\x81',10,chr(129)),(b'\x81\x7f',10,chr(129)+chr(127))]
    cases += [(bytes((0x81+i//128,0x80+i%128)),3,chr(1024+i)) for i in range(len(chars))]
    for source,capacity,expected in cases:
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN);u.mem_map(0x100000,0x100000)
        u.mem_write(0x107054,d[0x54:0x100]);u.mem_write(0x180000,source+b'\0')
        u.reg_write(UC_MIPS_REG_A0,0x181000);u.reg_write(UC_MIPS_REG_A1,0x180000)
        u.reg_write(UC_MIPS_REG_A2,capacity);u.reg_write(UC_MIPS_REG_RA,0x190000)
        u.emu_start(0x107054,0x190000,count=10000)
        actual=bytes(u.mem_read(0x181000,(len(expected)+1)*2))
        assert actual==(expected+'\0').encode('utf-16le'),(source,actual,expected)
    shorts=json.loads((root/'translation/scoreboard.ko.json').read_text(encoding='utf8'))
    short_cases=[(en.encode('ascii'),''.join(chr(1024+chars.index(c)) for c in kr)) for en,kr in shorts.items()]
    short_cases += [(b'', ''),(b'A','A'),(b'ABC','ABC'),(b'ANAX','ANAX'),(b'ANAHEIM','ANAHEIM'),(b'NJX','NJX'),(b'\x81\x80',chr(1024))]
    for source,expected in short_cases:
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN);u.mem_map(0x100000,0x100000)
        u.mem_write(0x107054,d[0x54:0x100]);u.mem_write(0x1f8fc0,d[0xf1fc0:0xf2320])
        u.mem_write(0x180001,source+b'\0');u.mem_write(0x181000,b'\xaa'*128)
        u.reg_write(UC_MIPS_REG_A0,0x181000);u.reg_write(UC_MIPS_REG_A1,0x180001)
        u.reg_write(UC_MIPS_REG_A2,64);u.reg_write(UC_MIPS_REG_RA,0x190000)
        u.emu_start(0x1f9200,0x190000,count=10000)
        raw=(expected+'\0').encode('utf-16le')
        assert bytes(u.mem_read(0x181000,len(raw)+2))==raw+b'\xaa\xaa',(source,expected)
    # 시작/저장 안내문에서 쓰는 UTF-16 -> 2바이트 역변환 검증.
    for i in range(len(chars)):
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN);u.mem_map(0x100000,0x200000)
        u.mem_write(0x1f9100,d[0xf2100:0xf2200]);u.mem_write(0x180000,('A'+chr(1024+i)+'Z\0').encode('utf-16le'))
        u.reg_write(UC_MIPS_REG_A1,0x180000);u.reg_write(UC_MIPS_REG_A2,0x181000);u.reg_write(UC_MIPS_REG_RA,0x190000)
        u.emu_start(0x1f9100,0x190000,count=10000)
        assert bytes(u.mem_read(0x181000,5))==b'A'+bytes((129+i//128,128+i%128))+b'Z\0'
    for name,font in big((root/'work/test-build/FE_FE_FONTS.VIV').read_bytes()):
        count=struct.unpack_from('<H',font,10)[0];ct=struct.unpack_from('<I',font,20)[0]
        codes=[struct.unpack_from('<H',font,ct+i*16)[0] for i in range(count)]
        assert codes==sorted(codes) and len(codes)==len(set(codes)),name
        assert set(range(1024,1024+len(chars)))<=set(codes)
        shape=struct.unpack_from('<I',font,28)[0];w,h=struct.unpack_from('<HH',font,shape+4)
        for i in range(count):
            c,cw,ch,x,y=struct.unpack_from('<HBBHH',font,ct+i*16)
            assert x+cw<=w and y+ch<=h,(name,c)
    ko=json.loads((root/'translation/ko.json').read_text(encoding='utf8'))
    for en,kr in ko.items():
        assert re.findall(r'%[-+0-9.*]*[a-zA-Z]',en)==re.findall(r'%[-+0-9.*]*[a-zA-Z]',kr),(en,kr)
    legacy=big((root/'work/test-build/UGI_UGIALL.VIV').read_bytes())+big((root/'work/test-build/GAMEDATA_CHARACS.VIV').read_bytes())
    for name,font in legacy:
        if font[:4]!=b'FNTS':continue
        count=struct.unpack_from('<H',font,10)[0];ct=struct.unpack_from('<I',font,20)[0]
        codes=[struct.unpack_from('<H',font,ct+i*12)[0] for i in range(count)]
        assert codes==sorted(set(codes)) and set(range(1024,1024+len(chars)))<=set(codes),name
        shape=struct.unpack_from('<I',font,28)[0];w,h=struct.unpack_from('<HH',font,shape+4)
        assert shape%16==0,(name,'텍스처 DMA 정렬',shape)
        palette=shape+int.from_bytes(font[shape+1:shape+4],'little')
        assert palette%16==0,(name,'팔레트 DMA 정렬',palette)
        for i in range(count):
            c,cw,ch,x,y=struct.unpack_from('<HBBHH',font,ct+i*12)
            assert x+cw<=w and y+ch<=h,(name,c)
    mapping=names.load(root);teams=json.loads((root/'translation/teams.ko.json').read_text(encoding='utf8'))
    def encode(s):
        return b''.join(bytes((129+chars.index(c)//128,128+chars.index(c)%128)) if c in chars else c.encode('cp1252') for c in s)
    built=dict(big((root/'work/test-build/DB_DB.VIV').read_bytes()));checked=0
    for name,source in big((root/'work/DB_DB.VIV').read_bytes()):
        if name not in ('nhl2004.tdb','nhl2004PC.tdb'):continue
        target=built[name]
        for table,key,row,off,width,s in tdb.strings(source):
            selected=mapping if table=='SPBT' and key in ('FNME','LNME') else teams if (table=='STEA' and key in ('FNME','SNME')) or (table=='SARE' and key in ('NAME','CITY')) else None
            if selected is None:continue
            if not s:
                assert target[off:off+width]==source[off:off+width]
                continue
            assert s in selected,(name,table,key,row,s)
            assert target[off:off+width].split(b'\0')[0]==encode(selected[s]),(name,table,key,row)
            checked+=1
        ts=list(tdb.tables(target))
        for i,(_,o,*_) in enumerate(ts):
            end=ts[i+1][1] if i+1<len(ts) else len(target)-4
            assert tdb.crc(target[o+40:end])==struct.unpack_from('<I',target,end)[0]
    print('검증 통과: MIPS 변환',len(cases),'건, 메뉴/경기/선수 표시 폰트 11개, 번역 서식 인자',len(ko),'건, 선수/팀/경기장 필드',checked,'건')

if __name__=='__main__':main()
