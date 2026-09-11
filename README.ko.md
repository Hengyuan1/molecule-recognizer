# Molecule Recognizer

[English](README.md) | [简体中文](README.zh-CN.md) | 한국어 | [Русский](README.ru.md) | [Français](README.fr.md)

스크린샷, 논문, 웹페이지의 이미지에서 분자 구조를 인식하고 SMILES로 변환합니다. 인식한 구조를 직접 편집하고 3차원 좌표를 생성하여 XYZ 파일로 저장하거나 복사할 수 있는 계산화학용 데스크톱 프로그램입니다.

**버전 [0.3.0](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0)** — OSRA가 포함된 Windows 포터블 앱과 Linux/Python 앱을 제공합니다. [Windows 버전 다운로드](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip).

![원본 이미지, 편집 가능한 2D 분자 구조, 나란히 표시된 3D 구조를 보여 주는 MolRecognizer](docs/media/UI-demo.png)

생성한 3D 미리보기를 두 번 클릭하면 2D 캔버스 옆에서 비교할 수 있습니다. 구분선을 드래그하여 너비를 조절할 수 있으며, 비교 중에도 2D 편집기와 SMILES를 사용할 수 있습니다.

이 문서는 설치와 일상적인 사용법을 설명합니다. 자세한 기능·개발·릴리스 기록은 [영문 README](README.md)와 아래 링크를 참고하세요. 번역 대상은 문서이며, 앱의 메뉴와 버튼은 영어이므로 설명에서도 실제 버튼 이름을 그대로 사용합니다.

## 바로가기

- [Windows 사용법](#windows-사용법)
- [Linux 사용법](#linux-사용법)
- [OSRA 및 선택 의존성](#osra-및-선택-의존성)
- [인식·편집·내보내기](#인식편집내보내기)
- [단축키](#단축키) · [Python API](#python-api) · [문제 해결](#문제-해결)

## Windows 사용법

### 포터블 EXE: Python, Conda, WSL 설치 불필요

1. [MolRecognizer-0.3.0-windows-x64.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip) 파일을 다운로드합니다(159 MiB).
2. `C:\Users\YourName\Apps`처럼 경로가 짧고 쓰기 가능한 고정 폴더에 **ZIP 전체를 압축 해제**합니다. 지나치게 깊은 폴더 경로는 피하세요.
3. 압축 해제된 `MolRecognizer` 폴더에서 `MolRecognizer.exe`를 실행합니다.
4. `_internal`, `tools`, 작업 프로세스용 EXE와 모든 부속 파일을 함께 보관합니다. **메인 EXE만 복사하거나 ZIP 안에서 바로 실행하지 마세요.** 이 EXE를 가리키는 바탕 화면 바로가기를 만들 수 있습니다.

대상 환경은 **Windows 10/11 x64**이며, 화면 캡처에는 .NET Framework 4.x가 필요합니다. **OSRA 2.2.4**, 사전 파일, DLL, Python/Qt/RDKit 런타임 및 미리 컴파일된 캡처 도구가 포함되어 있습니다. OSRA를 따로 설치하거나 PowerShell 스크립트를 실행할 필요가 없습니다. MolScribe와 모델 가중치는 포함되지 않습니다.

업데이트할 때는 앱을 종료하고 새 버전을 별도 폴더에 압축 해제한 뒤, 테스트 후 바로가기 대상을 변경하세요. 서로 다른 버전의 파일을 섞지 마세요.

### 다운로드 파일의 차이와 보안 안내

- `MolRecognizer-0.3.0-windows-x64.zip`: 바로 실행할 수 있는 Windows 앱입니다. 일반 사용자는 이 파일만 받으면 됩니다.
- `MolRecognizer-0.3.0-sources.zip`: **같은 버전**의 앱·의존성 소스 코드, 패치, 빌드 안내입니다. 소스를 살펴보거나 다시 빌드하는 개발자를 위한 파일로, 이전 버전이 아니며 앱 실행에 필요하지 않습니다.
- `.zip.sha256`: 해당 ZIP이 손상되거나 변경되었는지 확인하기 위한 체크섬 파일입니다.
- GitHub가 자동 생성하는 “Source code” 다운로드는 실행 가능한 앱이 아니며, 의존성 소스까지 담긴 `sources.zip`을 대신하지도 않습니다.

ZIP과 체크섬 파일이 있는 폴더에서 PowerShell을 열고 실행하세요.

```powershell
Get-FileHash .\MolRecognizer-0.3.0-windows-x64.zip -Algorithm SHA256
Get-Content .\MolRecognizer-0.3.0-windows-x64.zip.sha256
```

두 SHA-256 값을 비교하세요. 체크섬 일치는 디지털 서명이나 보안 보증이 아닙니다. 앱은 코드 서명되지 않아 Windows 보안 경고가 나타날 수 있습니다. 다운로드 출처를 확인하고 **백신을 끄거나 회사의 보안 정책을 우회하지 마세요**.

배포 파일은 테스트한 ZIP과 동일합니다. 내부 문서 일부의 “not published”는 빌드 당시 상태를 기록한 것이며, 이후 공개된 사실은 [릴리스 페이지](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0)에 표시됩니다. `v0.3.0` 태그는 실제 빌드 소스를, `main`은 이후 문서 업데이트도 포함한 내용을 가리킵니다.

### PowerShell에서 소스로 실행하기

포터블 EXE를 사용한다면 이 절은 건너뛰세요. 네이티브 Windows Python이나 회사에서 허용한 Conda 환경으로 실행할 수 있으며 WSL은 필요하지 않습니다.

Git과 uv가 필요하다면 설치합니다.

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

PowerShell을 다시 연 다음 소스를 받습니다.

```powershell
git clone --branch main https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
```

Git을 사용할 수 없다면 `main` 브랜치의 소스 ZIP을 다운로드하여 압축을 풀고 `pyproject.toml`이 있는 폴더로 이동하세요. 다음 중 한 가지 설치 방법을 선택합니다.

**방법 A — uv 편집 가능 도구 설치: 어느 폴더에서든 실행.**

```powershell
uv tool install --python 3.11 --editable .
uv tool update-shell
```

PowerShell을 다시 열고 실행합니다.

```powershell
molrecognizer
```

편집 가능 설치는 소스 폴더를 직접 사용하므로 폴더를 유지하세요. 위치를 옮겼다면 새 위치에서 도구를 다시 설치해야 합니다.

**방법 B — Conda / Miniconda.**

```powershell
conda create -n molrecognizer python=3.11 -y
conda activate molrecognizer
python -m pip install -e .
molrecognizer
```

새 터미널에서는 먼저 `conda activate molrecognizer`를 실행한 뒤 `molrecognizer`를 실행하세요.

**개발용 설치:** 도구로 설치하는 대신 저장소 폴더에서 `uv sync --python 3.11`, `uv run molrecognizer`를 실행해도 됩니다.

### Windows 소스 설치에 OSRA 연결하기

소스 설치는 **OSRA를 자동 설치하지 않습니다**. 완전한 Windows OSRA 런타임이나 이미 압축 해제한 포터블 앱의 `MolRecognizer\tools\osra` 폴더를 사용할 수 있습니다. DLL, 사전 및 기타 런타임 파일을 함께 보관하세요. 직접 빌드하려면 [OSRA 빌드 안내](packaging/windows/OSRA-BUILD.md)(영문)를 참고하세요.

현재 PowerShell 세션에서 실제 실행 파일 경로를 설정합니다.

```powershell
$env:OSRA_EXECUTABLE = "C:\path\to\OSRA\bin\osra.exe"
& $env:OSRA_EXECUTABLE --version
molrecognizer
```

포터블 앱의 OSRA를 사용한다면 경로 끝은 `MolRecognizer\tools\osra\bin\osra.exe`입니다. 이후 세션에도 적용하려면 사용자 환경 변수로 저장합니다.

```powershell
[Environment]::SetEnvironmentVariable(
    "OSRA_EXECUTABLE",
    "C:\path\to\OSRA\bin\osra.exe",
    "User"
)
```

저장 후 PowerShell을 다시 여세요. 특정 Conda 환경에만 연결할 수도 있습니다.

```powershell
conda activate molrecognizer
conda env config vars set OSRA_EXECUTABLE="C:\path\to\OSRA\bin\osra.exe"
conda deactivate
conda activate molrecognizer
```

### Windows 화면 캡처와 표시 크기

MolRecognizer에 키보드 포커스를 둔 상태에서 포인터를 노트북 화면이나 원하는 외부 모니터로 옮기고 **Alt+Y** 또는 **Ctrl+Shift+S**를 누르세요. 사각형을 그린 뒤 영역을 이동하거나 모서리·가장자리를 조절할 수 있습니다. **Enter / Recognize**로 인식하고 **Esc / 오른쪽 클릭 / Cancel**로 취소합니다. 방향키는 1픽셀, Shift와 함께 누르면 10픽셀씩 이동합니다. **Screenshot** 버튼도 사용할 수 있습니다.

네이티브 Windows의 단축키는 **전역 단축키가 아니며**, 앱에 키보드 포커스가 있어야 합니다. 한 번에 모니터 하나를 캡처합니다. 다른 화면을 선택하려면 취소하고 포인터를 옮긴 뒤 다시 시작하세요.

포터블 앱은 미리 컴파일된 캡처 도구를 사용합니다. Python 소스 설치는 Windows PowerShell의 `Add-Type`으로 C# 도우미를 컴파일하므로 회사 정책에 의해 차단될 수 있습니다. Snipaste는 필요하지 않습니다. 캡처가 차단되면 허용된 캡처 도구로 저장한 이미지를 **Open Image**로 불러오세요.

모니터 간 드래그가 끝나면 창 크기가 자동 조정됩니다. 오른쪽 아래 **A− / A+**로 UI 크기를 조절하고, 백분율을 클릭하면 해당 모니터의 권장 배율로 돌아갑니다. **Fit**은 창 크기를 다시 맞춥니다. 설정은 모니터별로 저장됩니다.

### 선택 사항: WSL2 / WSLg

WSL은 Linux 앱을 실행하는 다른 방법일 뿐, **Windows EXE나 Conda 사용에 필수는 아닙니다**. 허용된 환경에서만 사용하세요.

WSLg가 있는 Ubuntu/WSL2 안에서 아래 Linux 절차에 따라 **Linux OSRA와 Linux Python/uv**를 설치하고 Ubuntu 터미널에서 `molrecognizer`를 실행합니다. Linux 앱에 Windows `osra.exe`를 지정하지 마세요.

WSLg에서는 Windows 도우미가 실행 가능하고 다른 앱이 단축키를 사용하지 않는 경우, 앱 실행 중 **전역 Windows Alt+Y**를 사용할 수 있습니다. 포인터가 있는 Windows 모니터를 캡처하며, PowerShell 상호 운용 및 도우미 실행 권한이 필요합니다. WSLg 메뉴와 재인식 검토 패널은 팝업 표시 문제를 줄이기 위해 메인 창 내부에 표시됩니다.

## Linux 사용법

Linux 버전은 로컬 OSRA를 사용하는 Python 데스크톱 앱으로, 그래픽 데스크톱 세션이 필요합니다. 다음 Bash 명령은 Ubuntu/Debian 기준이며 다른 배포판에서는 해당 패키지를 사용하세요.

### OSRA 설치

OSRA 패키지를 제공하는 배포판에서:

```bash
sudo apt update
sudo apt install git osra
osra --version
```

패키지 제공 여부와 버전은 배포판에 따라 다르며 Windows 번들의 OSRA 2.2.4와 다를 수 있습니다. 이미 정상 작동하는 OSRA가 있다면 그대로 사용해도 됩니다. 사용자 지정 경로:

```bash
export OSRA_EXECUTABLE="/path/to/OSRA/bin/osra"
"$OSRA_EXECUTABLE" --version
```

실제 경로로 바꾸세요. 이후 터미널에서도 사용하려면 `export` 줄을 `~/.bashrc` 또는 사용하는 셸의 시작 파일에 추가합니다. 적절한 패키지가 없으면 [OSRA 프로젝트](https://sourceforge.net/projects/osra/)의 소스와 빌드 안내를 이용하세요.

### MolRecognizer 설치와 실행

**Python 3.10 이상**이 필요하며 예제에서는 3.11을 사용합니다. uv 방식을 선택한다면 [공식 안내](https://docs.astral.sh/uv/getting-started/installation/)에 따라 uv를 설치하고 소스를 받습니다.

```bash
git clone --branch main https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
```

**방법 A — uv 편집 가능 도구 설치.**

```bash
uv tool install --python 3.11 --editable .
uv tool update-shell
```

새 터미널에서는 환경 활성화 없이 어느 폴더에서든 실행할 수 있습니다.

```bash
molrecognizer
```

소스 폴더를 유지하고, 이동했다면 새 위치에서 다시 설치하세요.

**방법 B — pip 가상 환경.** Python 3.10+와 `venv` 지원이 설치되어 있어야 합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
molrecognizer
```

새 터미널에서는 같은 환경을 먼저 활성화합니다.

```bash
source /path/to/molecule-recognizer/.venv/bin/activate
molrecognizer
```

**개발용 설치:** 저장소에서 `uv sync --python 3.11`, `uv run molrecognizer`를 실행합니다. 다른 폴더에서는 다음과 같이 실행할 수 있습니다.

```bash
uv run --project /path/to/molecule-recognizer molrecognizer
```

### Linux 화면 캡처

앱에 포커스를 둔 채 포인터를 대상 화면으로 옮기고 **Alt+Y / Ctrl+Shift+S**를 누릅니다. 테두리 없는 Qt 선택 화면에서 영역을 그리거나 이동·크기 조절한 뒤 Enter로 확인하거나 Esc로 취소합니다. 네이티브 Linux는 전역 캡처 단축키를 등록하지 않습니다.

- **X11:** 먼저 Qt 캡처를 시도하며, 보통 별도 패키지가 필요하지 않습니다. `scrot`은 선택적인 대체 도구입니다.
- **Wayland:** 데스크톱과 컴포지터의 허용 범위에 따라 작동합니다. `grim`은 호환 컴포지터에서만 사용할 수 있으며 모든 Wayland 환경을 지원하는 해결책은 아닙니다. `gnome-screenshot`이 설치되어 있으면 이것도 시도합니다.
- 캡처 실패, 검은 화면 또는 잘못된 화면이 나오면 데스크톱의 캡처 도구로 이미지를 저장한 뒤 **Open Image**로 불러오세요.

필요한 대체 도구만 설치하세요.

```bash
# X11 대체 도구
sudo apt install scrot

# 호환 Wayland 컴포지터용 대체 도구
sudo apt install grim
```

WSLg에서 실행하는 경우에는 위 WSLg 절의 Windows 캡처 설명을 따르세요.

## OSRA 및 선택 의존성

소스 설치 시 RDKit, PySide6, Pillow, NumPy(`numpy<2`)가 자동 설치됩니다. [pyproject.toml](pyproject.toml)을 참고하세요. OSRA는 Python wheel이 아닌 별도의 네이티브 프로그램이므로 `pip` 또는 `uv sync`가 설치하지 않습니다. Windows 포터블 앱에는 이미 포함되어 있습니다.

`OSRA_EXECUTABLE`을 명시하면 항상 우선하며, 실제 실행 가능한 파일을 가리켜야 합니다. 설정하지 않은 경우:

- **Windows 포터블:** EXE 옆의 `tools/osra/bin`, `.tools/osra/bin`, `PATH` 순서로 검색합니다.
- **Python 소스 설치:** `PATH`, 소스 폴더의 `.tools/osra/bin`, `tools/osra/bin` 순서로 검색합니다.

프로젝트 내부 설치 예시입니다. Windows에서는 `osra` 대신 `osra.exe`를 사용하세요.

```text
.tools/osra/
├── bin/
│   ├── osra
│   └── 필요한 런타임 라이브러리 및 기타 파일
└── share/
    ├── chain.txt
    ├── spelling.txt
    └── superatom.txt
```

선택한 OSRA 설치의 `share/osra`, `share` 또는 `bin`에서 사전 파일 세 개를 모두 찾으면 앱이 절대 경로를 자동으로 전달합니다. 따라서 현재 작업 폴더에 의존하지 않습니다. 나머지 런타임 파일도 함께 유지하세요.

### 선택 사항: MolScribe 백엔드

실제로 사용하는 환경에 맞는 명령 하나를 선택합니다.

```bash
# uv 개발 환경
uv sync --extra molscribe

# uv 편집 가능 도구: 소스 폴더에서 실행
uv tool install --python 3.11 --editable --with molscribe --with huggingface-hub .

# 활성화된 pip / Conda 환경
python -m pip install -e ".[molscribe]"
```

선택 의존성을 설치해도 기본 OSRA 백엔드는 바뀌지 않습니다. Python API에서 `backend="molscribe"`를 명시하세요. 처음 사용할 때 모델 가중치를 다운로드할 수 있습니다. GPU 사용에는 호환되는 CUDA 지원 PyTorch도 필요합니다. 이 설치로 기존 포터블 EXE에 MolScribe가 추가되지는 않습니다.

## 인식·편집·내보내기

1. **Open Image** 또는 화면 캡처로 분자 하나를 불러옵니다. **Load SMILES**는 OSRA 없이도 사용할 수 있습니다.
2. 원본과 2D 구조·SMILES를 비교하여 원자 라벨, 고리 연결, 결합 차수, 전하와 입체화학을 확인하세요. 원자가 검사를 통과해도 인식 결과가 맞는 것은 아닙니다. 여러 구조가 있으면 첫 번째 유효한 결과를 불러옵니다.
3. 도구로 직접 수정하거나 **Retry recognition**으로 다른 결과를 비교합니다. Undo/Redo는 연결 관계와 입체 정보를 보존합니다.
4. **Render**로 3D 좌표를 생성하고 미리보기를 두 번 클릭하여 나란히 비교합니다. 구분선으로 너비를 조절하며, 3D 뷰는 왼쪽 드래그로 회전, 오른쪽 드래그로 이동, 휠로 확대·축소합니다.
5. 2D 구조를 수정했다면 **Render**를 다시 눌러 3D 결과를 갱신합니다.
6. **Copy / Export**는 SMILES, **Save xyz / Copy xyz**는 전체 XYZ 좌표를 저장·복사합니다. 좌표 단위는 Angstrom(Å, 기본값) 또는 Bohr를 선택할 수 있습니다.

**View → Fit structure**는 좌표나 결합 위치를 바꾸지 않고 2D 뷰만 맞춥니다. **Format**은 2D 배치를 다시 계산하며, **Clean**은 작업 공간을 비웁니다. 오른쪽 아래 **Fit**은 앱 창 크기를 맞추는 별도 기능입니다.

### 복잡한 구조 다시 인식하기

최초 인식이 끝나거나 실패한 뒤 **Retry recognition**을 사용할 수 있습니다. 원본 해상도의 이미지로 적응형 임계값, 100 dpi 해석, 회색조 임계값 0.35라는 세 가지 로컬 OSRA 방식을 비교합니다. 점수는 정확도 백분율이 아니며 결과를 자동 선택하지 않습니다.

교체하려는 경우에만 **Use selected**를 누르세요. **Keep current / Esc**는 기존 편집을 유지합니다. **Stop retries**는 추가 시도를 중단하지만 완료된 후보는 남겨둡니다. 결과 교체는 한 번에 실행 취소할 수 있습니다. 새 결과를 적용한 뒤 XYZ를 저장하려면 Render를 다시 실행하세요.

각 시도는 OSRA 처리 15초와 프로세스 유예 10초로 제한되며, 세 번 합계 최대 약 75초입니다. 언제든 취소할 수 있습니다. 모든 후보가 틀릴 수도 있으며, 작은 PNG를 확대하는 것보다 원본 PDF/벡터 그림에서 더 선명하게 캡처하는 편이 유용합니다.

### 편집 도구와 표시

- **Select:** 원자를 클릭하여 원소 변경, 드래그하여 이동, 빈 공간을 드래그하여 영역 선택, 선택 영역 전체 이동, 결합 클릭으로 차수 순환.
- **Bond:** Single/Double/Triple/Wedge/Dash 선택. 원자 클릭으로 연결된 원자를 추가하거나 드래그하여 결합 생성. 쐐기형·점선 쐐기형 결합은 입체화학 표시용입니다.
- **Atom / Eraser:** 원자 추가·변경 / 원자·결합 삭제. 영역 선택 후 일괄 삭제도 지원합니다.
- **Ring:** 벤젠 또는 6·5·4·3원자 고리를 원자나 결합에 연결하거나 독립적으로 추가하고, 드래그하여 방향 조절.
- **Charge ⊕/⊖ / PT:** 형식 전하 조절 / 주기율표에서 원소 선택.
- **Undo / Redo:** 원자·결합·연결 관계·좌표·입체 표지를 실행 취소하거나 복원.
- 방향족 고리는 케쿨레식 단일·이중 결합으로 표시합니다. 일반적인 O–H와 N–H는 OH, NH, NH₂ 등으로 간결하게 표시하지만 분자 데이터와 SMILES는 바꾸지 않습니다. 동위원소·매핑·전하·입체 표지가 있는 수소는 명시적으로 남습니다.
- OSRA의 2D 좌표, 단일·이중 결합 배치 및 쐐기 표지를 보존하여 원본과 비교하기 쉽게 합니다. 인식 오류는 직접 수정해야 합니다. Format은 배치를 다시 계산하고 입체 정보를 확인하지만 원본과의 대조를 대신하지 않습니다.
- 2D 캔버스는 휠로 확대·축소하고 가운데 또는 오른쪽 버튼으로 드래그하여 이동합니다. 3D 비교 패널을 닫으면 전체 2D 캔버스로 돌아갑니다.

## 단축키

| 동작 | 단축키 |
| --- | --- |
| 이미지 열기 | Ctrl+O |
| 화면 캡처 | Ctrl+Shift+S / Alt+Y |
| SMILES 내보내기 | Ctrl+E |
| 실행 취소 / 다시 실행 | Ctrl+Z / Ctrl+Shift+Z |
| 종료 | Ctrl+Q |
| 선택 영역 삭제 | Delete / Backspace |
| UI 확대 / 축소 | Ctrl+Alt++ / Ctrl+Alt+- |
| UI 배율 초기화 | Ctrl+Alt+0 |

네이티브 Windows와 Linux의 캡처 단축키는 앱에 포커스가 있어야 합니다. 전역 Alt+Y는 앞서 설명한 WSLg 도우미에서만 제공됩니다.

## 개인정보와 임시 파일

인식은 로컬에서 수행되며 이미지를 NCI OSRA 웹사이트에 업로드하지 않습니다. Windows 캡처 도구는 화면과 선택 영역을 메모리에만 저장합니다. Linux의 명령줄 대체 도구는 임시 PNG를 만들 수 있으며 읽은 뒤 삭제합니다. 인식에 사용하는 임시 이미지도 처리 후 삭제합니다.

원본 이미지는 Retry recognition을 위해 새 이미지로 바뀌거나 작업 공간이 비워지거나 앱이 종료될 때까지 메모리에 유지됩니다. 재인식은 사이드바 축소 이미지가 아닌 원본 픽셀을 사용합니다. 재인식용 임시 PNG는 완료·실패·취소 후 삭제됩니다.

## Python API

Python 패키지와 인식 백엔드가 설치된 환경에서 사용하는 예제입니다. EXE 안에서 직접 실행하는 코드는 아닙니다.

```python
import molrecognizer

# 이미지에서 SMILES 또는 좌표가 있는 분자 객체 얻기
smiles = molrecognizer.recognize("molecule.png")
mol = molrecognizer.recognize_to_molecule("molecule.png")
print(smiles, mol.num_atoms, mol.num_bonds)

# SMILES 변환 및 원자가 검사
mol = molrecognizer.smiles_to_molecule("CCO")
print(molrecognizer.molecule_to_smiles(mol))
print(molrecognizer.check_valence(mol))
```

선택적인 MolScribe GPU 모드:

```python
smiles = molrecognizer.recognize(
    "molecule.png", backend="molscribe", device="cuda"
)
```

분자를 프로그래밍 방식으로 편집하는 추가 예제는 [영문 API 안내](README.md#python-api)를 참고하세요.

## 문제 해결

- **`molrecognizer` 명령을 찾을 수 없음:** uv 도구는 `uv tool update-shell` 후 터미널을 다시 여세요. Conda/venv는 해당 환경을 활성화합니다. Linux에서는 `command -v molrecognizer`로 경로를 확인하세요.
- **OSRA를 찾을 수 없음:** Windows는 `$env:OSRA_EXECUTABLE`, `Get-Command osra.exe`; Linux는 `command -v osra`, `printenv OSRA_EXECUTABLE`을 확인합니다. 오래된 환경 변수는 번들 OSRA보다 우선합니다.
- **사전 또는 DLL 누락:** 전체 런타임을 복원하고 `chain.txt`, `spelling.txt`, `superatom.txt`를 확인하세요. EXE만 복사하지 마세요.
- **캡처 단축키가 작동하지 않음:** 네이티브 Windows/Linux에서는 포커스를, WSLg에서는 도우미 실행 권한과 단축키 충돌을 확인하세요. 허용된 다른 도구로 캡처한 파일을 Open Image로 열 수도 있습니다.
- **UI 크기가 맞지 않음:** 해당 모니터에서 **Fit / A− / A+**를 사용하세요.
- **Linux에서 디스플레이 또는 Qt 플러그인 오류:** 정상적인 데스크톱/WSLg 세션에서 실행하고 배포판의 Qt 런타임 라이브러리를 확인하세요. 그래픽 환경 없는 터미널만으로는 GUI를 표시할 수 없습니다.
- **인식 오류:** 선명한 분자 하나만 잘라서 인식하고 후보와 원본을 수동으로 비교하세요. OSRA에는 알려진 입체화학 인식 오류가 있습니다.

로그는 Linux의 `~/.molrecognizer/molrecognizer.log`, Windows의 `%USERPROFILE%\.molrecognizer\molrecognizer.log`에 있으며 실행할 때마다 새로 기록됩니다. [문제 보고](https://github.com/Hengyuan1/molecule-recognizer/issues)에는 버전, 재현 절차와 공개 가능한 예제를 포함하되, 기밀 연구 이미지나 개인정보가 담긴 로그는 올리지 마세요.

## 테스트와 개발 문서

소스 폴더에서 실행합니다.

```bash
# 모델 또는 OSRA가 필요 없는 빠른 테스트
uv run pytest tests/ -m "not slow"

# 선택적 MolScribe 통합 테스트: 첫 실행 시 모델 다운로드 가능
uv run --extra molscribe pytest tests/ -m slow
```

[상세 기능](README.md#features) · [프로젝트 구조](README.md#project-structure) · [변경 이력](CHANGELOG.md) · [Windows 빌드 안내](packaging/windows/README.md) · [릴리스 검증](packaging/windows/audits/0.3.0-final/VALIDATION.md)(영문). 자동 테스트와 소유자의 초기 테스트는 완전한 새 시스템 검증이나 인식 정확도 보증이 아닙니다.

## 라이선스

MolRecognizer 앱 코드는 [MIT 라이선스](LICENSE)를 따릅니다. Windows 패키지의 OSRA 등 타사 구성 요소에는 각각의 라이선스가 적용됩니다. [타사 고지](packaging/windows/THIRD-PARTY-NOTICES.md) 및 **Help → Third-party licenses**를 확인하세요. 앱의 MIT 라이선스가 타사 조건을 대체하지 않습니다.
