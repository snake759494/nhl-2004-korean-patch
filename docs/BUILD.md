# 빌드

Python 3.11 이상, `requirements.txt`의 라이브러리, 원본 북미판 ISO, `NanumSquareNeo-dEb.ttf`가 필요합니다. 글꼴은 나눔스퀘어네오 공식 배포본에서 구합니다. 외부 번역 서비스를 사용하지 않습니다.

저장소 루트에 원본 `NHL 2004 (USA).iso`와 글꼴을 놓고 실행합니다.

```text
python -m pip install -r requirements.txt
python tools/prepare.py
python tools/build_test.py
python tools/verify_test.py
python tools/verify_names.py
python tools/verify_font_shadow.py
python tools/verify_extra.py
python tools/iso_build.py "NHL 2004 (USA) (Korean TEST9).iso"
```

`prepare.py`는 원본 SHA-256을 확인하고 작업 파일 및 영어 원문 연결을 복원합니다. 복원 파일과 게임 원본은 Git에서 제외됩니다. `located.json`은 게임 자료 경로·위치·길이·인코딩과 한글 번역만 보관합니다. `short_keys.json`에는 짧은 보정 키와 사용되지 않는 번역의 글자 집합 유지용 키가 있습니다.

빌드 결과의 파일별 해시는 `validation/rebuild.json`, 배포 ISO 및 패치 해시는 `release_manifest.json`과 비교할 수 있습니다. 도구 및 글꼴 버전 차이로 결과가 달라질 수 있으므로 배포판과 완전히 같은 결과가 필요하면 검증된 xdelta를 적용합니다.

차분 파일 생성과 복원 검사:

```text
xdelta3 -e -9 -S none -A -s "NHL 2004 (USA).iso" "NHL 2004 (USA) (Korean TEST9).iso" NHL2004_PS2_KO_v0.9.0-test9.xdelta
xdelta3 -d -s "NHL 2004 (USA).iso" NHL2004_PS2_KO_v0.9.0-test9.xdelta verify.iso
```

복원 ISO의 SHA-256이 릴리즈의 결과 해시와 일치해야 합니다. 검사 후 `verify.iso`를 삭제할 수 있습니다. 원본 및 현재 사용하는 패치 ISO는 보존하세요.
