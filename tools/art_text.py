"""문자 전용 텍스처를 프로젝트 글꼴로 생성한다. 크기/팔레트/해시를 보존한다."""
import struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
from formats import big,pack,pack_big

LABELS={'FIGHT_CONFIRM_ENG':'싸워라!', 'FIGHT_ENG':'싸움',
        'Hockey_News_Title':'파워플레이'}

def glyph_texture(d,text,fontpath):
    o=struct.unpack_from('<I',d,20)[0]
    kind=d[o];w,h=struct.unpack_from('<HH',d,o+4)
    assert kind in (1,2)
    ps=o+int.from_bytes(d[o+1:o+4],'little');count=16 if kind==1 else 256
    pal=np.frombuffer(d[ps+16:ps+16+count*4],np.uint8).reshape(count,4).copy()
    if kind==2:
        for z in range(0,256,32):pal[z+8:z+24]=pal[z+8:z+24].reshape(2,8,4)[::-1].reshape(16,4)
    pal[:,3]=np.minimum(pal[:,3].astype(int)*2,255)
    scale=4;stroke=max(1,h//32)
    for size in range(max(8,h-2*stroke),3,-1):
        font=ImageFont.truetype(str(fontpath),size*scale)
        box=font.getbbox(text,stroke_width=stroke*scale)
        if box[2]-box[0]<=(w-2)*scale and box[3]-box[1]<=(h-2)*scale:break
    canvas=Image.new('RGBA',(w*scale,h*scale))
    draw=ImageDraw.Draw(canvas)
    color=(240,240,240,255) if text=='파워플레이' else (255,230,40,255)
    draw.text(((w*scale-box[2]+box[0])//2-box[0],(h*scale-box[3]+box[1])//2-box[1]),text,font=font,fill=color,stroke_width=stroke*scale,stroke_fill=(0,0,0,255))
    im=canvas.resize((w,h),Image.Resampling.LANCZOS)
    # 알파를 포함한 색상 거리. 투명색의 RGB는 표시되지 않는다.
    a=np.asarray(im).astype(np.float32).reshape(-1,4);p=pal.astype(np.float32)
    a[:,:3]*=a[:,3:4]/255;p[:,:3]*=p[:,3:4]/255
    indices=np.empty(w*h,np.uint8)
    for i in range(0,len(a),1024):indices[i:i+1024]=((a[i:i+1024,None]-p[None])**2).sum(2).argmin(1)
    raw=indices.tobytes() if kind==2 else (indices[::2]|indices[1::2]<<4).tobytes()
    assert len(raw)<=ps-o-16
    result=bytearray(d);result[o+16:o+16+len(raw)]=raw
    assert len(result)==len(d) and result[ps:]==d[ps:]
    return bytes(result)

def archive(d,fontpath):
    items=big(d);changes=0;values=[]
    for name,data in items:
        new=data
        if name in LABELS:
            new=glyph_texture(data,LABELS[name],fontpath);changes+=1
        values.append((name,new))
    if not changes:return d,0
    n=len(items);table=struct.unpack_from('>I',d,12)[0]
    if table==16+80*n:
        out=bytearray(d[:table]);out+=bytes(-len(out)%128)
        for i,((name,new),(_,old)) in enumerate(zip(values,items)):
            off,size=struct.unpack_from('>II',d,16+80*i)
            payload=d[off:off+size] if new==old else pack(new) if d[off:off+2]==b'\x10\xfb' else new
            struct.pack_into('>II',out,16+80*i,len(out),len(payload))
            out+=payload;out+=bytes(-len(out)%128)
        struct.pack_into('>I',out,4,len(out));result=bytes(out)
        for i in range(n):assert result[28+80*i:96+80*i]==d[28+80*i:96+80*i]
    else:result=pack_big(values)
    assert big(result)==values
    return result,changes
