"""실험용 2바이트 한글 → 16비트 글리프 변환. 원본 명령 검증 필수."""
import struct
from asm import *

class Code:
    def __init__(self,org):self.org=org;self.w=[];self.labels={};self.fix=[]
    def emit(self,*w):self.w.extend(w)
    def label(self,n):self.labels[n]=self.org+len(self.w)*4
    def branch(self,op,r,t,n):self.fix.append((len(self.w),op,r,t,n));self.w.append(0)
    def finish(self):
        for i,op,r,t,n in self.fix:self.w[i]=op(r,t,(self.labels[n]-self.org-i*4-4)//4)
        return b''.join(struct.pack('<I',w) for w in self.w)

def patch(original,chars=None,short_names=None):
    d=bytearray(original); changes=[]
    def put(va,code):
        off=va-0x107000
        assert off>=0
        changes.append({'address':hex(va),'before':d[off:off+len(code)].hex(),'after':code.hex()})
        d[off:off+len(code)]=code
    def words(va,*ws):put(va,b''.join(struct.pack('<I',w) for w in ws))
    # ELF 헤더와 첫 코드 사이의 실제 로드되는 172바이트 패딩.
    org=0x107054
    assert not any(d[0x54:0x100])
    a=Code(org)
    a.branch(beq,'a0','zero','return');a.emit(NOP)
    a.branch(beq,'a1','zero','end');a.emit(NOP)
    a.branch(beq,'a2','zero','return');a.emit(NOP)
    a.emit(addiu('a2','a2',-1))
    a.label('loop');a.branch(beq,'a2','zero','end');a.emit(lbu('v0',0,'a1'))
    a.branch(beq,'v0','zero','end');a.emit(addiu('a1','a1',1))
    a.emit(addiu('v1','v0',-0x81),sltiu('t0','v1',15))
    a.branch(beq,'t0','zero','store');a.emit(NOP)
    a.emit(lbu('t0',0,'a1'),sltiu('t1','t0',0x80))
    a.branch(bne,'t1','zero','store');a.emit(NOP)
    a.emit(sll('v1','v1',7),addu('v0','v1','t0'),addiu('v0','v0',0x380),addiu('a1','a1',1))
    a.label('store');a.emit(sh('v0',0,'a0'),addiu('a0','a0',2))
    a.branch(beq,'zero','zero','loop');a.emit(addiu('a2','a2',-1))
    a.label('end');a.emit(sh('zero',0,'a0'))
    a.label('return');a.emit(jr('ra'),NOP)
    code=a.finish();assert len(code)<=172;put(org,code)
    # 목적지, 원본, 최대 글자 수(종료 문자 포함).
    display_decoder=0x1f9200 if short_names else org
    words(0x234d40,j(display_decoder),NOP)
    words(0x234e00,j(display_decoder),addiu('a2','zero',-1))
    # CharToWide의 인자 순서는 원본, 목적지.
    words(0x51d860,move('t2','a0'),move('a0','a1'),move('a1','t2'),j(display_decoder),addiu('a2','zero',-1))
    # FEWideString 할당은 원래 바이트 수+1 유지: 출력 글자 수보다 충분히 큼.
    words(0x238d94,move('a0','v0'),move('a1','s2'),jal(display_decoder),addiu('a2','s1',1),j(0x238dd8),move('v0','s0'))
    # 8비트 그리기/폭 측정은 16비트 구현으로 전달한다. 기존 함수 영역 재사용.
    # 원본 호출 규약의 정수 인자 6개와 f12/f13은 변환 동안 보존한다.
    for entry,wide in ((0x1f8f28,0x1f8b30),(0x1f96e8,0x1f9320)):
        ws=[addiu('sp','sp',-0x1080),sd('ra',0x60,'sp')]
        for i,r in enumerate(('a0','a1','a2','a3','t0','t1')):ws.append(sd(r,0x20+i*8,'sp'))
        ws += [addiu('a0','sp',0x80),jal(0x1f9200 if short_names else org),addiu('a2','zero',2048)]
        for i,r in enumerate(('a0','a1','a2','a3','t0','t1')):ws.append(ld(r,0x20+i*8,'sp'))
        ws += [jal(wide),addiu('a1','sp',0x80),ld('ra',0x60,'sp'),jr('ra'),addiu('sp','sp',0x1080)]
        words(entry,*ws)
    # 역변환: 특수 제어 코드는 기존 경로를 유지하고 새 글리프만 2바이트로 복원.
    rev=Code(0x1f9800)
    rev.emit(addiu('t0','a2',-0x400),sltiu('t1','t0',1920))
    rev.branch(beq,'t1','zero','latin');rev.emit(addu('v0','s3','s2'))
    rev.emit(srl('t1','t0',7),addiu('t1','t1',0x81),sb('t1',0,'v0'),andi('t0','t0',127),ori('t0','t0',128),sb('t0',1,'v0'),j(0x238c20),addiu('s2','s2',2))
    rev.label('latin');rev.emit(sb('a2',0,'v0'),j(0x238c20),addiu('s2','s2',1))
    put(rev.org,rev.finish());words(0x238c10,j(rev.org),NOP)
    # 대문자화 루프가 한글의 두 번째 바이트를 라틴 문자로 바꾸지 않도록 건너뛴다.
    upper=Code(0x1f9900)
    upper.emit(lbu('v0',0,'s0'),addiu('v1','v0',-0x81),sltiu('v1','v1',15))
    upper.branch(beq,'v1','zero','normal');upper.emit(NOP)
    upper.emit(lbu('v1',1,'s0'),sltiu('v1','v1',128))
    upper.branch(bne,'v1','zero','normal');upper.emit(NOP)
    upper.emit(j(0x40cf90),addiu('s1','s0',2))
    upper.label('normal');upper.emit(jal(0x40cda0),lbu('a0',0,'s0'),j(0x40cf8c),NOP)
    put(upper.org,upper.finish());words(0x40cf84,j(upper.org),NOP)
    # 경기 명단 대문자화: 라틴 확장 문자 변환은 한글 뒤 바이트를
    # I/E/U 같은 ASCII로 바꾼다. 입구에서 ASCII 소문자만 처리한다.
    # 번역된 이름에는 Mac/Le 접두어 예외 처리도 필요하지 않다.
    case=Code(0x40ce48)
    case.branch(beq,'a0','zero','return');case.emit(NOP)
    case.label('loop');case.emit(lbu('v0',0,'a0'))
    case.branch(beq,'v0','zero','return');case.emit(addiu('v1','v0',-97))
    case.emit(sltiu('v1','v1',26))
    case.branch(beq,'v1','zero','next');case.emit(NOP)
    case.emit(addiu('v0','v0',-32),sb('v0',0,'a0'))
    case.label('next');case.branch(beq,'zero','zero','loop');case.emit(addiu('a0','a0',1))
    case.label('return');case.emit(jr('ra'),NOP)
    assert len(case.finish())<=392
    put(case.org,case.finish())
    # CPlayer::Init의 xlat: 경기 표시용 이름의 악센트를 제거하는 별도 경로.
    # 유효한 한글 바이트 쌍은 보존하고 단독 라틴 문자는 원본 표로 변환.
    xlat=Code(0x2b7960)
    xlat.branch(beq,'a0','zero','return');xlat.emit(NOP)
    xlat.emit(lui('t3',0x56),ori('t3','t3',0xe288),lui('t4',0x56),ori('t4','t4',0xe2c0))
    xlat.label('loop');xlat.emit(lbu('v0',0,'a0'))
    xlat.branch(beq,'v0','zero','return');xlat.emit(addiu('v1','v0',-129))
    xlat.emit(sltiu('v1','v1',15))
    xlat.branch(beq,'v1','zero','latin');xlat.emit(NOP)
    xlat.emit(lbu('v1',1,'a0'),sltiu('v1','v1',128))
    xlat.branch(beq,'v1','zero','loop');xlat.emit(addiu('a0','a0',2))
    xlat.emit(addiu('a0','a0',-2))
    xlat.label('latin');xlat.emit(move('t0','zero'))
    xlat.label('search');xlat.emit(addu('t1','t3','t0'),lbu('t2',0,'t1'))
    xlat.branch(beq,'t2','zero','next');xlat.emit(NOP)
    xlat.branch(beq,'t2','v0','replace');xlat.emit(NOP)
    xlat.branch(beq,'zero','zero','search');xlat.emit(addiu('t0','t0',1))
    xlat.label('replace');xlat.emit(addu('t1','t4','t0'),lbu('v0',0,'t1'),sb('v0',0,'a0'))
    xlat.label('next');xlat.branch(beq,'zero','zero','loop');xlat.emit(addiu('a0','a0',1))
    xlat.label('return');xlat.emit(jr('ra'),NOP)
    assert len(xlat.finish())<=164
    put(xlat.org,xlat.finish())
    # 메모리 카드 메시지는 UTF-16을 별도 함수로 좁힌다.
    narrow=Code(0x1f9100)
    narrow.branch(beq,'a1','zero','return');narrow.emit(NOP)
    narrow.branch(beq,'a2','zero','return');narrow.emit(NOP)
    narrow.label('loop');narrow.emit(lhu('v0',0,'a1'))
    narrow.branch(beq,'v0','zero','end');narrow.emit(addiu('a1','a1',2))
    narrow.emit(addiu('v1','v0',-1024),sltiu('t0','v1',1920))
    narrow.branch(beq,'t0','zero','single');narrow.emit(NOP)
    narrow.emit(srl('t0','v1',7),addiu('t0','t0',0x81),sb('t0',0,'a2'),addiu('a2','a2',1),andi('v0','v1',127),ori('v0','v0',128))
    narrow.label('single');narrow.emit(sb('v0',0,'a2'))
    narrow.branch(beq,'zero','zero','loop');narrow.emit(addiu('a2','a2',1))
    narrow.label('end');narrow.emit(sb('zero',0,'a2'))
    narrow.label('return');narrow.emit(jr('ra'),NOP)
    put(narrow.org,narrow.finish());words(0x48e7e8,j(narrow.org),NOP)
    if short_names:
        # 약칭은 자료 검색 키로도 쓰인다. 원본 데이터는 보존하고 그리기/폭 측정에서만 변환.
        table=bytearray()
        for en,kr in short_names.items():
            assert 2<=len(en)<=3 and len(kr)==2
            table+=en.encode('ascii').ljust(4,b'\0')+struct.pack('<HH',*(1024+chars.index(c) for c in kr))
        assert len(table)<=320
        put(0x1f8fc0,table)
        short=Code(0x1f9200)
        short.branch(beq,'a0','zero','fallback');short.emit(NOP)
        short.branch(beq,'a1','zero','fallback');short.emit(sltiu('t0','a2',3))
        short.branch(bne,'t0','zero','fallback');short.emit(NOP)
        short.emit(lbu('t0',0,'a1'))
        short.branch(beq,'t0','zero','fallback');short.emit(NOP)
        short.emit(lbu('v0',1,'a1'))
        short.branch(beq,'v0','zero','fallback');short.emit(NOP)
        short.emit(sll('v0','v0',8),addu('t0','t0','v0'),lbu('v0',2,'a1'))
        short.branch(beq,'v0','zero','search');short.emit(NOP)
        short.emit(sll('v0','v0',16),addu('t0','t0','v0'),lbu('v0',3,'a1'))
        short.branch(bne,'v0','zero','fallback');short.emit(NOP)
        short.label('search');short.emit(lui('t1',0x1f),ori('t1','t1',0x8fc0),addiu('t2','zero',len(short_names)))
        short.label('next');short.emit(lw('v0',0,'t1'))
        short.branch(beq,'v0','t0','found');short.emit(addiu('t2','t2',-1))
        short.branch(bne,'t2','zero','next');short.emit(addiu('t1','t1',8))
        short.label('fallback');short.emit(j(org),NOP)
        short.label('found');short.emit(lhu('v0',4,'t1'),sh('v0',0,'a0'),lhu('v0',6,'t1'),sh('v0',2,'a0'),sh('zero',4,'a0'),jr('ra'),NOP)
        code=short.finish();assert len(code)<=0x11c
        put(short.org,code)
    # 대결 로딩 화면의 영문 이니셜은 한글 첫 바이트를 잘라 버린다.
    # 이름 전체를 넘기고 20바이트 임시 버퍼를 32바이트로 늘린다.
    assert original[0x5276a4-0x107000:0x5276a8-0x107000]==struct.pack('<I',addiu('a1','zero',20))
    assert original[0x5276c4-0x107000:0x5276c8-0x107000]==struct.pack('<I',lbu('a2',16,'s5'))
    assert original[0x59e528-0x107000:0x59e52f-0x107000]==b'%c. %s\0'
    words(0x5276a4,addiu('a1','zero',32))
    words(0x5276c4,addiu('a2','s5',16))
    put(0x59e528,b'%s %s\0\0')
    # 20바이트 이름 표시 버퍼: 들어가면 전체 이름, 긴 이름은 첫 한글 음절+성.
    # %c가 한글 선행 바이트 하나만 출력하던 경기/명단/기록 경로를 함께 수정.
    name=Code(0x1f99a0)
    name.emit(move('t0','a2'),move('t3','zero'))
    name.label('firstlen');name.emit(lbu('v0',0,'t0'))
    name.branch(beq,'v0','zero','lastlen_start');name.emit(addiu('t0','t0',1))
    name.branch(beq,'zero','zero','firstlen');name.emit(addiu('t3','t3',1))
    name.label('lastlen_start');name.emit(move('t0','a3'),move('t4','zero'))
    name.label('lastlen');name.emit(lbu('v0',0,'t0'))
    name.branch(beq,'v0','zero','choose');name.emit(addiu('t0','t0',1))
    name.branch(beq,'zero','zero','lastlen');name.emit(addiu('t4','t4',1))
    name.label('choose');name.emit(addu('v0','t3','t4'),sltiu('v0','v0',19))
    name.branch(bne,'v0','zero','copy_start');name.emit(NOP)
    name.emit(lbu('v0',0,'a2'),addiu('v0','v0',-0x81),sltiu('v0','v0',15),addiu('t3','v0',1))
    name.label('copy_start');name.emit(move('t1','a0'),addiu('t2','zero',19))
    name.label('firstcopy');name.branch(beq,'t3','zero','separator');name.emit(lbu('v0',0,'a2'))
    name.branch(beq,'v0','zero','separator');name.emit(addiu('t3','t3',-1))
    name.emit(sb('v0',0,'t1'),addiu('t1','t1',1),addiu('t2','t2',-1))
    name.branch(beq,'zero','zero','firstcopy');name.emit(addiu('a2','a2',1))
    name.label('separator');name.branch(beq,'t1','a0','lastcopy');name.emit(lbu('v0',0,'a3'))
    name.branch(beq,'v0','zero','lastcopy');name.emit(addiu('v0','zero',32))
    name.emit(sb('v0',0,'t1'),addiu('t1','t1',1),addiu('t2','t2',-1))
    name.label('lastcopy');name.emit(j(0x1f9760),NOP)
    code=name.finish();assert len(code)<=0x10c;put(name.org,code)
    tail=Code(0x1f9760)
    tail.label('loop');tail.emit(lbu('v0',0,'a3'))
    tail.branch(beq,'v0','zero','end');tail.emit(addiu('t4','v0',-0x81))
    tail.emit(sltiu('t4','t4',15),addiu('t4','t4',1),sltu('v1','t2','t4'))
    tail.branch(bne,'v1','zero','end');tail.emit(NOP)
    tail.emit(sb('v0',0,'t1'),addiu('t1','t1',1),addiu('a3','a3',1),addiu('t2','t2',-1),addiu('t4','t4',-1))
    tail.branch(beq,'t4','zero','loop');tail.emit(NOP)
    tail.emit(lbu('v0',0,'a3'))
    tail.branch(beq,'v0','zero','undo');tail.emit(NOP)
    tail.emit(sb('v0',0,'t1'),addiu('t1','t1',1),addiu('t2','t2',-1))
    tail.branch(beq,'zero','zero','loop');tail.emit(addiu('a3','a3',1))
    tail.label('undo');tail.emit(addiu('t1','t1',-1))
    tail.label('end');tail.emit(sb('zero',0,'t1'),jr('ra'),subu('v0','t1','a0'))
    code=tail.finish();assert len(code)<=0xa0;put(tail.org,code)
    loads=[(0x2bfa4c,'v0',0xb8),(0x2bfaa4,'v0',0xb8),(0x2bfae8,'v0',0x75c),
        (0x2c2928,'v0',0xb8),(0x2c29a8,'v0',0xb8),(0x2c29fc,'s0',0xb8),
        (0x402858,'s0',16),(0x417e38,'a3',0),(0x422648,'a3',0),
        (0x4235c8,'t0',0),(0x423988,'t0',0),(0x4448ec,'a3',0),
        (0x4598f0,'sp',0),(0x45be00,'sp',0x550),(0x48d320,'sp',0x110),
        (0x48fca0,'a3',16),(0x497528,'a3',16),(0x4da7c0,'sp',0x50),
        (0x4dfb74,'s1',16),(0x4ff44c,'s3',16),(0x4ffdb4,'s1',16),(0x501e50,'a3',16)]
    for va,reg,off in loads:
        assert original[va-0x107000:va-0x107000+4]==struct.pack('<I',lbu('a2',off,reg)),hex(va)
        words(va,addiu('a2',reg,off))
    for va in [0x2bfaec,0x2c292c,0x2c29b0,0x2c29f8,0x402864,0x417e40,0x422650,
            0x4235c4,0x423984,0x4448f0,0x4598fc,0x45be10,0x48d32c,0x48fca4,
            0x49752c,0x4da7d0,0x4dfb80,0x4ff45c,0x4ffdc0,0x501e58]:
        assert original[va-0x107000:va-0x107000+4]==struct.pack('<I',jal(0x1e4310)),hex(va)
        words(va,jal(name.org))
    # 단장 순위는 출력 버퍼가 UTF-16이므로 같은 안전한 이름을 만든 뒤 변환.
    words(0x1f9940,addiu('sp','sp',-64),sd('ra',0,'sp'),sd('a0',8,'sp'),
        jal(name.org),addiu('a0','sp',32),sd('v0',16,'sp'),ld('a0',8,'sp'),
        addiu('a1','sp',32),jal(org),addiu('a2','zero',20),ld('v0',16,'sp'),
        ld('ra',0,'sp'),jr('ra'),addiu('sp','sp',64))
    assert original[0x4bc9f4-0x107000:0x4bc9f8-0x107000]==struct.pack('<I',lbu('a2',0x80,'sp'))
    assert original[0x4bca00-0x107000:0x4bca04-0x107000]==struct.pack('<I',jal(0x234e88))
    words(0x4bc9f4,addiu('a2','sp',0x80));words(0x4bca00,jal(0x1f9940))
    return bytes(d),changes
