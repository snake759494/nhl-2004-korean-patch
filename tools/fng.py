"""화면 파일의 St UTF-16 표시 문자열만 고정 크기로 교체한다."""
import re,struct

def strings(d):
    for m in re.finditer(b'St',d):
        o=m.start()
        if o+4>len(d):continue
        size=struct.unpack_from('<H',d,o+2)[0]
        if size<4 or size>8192 or size%2 or o+4+size>len(d):continue
        raw=d[o+4:o+4+size]
        if not raw.endswith(b'\0\0'):continue
        try:s=raw.decode('utf-16le').rstrip('\0')
        except UnicodeDecodeError:continue
        if any(ord(c)<32 and c not in '\r\n\t' for c in s):continue
        yield o+4,size,s

def patch(d,mapping,chars):
    out=bytearray(d);count=0
    for off,size,s in strings(d):
        if s not in mapping:continue
        kr=mapping[s]
        raw=b''.join(struct.pack('<H',1024+chars.index(c) if c in chars else ord(c)) for c in kr)+b'\0\0'
        # 기존 텍스트 명령의 길이와 뒤 명령의 주소를 보존한다.
        if len(raw)>size:continue
        out[off:off+size]=raw+bytes(size-len(raw));count+=1
    return bytes(out),count
