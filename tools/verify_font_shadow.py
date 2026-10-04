"""원본 영문 보존 및 한글 본체/그림자 팔레트 검증, 확대 비교 이미지."""
from pathlib import Path
import struct
import numpy as np
from PIL import Image,ImageDraw
from formats import big

def read(d):
    ct=struct.unpack_from('<I',d,20)[0];shape=struct.unpack_from('<I',d,28)[0]
    ns=struct.unpack_from('<I',d,48)[0];p=ns+struct.unpack_from('<I',d,ns+4)[0]
    p+=struct.unpack_from('<I',d,p+8)[0]
    pal=np.frombuffer(d[p:p+1024],np.uint8).reshape(256,4).copy()
    for b in range(0,256,32):pal[b+8:b+24]=pal[b+8:b+24].reshape(2,8,4)[::-1].reshape(16,4)
    w,h=struct.unpack_from('<HH',d,shape+4)
    pixels=np.frombuffer(d[shape+16:shape+16+w*h],np.uint8).reshape(h,w)
    glyphs={}
    for i in range(struct.unpack_from('<H',d,10)[0]):
        code,cw,ch,x,y=struct.unpack_from('<HBBHH',d,ct+i*16)
        glyphs[code]=pal[pixels[y:y+ch,x:x+cw]]
    return glyphs

root=Path(__file__).resolve().parent.parent
original=dict(big((root/'work/FE_FE_FONTS.VIV').read_bytes()))
built=dict(big((root/'work/test-build/FE_FE_FONTS.VIV').read_bytes()))
chars=(root/'work/test-build/characters.txt').read_text(encoding='utf8')
sheet=Image.new('RGB',(820,6*145),(130,140,150));draw=ImageDraw.Draw(sheet)
for row,(name,d) in enumerate(original.items()):
    src=read(d);dst=read(built[name])
    for code,g in src.items():assert np.array_equal(g,dst[code]),(name,code,'원본 변경')
    draw.text((8,row*145+4),name,fill='white')
    x=8
    for code in [ord('A'),ord('M')]+[1024+chars.index(c) for c in '한글선수']:
        g=dst[code];valid=g[:,:,3]>g[:,:,3].max()*.1
        if code>=1024:
            luminance=g[:,:,:3].mean(2)
            assert np.any(valid & (luminance<80)) and np.any(valid & (luminance>200)),(name,code)
        tile=Image.fromarray(g,'RGBA').resize((g.shape[1]*4,g.shape[0]*4),Image.Resampling.NEAREST)
        sheet.paste(tile,(x,row*145+25),tile);x+=tile.width+12
sheet.save(root/'work/font-shadow-comparison.png')
print('6개 글꼴: 원본 글리프 보존 및 한글 본체/그림자 검증 통과')
