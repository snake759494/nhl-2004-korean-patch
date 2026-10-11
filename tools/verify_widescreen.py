"""와이드 MIPS 보조 루틴의 투영/클리핑 배율과 복귀 경로 검사."""
from pathlib import Path
import argparse,json,math,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS64,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import UC_MIPS_REG_S0,UC_MIPS_REG_V0,UC_MIPS_REG_F0,UC_MIPS_REG_F1,UC_MIPS_REG_F20
from prepare_widescreen_release import ROOT,WORDS,generate
import iso

def main():
    ap=argparse.ArgumentParser();ap.add_argument('iso',type=Path);args=ap.parse_args()
    path,info=generate(args.iso,update_manifest=False)
    index={n:(l,s) for n,l,s,r in iso.walk(args.iso)}
    d=bytearray(iso.read(*index['SLUS_207.56'],args.iso))
    for a,v in WORDS.items():struct.pack_into('<I',d,a-0x107000,v)
    def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
    samples=[.01,.25,.5,.75,1.,1.333333,2.,4.,8.,100.]
    for value in samples:
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN)
        u.mem_map(0x100000,0x200000);u.mem_write(0x107000,bytes(d[:0x100]))
        u.mem_write(0x12d180,bytes(d[0x12d180-0x107000:0x12d228-0x107000]))
        u.reg_write(UC_MIPS_REG_S0,0x200000);u.reg_write(UC_MIPS_REG_V0,0x200020)
        u.reg_write(UC_MIPS_REG_F1,bits(value));u.mem_write(0x200020,b'\xaa'*16)
        u.emu_start(0x12d188,0x12d190,count=100)
        actual=struct.unpack('<f',u.mem_read(0x200020,4))[0]
        assert math.isclose(actual,value*.75,rel_tol=1e-6)
        assert bytes(u.mem_read(0x200024,12))==bytes(4)+b'\xaa'*8
        u.reg_write(UC_MIPS_REG_F0,bits(value))
        u.emu_start(0x12d218,0x12d220,count=100)
        actual=struct.unpack('<f',struct.pack('<I',u.reg_read(UC_MIPS_REG_F20)))[0]
        assert math.isclose(actual,value*4/3,rel_tol=1e-6)
    result={'crc':info['crc'],'patch':path.name,'mips_cases':len(samples)*2,
            'projection_x':.75,'conservative_culling':4/3,'passed':True}
    (ROOT/'validation/widescreen-static.json').write_text(json.dumps(result,indent=2)+'\n','utf8')
    print('와이드 MIPS 검사 통과:',result)

if __name__=='__main__':main()
