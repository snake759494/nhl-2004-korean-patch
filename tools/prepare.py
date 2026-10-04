"""사용자가 가진 원본에서 추출 자료와 번역 원문 연결을 복원한다."""
from pathlib import Path
import hashlib,json
import iso
from formats import big

ROOT=Path(__file__).resolve().parent.parent

def main():
    source=ROOT/'NHL 2004 (USA).iso'
    h=hashlib.sha256()
    with source.open('rb') as f:
        while block:=f.read(8*1024*1024):h.update(block)
    assert h.hexdigest()=='a4913c644b70802bbafcc310b4d88a89ba42a04d9eed2c6f24c650a7f4dcb7b4','원본 ISO SHA-256 불일치'
    index={p:(l,s) for p,l,s,r in iso.walk(source)};cache={}
    def resource(path):
        if path in cache:return cache[path]
        if '::' in path:
            parent,name=path.rsplit('::',1);data=dict(big(resource(parent)))[name]
        else:data=iso.read(*index[path],source)
        cache[path]=data;return data
    work=ROOT/'work';work.mkdir(exist_ok=True)
    for path in ['SLUS_207.56','FE/LOCAL.VIV','FE/FE_FONTS.VIV','UGI/UGIALL.VIV','PRELOAD.VIV','DB/DB.VIV']:
        (work/path.replace('/','_')).write_bytes(resource(path))
    tr=ROOT/'translation'
    located=json.loads((tr/'located.json').read_text('utf8'))
    extra=json.loads((tr/'short_keys.json').read_text('utf8'))
    for filename,records in located.items():
        mapping={}
        for item in records:
            if 'key' in item:key=item['key']
            else:
                d=resource(item['resource']);at=item['offset']
                key=d[at:at+item['length']].decode(item['encoding'])
            assert key not in mapping or mapping[key]==item['korean']
            mapping[key]=item['korean']
        mapping.update(extra.get(filename,{}))
        (tr/filename).write_text(json.dumps(mapping,ensure_ascii=False,indent=2),'utf8')
    d=resource('SLUS_207.56');mapping={}
    for address,korean in json.loads((tr/'elf_offsets.korean.json').read_text('utf8')).items():
        at=int(address,16)
        mapping[address]={'source':d[at:d.index(0,at)].decode('cp1252'),'korean':korean}
    (tr/'elf_offsets.ko.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),'utf8')
    print('원본 해시 및 번역 자료 복원 완료')

if __name__=='__main__':main()
