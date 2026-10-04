"""표시용 일반 텍스트. 파서 태그와 줄 단위 버퍼 제한을 보존한다."""
import re

def wrap(text,encode,limit):
    lines=[];line=''
    for word in text.split(' '):
        candidate=(line+' '+word).strip()
        if len(encode(candidate))<=limit:
            line=candidate;continue
        if line:lines.append(line);line=''
        for c in word:
            if len(encode(line+c))>limit:lines.append(line);line=''
            line+=c
    if line:lines.append(line)
    return lines or ['']

def credits(d,mapping,encode):
    lines=[]
    for line in d.decode('cp1252').splitlines():
        m=re.fullmatch(r'\s*(<[TPCH]>)(.*?)\s*',line)
        if not m or not m[2].strip():lines.append(line);continue
        text=m[2].strip();assert text in mapping,text
        kr=mapping[text]
        # 탭으로 좌우 열을 나누는 C 태그는 한 레코드로 유지한다.
        if m[1]=='<C>':lines.append(m[1]+kr)
        else:lines.extend(m[1]+s for s in wrap(kr,encode,64))
    assert all(len(encode(s))<128 for s in lines)
    return encode('\r\n'.join(lines)+'\r\n')

def agreement(text,encode):
    # PKOnlineAgreement는 한 줄당 60바이트, 총 1500줄을 저장한다.
    lines=[s for paragraph in text.splitlines() for s in wrap(paragraph,encode,52)]
    assert len(lines)<1500 and all(len(encode(s))<60 for s in lines)
    return encode('\r\n'.join(lines)+'\r\n')
