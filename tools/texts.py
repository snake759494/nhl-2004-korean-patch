"""영문 언어 테이블을 순서와 해시를 보존하여 추출한다."""
from pathlib import Path
import struct,json

def entries(d):
    hashed=d[:4]==b'\xfe'*4
    if hashed:
        n=struct.unpack_from('<I',d,4)[0];base=16+4*n
    else:
        base=0;n=struct.unpack_from('<I',d)[0]//4
    result=[]
    for i in range(n):
        o=struct.unpack_from('<I',d,base+4*i)[0]
        # 포인터는 파일 시작 기준이다.
        assert base+4*n<=o<len(d),(i,o,len(d))
        end=d.index(0,o)
        result.append(d[o:end].decode('cp1252'))
    return result

if __name__=='__main__':
    for p in Path('work/decoded/FE_LOCAL.VIV').glob('*.ENG'):
        e=entries(p.read_bytes())
        Path('translation/'+p.stem+'.source.json').write_text(json.dumps(e,ensure_ascii=False,indent=2),encoding='utf-8')
        print(p.name,len(e),e[:8])
