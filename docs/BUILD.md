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

## 와이드 파일 및 릴리즈 동봉

`iso_build.py`는 완성한 ISO의 CRC를 계산하고 호환성을 검사하여 `patches/SLUS-20756_<CRC>.pnach`를 생성합니다. 이후 매 빌드에 이 파일을 xdelta와 함께 릴리즈합니다. 기존 ISO만으로 다시 생성하려면 다음을 실행합니다.

```text
python tools/prepare_widescreen_release.py "NHL 2004 (USA) (Korean TEST9).iso"
python tools/verify_widescreen.py "NHL 2004 (USA) (Korean TEST9).iso"
```

새 버전은 `release_manifest.json`의 버전·ISO·xdelta 정보를 실제 결과에 맞게 갱신하고 런타임 검사 범위를 기록하세요. 와이드 생성기가 코드 지문이나 빈 공간 검사에 실패하면 실행 코드를 다시 분석해야 합니다.

게시 전 검사와 실제 게시(검사 명령에 `--publish` 추가):

```text
python tools/publish_release.py --iso "NHL 2004 (USA) (Korean TEST9).iso" --xdelta NHL2004_PS2_KO_v0.9.0-test9.xdelta --notes docs/RELEASE_NOTES.md --tag v0.9.0-test9 --title "v0.9.0-test9 한글패치"
```

게시 후에는 첨부 파일을 다시 다운로드하여 manifest의 SHA-256과 비교하세요. 와이드 사용법은 [WIDESCREEN.md](WIDESCREEN.md)를 참조합니다.
