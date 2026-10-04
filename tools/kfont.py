"""메뉴 SFN에 글리프 추가. 기존 영문/기호와 커닝은 보존한다."""
import struct,math
import numpy as np
from PIL import Image,ImageFont,ImageDraw,ImageFilter

def shadow_glyph(c,font,size,palette,foreground):
    """원본 메뉴 글꼴: 반경 1px 외곽선을 우하단 1px 이동한 그림자."""
    box=font.getbbox(c)
    ink=Image.new('L',(max(1,box[2]-box[0]),max(1,box[3]-box[1])))
    ImageDraw.Draw(ink).text((-box[0],-box[1]),c,font=font,fill=255)
    room=size-2
    if ink.width>room or ink.height>room:
        scale=min(room/ink.width,room/ink.height)
        ink=ink.resize((max(1,round(ink.width*scale)),max(1,round(ink.height*scale))),Image.Resampling.LANCZOS)
    mask=Image.new('L',(size,size));mask.paste(ink,((room-ink.width)//2,0))
    outline=mask.filter(ImageFilter.MaxFilter(3))
    shadow=Image.new('L',(size,size));shadow.paste(outline,(1,1))
    a=np.asarray(mask,dtype=float)/255;back=np.asarray(shadow,dtype=float)/255
    alpha=a+back*(1-a)
    color=np.divide(foreground*a+(255-foreground)*back*(1-a),alpha,out=np.zeros_like(alpha),where=alpha>0)
    rgba=np.stack((color,color,color,alpha*int(palette[:,3].max())),axis=-1)
    # 팔레트는 원본 그대로 사용하고 RGB와 투명도를 모두 맞춘다.
    cost=((rgba[:,:,None,:]-palette[None,None,:,:].astype(float))**2*np.array([1,1,1,6])).sum(axis=-1)
    return Image.fromarray(cost.argmin(axis=-1).astype(np.uint8))

def build_legacy(d,chars,font_path):
    assert d[:4]==b'FNTS' and struct.unpack_from('<H',d,8)[0]==355
    n=struct.unpack_from('<H',d,10)[0];ct,kern,shape=struct.unpack_from('<III',d,20)
    assert ct==128 and not struct.unpack_from('<I',d,12)[0]&0x40000
    w,h=struct.unpack_from('<HH',d,shape+4);kind=d[shape];assert kind in (1,2)
    bsize=int.from_bytes(d[shape+1:shape+4],'little');paloff=shape+bsize
    raw=np.frombuffer(d[shape+16:paloff],dtype=np.uint8)
    if kind==1:
        pixels=np.empty(w*h,dtype=np.uint8);pixels[0::2]=raw&15;pixels[1::2]=raw>>4
    else:pixels=raw
    assert len(pixels)==w*h
    pal=np.frombuffer(d[paloff+16:paloff+16+(64 if kind==1 else 1024)],dtype=np.uint8).reshape(-1,4).copy()
    if kind==2:
        for b in range(0,256,32):pal[b+8:b+24]=pal[b+8:b+24].reshape(2,8,4)[::-1].reshape(16,4)
    lookup=[int(np.abs(pal[:,3].astype(int)-a).argmin()) for a in range(256)]
    a=d[ct+(65-32)*12:ct+(66-32)*12];size=max(12,a[3]);cell=size+2
    tw=max(w,512);th=256
    while (tw//cell)*((th-h)//cell)<len(chars):
        if th<1024:th*=2
        elif tw<1024:tw*=2
        else:raise ValueError('경기 폰트 텍스처 용량 초과')
    atlas=Image.new('L',(tw,th),0);atlas.paste(Image.frombytes('L',(w,h),pixels.tobytes()),(0,0))
    font=ImageFont.truetype(str(font_path),size);records=bytearray()
    for i,c in enumerate(chars):
        x=i%(tw//cell)*cell;y=h+i//(tw//cell)*cell
        g=Image.new('L',(size,size));dr=ImageDraw.Draw(g);box=font.getbbox(c)
        dr.text(((size-box[2]+box[0])//2-box[0],-box[1]),c,font=font,fill=255);atlas.paste(g.point(lookup),(x,y))
        records+=struct.pack('<HBBHHbbbB',1024+i,size,size,x,y,size,0,struct.unpack_from('<b',a,10)[0],0)
    # PS2 텍스처 업로드의 DMA 단위는 16바이트다. 12바이트 글리프를
    # 늘릴 때 커닝/이미지 시작 주소의 원본 정렬을 함께 보존한다.
    records+=bytes(-len(records)%16)
    delta=len(records);head=bytearray(d[:ct]);struct.pack_into('<H',head,10,n+len(chars))
    for o in (24,28):struct.pack_into('<I',head,o,struct.unpack_from('<I',head,o)[0]+delta)
    struct.pack_into('<ff',head,64,1/tw,1/th)
    image=np.frombuffer(atlas.tobytes(),dtype=np.uint8)
    if kind==1:image=image[0::2]|image[1::2]<<4
    sh=bytearray(d[shape:shape+16]);sh[1:4]=(16+len(image)).to_bytes(3,'little');struct.pack_into('<HH',sh,4,tw,th)
    out=head+d[ct:ct+n*12]+records+d[ct+n*12:shape]+sh+image.tobytes()+d[paloff:]
    struct.pack_into('<I',out,4,len(out));return bytes(out),atlas

def build(d,chars,font_path):
    assert d[:4]==b'FntS'
    n=struct.unpack_from('<H',d,10)[0]
    ct,kern,shape=struct.unpack_from('<III',d,20)
    newshape=struct.unpack_from('<I',d,48)[0]
    assert newshape+32==shape and ct==128
    assert struct.unpack_from('<I',d,12)[0]&0x40000
    w,h=struct.unpack_from('<HH',d,shape+4)
    assert d[shape]==2
    pix=d[shape+16:shape+16+w*h]
    assert len(pix)==w*h
    palette_start=newshape+struct.unpack_from('<I',d,newshape+4)[0]
    palette_data_offset=struct.unpack_from('<I',d,palette_start+8)[0]
    rawpal=np.frombuffer(d[palette_start+palette_data_offset:palette_start+palette_data_offset+1024],dtype=np.uint8).reshape(256,4)
    # PS2 CLUT의 8~15/16~23 순서를 복원.
    pal=rawpal.copy()
    for b in range(0,256,32):pal[b+8:b+16]=rawpal[b+16:b+24];pal[b+16:b+24]=rawpal[b+8:b+16]
    lookup=[]
    for alpha in range(256):
        target=np.array([255,255,255,alpha])
        cost=((pal.astype(float)-target)**2*np.array([1,1,1,6])).sum(axis=1)
        if alpha==0:cost=pal[:,3].astype(float)
        lookup.append(int(cost.argmin()))
    aentry=d[ct+(65-32)*16:ct+(66-32)*16]
    # A의 맨 위 획으로 흰 본체/검은 그림자와 반대 조합을 구별한다.
    aw,ah,ax,ay=struct.unpack_from('<BBHH',aentry,2)
    original_pixels=np.frombuffer(pix,dtype=np.uint8).reshape(h,w)
    top=pal[original_pixels[ay,ax:ax+aw]]
    solid=top[top[:,3]>=max(1,int(top[:,3].max())*.8)]
    foreground=255 if np.median(solid[:,:3])>=128 else 0
    cap=aentry[3];yoff=struct.unpack_from('<b',aentry,10)[0]
    size=max(12,cap);cell=size+2
    # 원본 아틀라스의 빈 아래쪽을 재사용한다. 기존 글리프 좌표는 유지한다.
    used_h=max(struct.unpack_from('<H',d,ct+i*16+6)[0]+d[ct+i*16+3] for i in range(n))+2
    tw=max(512,w);th=h
    while (tw//cell)*((th-used_h)//cell)<len(chars):
        if th<1024:th*=2
        elif tw<1024:tw*=2
        else:raise ValueError('단일 텍스처 수용량 초과: 폰트 페이지/공용 폰트 필요')
    atlas=Image.new('L',(tw,th),lookup[0]);atlas.paste(Image.frombytes('L',(w,h),pix).crop((0,0,w,used_h)),(0,0))
    font=ImageFont.truetype(str(font_path),size)
    records=bytearray()
    for i,c in enumerate(chars):
        x=(i%(tw//cell))*cell;y=used_h+(i//(tw//cell))*cell
        glyph=shadow_glyph(c,font,size,pal,foreground);atlas.paste(glyph,(x,y))
        records+=struct.pack('<HBBHHBbbBHh',0x400+i,size,size,x,y,0,0,yoff,0,0,size)
    delta=len(records);header=bytearray(d[:ct]);struct.pack_into('<H',header,10,n+len(chars))
    for o in (24,28,48):struct.pack_into('<I',header,o,struct.unpack_from('<I',header,o)[0]+delta)
    struct.pack_into('<ff',header,64,1/tw,1/th)
    body=d[ct:ct+n*16]+records+d[ct+n*16:newshape]
    sh=bytearray(d[newshape:shape+16]);blocksize=48+tw*th
    struct.pack_into('<III',sh,4,blocksize,48,tw*th)
    struct.pack_into('<II',sh,24,tw,th)
    sh[33:36]=blocksize.to_bytes(3,'little');struct.pack_into('<HH',sh,36,tw,th)
    result=header+body+sh+atlas.tobytes()+d[palette_start:]
    struct.pack_into('<I',result,4,len(result))
    return bytes(result),atlas
