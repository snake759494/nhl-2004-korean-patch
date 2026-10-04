"""표시용 이미지의 원본 팔레트를 해석해 목록과 검토용 시트를 만든다."""
import struct,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import iso
from formats import big
ROOT=Path(__file__).resolve().parent.parent

def decode(d):
    assert d[:4]==b'SHPS'
    o=struct.unpack_from('<I',d,20)[0];kind=d[o];w,h=struct.unpack_from('<HH',d,o+4)
    assert kind in (1,2),kind
    ps=o+int.from_bytes(d[o+1:o+4],'little');colors=16 if kind==1 else 256
    pal=np.frombuffer(d[ps+16:ps+16+colors*4],np.uint8).reshape(colors,4).copy()
    if kind==2:
        for z in range(0,256,32):pal[z+8:z+24]=pal[z+8:z+24].reshape(2,8,4)[::-1].reshape(16,4)
    pal[:,3]=np.minimum(pal[:,3].astype(int)*2,255)
    raw=np.frombuffer(d[o+16:ps],np.uint8)
    if kind==1:
        pix=np.empty(w*h,np.uint8);pix[::2]=raw&15;pix[1::2]=raw>>4
    else:pix=raw[:w*h]
    return Image.fromarray(pal[pix.reshape(h,w)])

def main():
    out=ROOT/'work/audit/art';out.mkdir(parents=True,exist_ok=True)
    idx={p:(l,s) for p,l,s,r in iso.walk()};items=[]
    for path in ['FE/BOOT_ART.VIV','FE/FE_ART.VIV','FE/OV_ART.VIV','FE/ART.VIV','FE/FR_ART.VIV','FE/CP_ART.VIV']:
        for n,d in big(iso.read(*idx[path])):
            if n.startswith('LOGO_') or d[:4]!=b'SHPS':continue
            try:im=decode(d)
            except (AssertionError,ValueError):continue
            i=len(items);items.append((path,n));im.save(out/f'{i:03}.png')
    for start in range(0,len(items),48):
        sheet=Image.new('RGB',(1000,8*115),'#777777');dr=ImageDraw.Draw(sheet)
        for i in range(start,min(start+48,len(items))):
            im=Image.open(out/f'{i:03}.png');im.thumbnail((160,88));x=(i-start)%6*166;y=(i-start)//6*115
            sheet.paste(im,(x,y+23),im);dr.text((x,y),f'{i} {items[i][1][:22]}',fill='white')
        sheet.save(out/f'sheet-{start//48}.png')
    (out/'index.json').write_text(json.dumps(items,indent=1),'utf8');print('이미지',len(items))
if __name__=='__main__':main()
