# 안경만두

빨간 안경을 쓴 작은 만두가 작업 옆에서 조용히 머무는 Windows 우선 데스크톱 펫입니다.
인터넷 연결, 계정, 소리, 말풍선 없이 실행합니다. 최초 의존성 설치에만 인터넷이 필요합니다.

## 실행 (Windows 10/11 · Python 3.10 이상)

PowerShell에서 저장소 폴더를 열고:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\pythonw.exe run_pet.py
```

종료 후 재실행할 때는 마지막 명령만 실행합니다. 실행 중인 인스턴스는 한 개만 허용합니다.
알림 영역에 아이콘이 안 보이면 Windows의 숨겨진 아이콘 목록을 확인하세요.

## 사용법

- 왼쪽 클릭: 한 번 통통 뛰기. 3분간 상호작용이 없으면 졸고, 클릭하면 깨어납니다.
- 누른 채 이동: 드래그 임계 거리를 넘으면 들리기, 놓으면 짧게 말랑한 착지.
- 오른쪽 클릭: 산책 켜기/끄기, 크기(90/120/180px), 항상 위, 잠깐 숨기기, 설정, 종료.
- 알림 영역 아이콘 두 번 클릭 또는 메뉴의 ‘안경만두 다시 보기’: 숨김 해제.
- 설정: 산책 빈도, 전체 화면 앱 자동 숨김, Windows 로그인 시 실행.

처음에는 기본 모니터의 작업표시줄 위 오른쪽에 나타납니다. 산책은 2~4초,
대기는 기본 10~22초로, 멈추면 정면을 봅니다. 드래그한 높이를 유지하며 짧게 걷습니다.
현재 모니터의 작업 영역에서 벗어나지 않도록 제한합니다. 자동으로 모니터 사이를 이동하지 않습니다.
트레이가 없는 환경에서는 복구할 수 없는 숨김을 막기 위해 숨기기 기능을 끕니다.

설정은 `%APPDATA%\GlassesMandu\settings.json`에 원자적으로 저장합니다.
위치, 크기, 이동 여부, 항상 위, 빈도, 자동 숨김 및 자동 실행 선택을 기억합니다.
숨김 상태는 저장하지 않아 다음 실행 때는 다시 나타납니다.
자동 실행은 현재 사용자 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`의
`GlassesMandu` 항목만 사용합니다. 실행 파일/저장소를 옮기기 전 옵션을 끄고 새 위치에서 다시 켜세요.
오류 기록은 같은 폴더의 `deskpet.log`에서 확인할 수 있습니다.

## 이미지 상태

현재 캐릭터는 첨부 1번의 정면·측면 외형을 참고해 코드로 다시 그린 임시 도트 아트이며, 투명 PNG 34장을 포함합니다.
첨부 원본 PNG 추출본이나 최종 승인 아트가 아닙니다. 실제 원본의 투명도는 아직 확인하지 못했습니다.
빨간 사각 안경, 노란 만두 몸, 큰 머리와 작은 팔다리를 유지했습니다.
[자산 규격](assets/README.md)에 맞춰 원본 기반 투명 PNG 프레임을 넣으면 자동으로 대체합니다.
확대·축소는 nearest-neighbor를 사용하고, 매 프레임의 알파 마스크로 투명 영역을 클릭 통과시킵니다.

## 개발 및 테스트

```bash
python -m pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python -m deskpet
```

Linux의 화면 없는 테스트에서는 Qt offscreen 플러그인을 사용합니다.
앱 창은 포커스를 받지 않도록 Qt 플래그 및 Windows `WS_EX_NOACTIVATE`를 설정합니다.
직접 연 설정 대화상자는 입력을 위해 포커스를 받습니다.
걷기·애니메이션은 단일 30Hz 타이머와 캐시된 프레임을 사용하며, 숨겨진 동안 갱신을 멈춥니다.

## Windows 배포

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller==6.12.0
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name GlassesMandu --add-data "assets;assets" run_pet.py
```

`dist\GlassesMandu\GlassesMandu.exe`를 실행합니다. 배포 시 **폴더 전체**를 전달하세요.
Python 설치는 필요하지 않습니다. 서명되지 않은 실행 파일은 Windows SmartScreen 경고가 나타날 수 있습니다.
GitHub Actions에도 Windows 테스트·빌드 및 아티팩트 업로드 작업을 마련했습니다.
워크플로를 실제 실행하기 전에는 빌드 성공을 보장하지 않습니다.

## Windows 수동 인수 확인

자동 테스트는 이동 모델, 설정 복원, 알파 마스크, 클릭/드래그 구분, 애니메이션 복귀를 검사합니다.
아래 항목은 실제 Windows 세션에서 확인해야 합니다.

- 메모장에 입력하면서 펫을 클릭/드래그해도 입력 포커스가 유지되는지
- 투명 영역을 클릭하면 뒤 프로그램을 조작할 수 있는지
- 작업표시줄 위치·디스플레이 배율 변경 후에도 캐릭터가 작업 영역 안에 있는지
- 트레이의 숨기기·다시 보기·종료 및 전체 화면 앱 전환 시 자동 복원
- 로그인 자동 실행의 등록·해제 및 실제 재로그인
- 여러 시간 사용 시 CPU·메모리, 모니터 분리 후 위치 복구

안경 고쳐 쓰기, 헤드폰 집중 모드, 말풍선, 자동 모니터 간 산책은 후속 범위입니다.

## 현재 검증 결과

2026-11-05: Linux / Python 3.12 / PySide6 6.8.3에서 자동 테스트 14개 통과.
실제 `main()` 시작, 이벤트 루프 실행, 정상 종료, 설정 파일 저장 및 단일 실행 잠금 해제도 확인했습니다.
`pip check` 통과. offscreen 플러그인은 OS 창 마스크 적용을 지원하지 않으므로
테스트는 계산된 마스크만 검사하며 Windows 클릭 통과·포커스·트레이·자동 실행과
배포 EXE 및 장시간 자원 사용은 아직 검증하지 않았습니다.
