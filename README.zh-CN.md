# Molecule Recognizer

[English](README.md) | 简体中文 | [한국어](README.ko.md) | [Русский](README.ru.md) | [Français](README.fr.md)

从截图、论文和网页图片中识别分子结构，转换为 SMILES，交互式修改识别结果，并生成、保存或复制 XYZ 三维坐标，适用于计算化学工作流程。

**版本 [0.3.0](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0)** — 提供内置 OSRA 的 Windows 便携版，以及 Linux/Python 应用。[下载 Windows 版](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip)。

![MolRecognizer：原始图片、可编辑的二维分子结构和并排显示的三维结构](docs/media/UI-demo.png)

双击已生成的三维预览，即可与二维画布并排比较。拖动分隔条调整两侧宽度；二维编辑器和 SMILES 仍可使用。

本页介绍安装和日常使用；详细功能说明、开发与发布记录可参阅[英文 README](README.md)及文中链接。这里只翻译文档，软件界面的按钮和菜单名称仍为英文，因此操作说明保留其原名。

## 快速导航

- [Windows 使用方法](#windows-使用方法)
- [Linux 使用方法](#linux-使用方法)
- [OSRA 与可选依赖](#osra-与可选依赖)
- [识别、编辑与导出](#识别编辑与导出)
- [快捷键](#快捷键) · [Python API](#python-api) · [常见问题](#常见问题)

## Windows 使用方法

### 便携版 EXE：无需 Python、Conda 或 WSL

1. 下载 [MolRecognizer-0.3.0-windows-x64.zip](https://github.com/Hengyuan1/molecule-recognizer/releases/download/v0.3.0/MolRecognizer-0.3.0-windows-x64.zip)（159 MiB）。
2. 将**整个 ZIP** 解压到路径较短、可写入的固定目录，例如 `C:\Users\YourName\Apps`。避免层级过深的目录。
3. 打开解压后 `MolRecognizer` 文件夹中的 `MolRecognizer.exe`。
4. 保留 `_internal`、`tools`、工作进程 EXE 及所有配套文件。**不能只复制主 EXE，也不要直接在 ZIP 中运行。**可为该 EXE 创建桌面快捷方式。

运行环境：**Windows 10/11 x64**；截图功能使用 .NET Framework 4.x。程序已包含 **OSRA 2.2.4**、字典、DLL、Python/Qt/RDKit 运行时和预编译的截图工具，无需另行安装 OSRA，也不需要运行 PowerShell 脚本。便携包不包含 MolScribe 或其模型权重。

更新时先关闭程序，将新版解压到新目录，测试后再修改快捷方式的目标。不要混合不同版本的文件。

### 下载文件的区别与安全提示

- `MolRecognizer-0.3.0-windows-x64.zip`：可直接运行的 Windows 应用，普通用户下载这个即可。
- `MolRecognizer-0.3.0-sources.zip`：同一版本的应用及依赖源代码、补丁和构建说明，供开发者检查或重新构建。它不是旧版本，也不是运行程序所必需的文件。
- `.zip.sha256`：对应 ZIP 的校验值文件，用于检查下载是否损坏或发生变化。
- GitHub 自动生成的 “Source code” 下载不是 Windows 应用，也不能代替包含依赖源代码的 `sources.zip`。

在存放 ZIP 和校验文件的目录中打开 PowerShell：

```powershell
Get-FileHash .\MolRecognizer-0.3.0-windows-x64.zip -Algorithm SHA256
Get-Content .\MolRecognizer-0.3.0-windows-x64.zip.sha256
```

比较两者的 SHA-256。校验一致不等于数字签名，也不能保证软件安全。应用尚未进行代码签名，Windows 可能显示安全警告。请确认下载来源，**不要关闭杀毒软件或绕过单位的安全策略**。

发布包与经过测试的 ZIP 完全相同。包内部分文档保留了构建时的 “not published” 状态；[发布页面](https://github.com/Hengyuan1/molecule-recognizer/releases/tag/v0.3.0)记录了之后的正式发布。`v0.3.0` 标签对应实际构建所用的源码，`main` 还包含后续文档更新。

### 在 PowerShell 中从源码运行

使用便携版的用户可以跳过此节。原生 Windows Python 或经单位允许的 Conda 环境均可运行，无需 WSL。

如需安装 Git 和 uv：

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

重新打开 PowerShell，然后获取源码：

```powershell
git clone --branch main https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
```

也可以下载 GitHub 上 `main` 分支的源码 ZIP，解压后进入包含 `pyproject.toml` 的目录。选择以下一种安装方式。

**方式 A：uv 可编辑工具，可从任意目录启动。**

```powershell
uv tool install --python 3.11 --editable .
uv tool update-shell
```

重新打开 PowerShell，运行：

```powershell
molrecognizer
```

保留源码目录；可编辑安装直接使用其中的文件。如果移动源码目录，需要从新位置重新安装工具。

**方式 B：Conda / Miniconda。**

```powershell
conda create -n molrecognizer python=3.11 -y
conda activate molrecognizer
python -m pip install -e .
molrecognizer
```

以后每次打开新终端，先执行 `conda activate molrecognizer`，再运行 `molrecognizer`。

**开发方式：**也可在仓库目录运行 `uv sync --python 3.11`，然后用 `uv run molrecognizer` 启动，而不安装为工具。

### 为 Windows 源码版配置 OSRA

源码安装**不会自动安装 OSRA**。可以使用完整的 Windows OSRA 运行时，也可以使用已解压便携包中的 `MolRecognizer\tools\osra`。必须保留 DLL、字典及其他配套文件。编译方法见 [OSRA 构建说明](packaging/windows/OSRA-BUILD.md)（英文）。

在当前 PowerShell 会话中指定真实路径：

```powershell
$env:OSRA_EXECUTABLE = "C:\path\to\OSRA\bin\osra.exe"
& $env:OSRA_EXECUTABLE --version
molrecognizer
```

如果使用便携包自带的 OSRA，路径应以 `MolRecognizer\tools\osra\bin\osra.exe` 结尾。保存为用户环境变量：

```powershell
[Environment]::SetEnvironmentVariable(
    "OSRA_EXECUTABLE",
    "C:\path\to\OSRA\bin\osra.exe",
    "User"
)
```

保存后重新打开 PowerShell。也可只为指定的 Conda 环境设置：

```powershell
conda activate molrecognizer
conda env config vars set OSRA_EXECUTABLE="C:\path\to\OSRA\bin\osra.exe"
conda deactivate
conda activate molrecognizer
```

### Windows 截图与屏幕缩放

让 MolRecognizer 保持键盘焦点，将光标移到需要截图的笔记本屏幕或扩展显示器，按 **Alt+Y** 或 **Ctrl+Shift+S**。绘制矩形后可拖动选区、调整边或角，按 **Enter** 或点击 **Recognize** 开始识别。**Esc**、右键或 **Cancel** 取消；方向键移动 1 像素，配合 Shift 移动 10 像素。也可点击 **Screenshot**。

原生 Windows 的快捷键**不是全局快捷键**，应用必须拥有键盘焦点。每次只捕获一台显示器；需要换屏时先取消，再移动光标重新截图。

便携版使用预编译截图工具；Python 源码版通过 Windows PowerShell 的 `Add-Type` 编译 C# 辅助程序，可能受单位安全策略限制。无需安装 Snipaste；如果截图被阻止，可用获准的截图工具保存图片，再通过 **Open Image** 导入。

跨显示器拖动结束后会自动调整窗口。右下角 **A− / A+** 调整界面大小，点击百分比恢复该屏幕的建议缩放，**Fit** 重新适配窗口尺寸。设置按显示器分别保存。

### 可选方式：WSL2 / WSLg

WSL 只是运行 Linux 应用的另一种方式，**不是 Windows EXE 或 Conda 方案的要求**。仅在单位允许时使用。

在带 WSLg 的 Ubuntu/WSL2 中，按下方 Linux 步骤安装 **Linux 版 OSRA 和 Python/uv**，从 Ubuntu 终端运行 `molrecognizer`。不要给 Linux 应用配置 Windows `osra.exe`。

WSLg 支持程序运行期间的**全局 Windows Alt+Y**，前提是 Windows 辅助程序可启动且快捷键未被其他应用占用。截图使用光标所在的 Windows 显示器，需要 PowerShell 互操作及运行辅助程序的权限。WSLg 的菜单和重试面板在主窗口内显示，以减少弹窗显示问题。

## Linux 使用方法

Linux 版是使用本地 OSRA 的 Python 桌面应用，需要图形桌面环境。以下 Bash 命令以 Ubuntu/Debian 为例，其他发行版请使用对应的软件包。

### 安装 OSRA

对于提供 OSRA 软件包的发行版：

```bash
sudo apt update
sudo apt install git osra
osra --version
```

软件包是否可用及其版本取决于发行版，可能与 Windows 包中的 OSRA 2.2.4 不同。已有可用 OSRA 时可以继续使用，不必重复安装。自定义路径示例：

```bash
export OSRA_EXECUTABLE="/path/to/OSRA/bin/osra"
"$OSRA_EXECUTABLE" --version
```

替换为实际路径；如需在后续终端中保留设置，将 `export` 行加入 `~/.bashrc` 或所用 shell 的启动文件。没有合适软件包时，可从 [OSRA 项目](https://sourceforge.net/projects/osra/)获取源码并按其说明构建。

### 安装和启动 MolRecognizer

需要 **Python 3.10 或更高版本**；示例使用 3.11。选择 uv 方式时，先按[官方说明](https://docs.astral.sh/uv/getting-started/installation/)安装 uv，然后获取源码：

```bash
git clone --branch main https://github.com/Hengyuan1/molecule-recognizer.git
cd molecule-recognizer
```

**方式 A：uv 可编辑工具。**

```bash
uv tool install --python 3.11 --editable .
uv tool update-shell
```

新开终端后，可从任意目录启动，无需激活环境：

```bash
molrecognizer
```

请保留源码目录；移动目录后需要重新安装。

**方式 B：pip 虚拟环境。**需要已安装 Python 3.10+ 及其 `venv` 支持。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
molrecognizer
```

以后在新终端中先激活相同环境：

```bash
source /path/to/molecule-recognizer/.venv/bin/activate
molrecognizer
```

**开发方式：**在仓库中运行 `uv sync --python 3.11` 和 `uv run molrecognizer`。也可从其他目录启动：

```bash
uv run --project /path/to/molecule-recognizer molrecognizer
```

### Linux 截图

应用保持焦点，将光标移到目标屏幕，按 **Alt+Y** 或 **Ctrl+Shift+S**。Qt 无边框选区支持绘制、移动和调整大小；Enter 确认，Esc 取消。原生 Linux 不注册全局截图快捷键。

- **X11：**优先使用 Qt 截图，通常无需额外软件；`scrot` 可作为备用。
- **Wayland：**能否截图取决于桌面和合成器。`grim` 只适用于兼容的合成器，并非所有 Wayland 桌面的通用解决方案；程序也会尝试已安装的 `gnome-screenshot`。
- 截图失败、黑屏或内容错误时，使用桌面自带截图工具保存选区，再通过 **Open Image** 导入。

按桌面类型选择需要的可选工具：

```bash
# X11 备用工具
sudo apt install scrot

# 兼容的 Wayland 合成器备用工具
sudo apt install grim
```

在 WSLg 内运行时，请使用上方 WSLg 的 Windows 截图说明。

## OSRA 与可选依赖

源码安装自动安装 RDKit、PySide6、Pillow 和 NumPy（`numpy<2`），详见 [pyproject.toml](pyproject.toml)。OSRA 是独立的原生可执行程序，不是 Python wheel，`pip` 和 `uv sync` 不会安装它。Windows 便携版已经包含 OSRA。

显式设置的 `OSRA_EXECUTABLE` 始终优先，必须指向可用的程序。没有该设置时：

- **Windows 便携版：**依次查找 EXE 旁的 `tools/osra/bin`、`.tools/osra/bin`，最后查找 `PATH`。
- **Python 源码版：**先查找 `PATH`，再查找项目的 `.tools/osra/bin`、`tools/osra/bin`。

项目内的 OSRA 可采用以下目录结构；Windows 中将 `osra` 换成 `osra.exe`：

```text
.tools/osra/
├── bin/
│   ├── osra
│   └── 所需的运行库及其他文件
└── share/
    ├── chain.txt
    ├── spelling.txt
    └── superatom.txt
```

在所选 OSRA 安装目录的 `share/osra`、`share` 或 `bin` 中找到全部三个字典时，程序会自动传入绝对路径，避免依赖当前工作目录。其他运行时文件也必须完整保留。

### 可选的 MolScribe 后端

根据实际使用的环境选择一种安装命令：

```bash
# uv 开发环境
uv sync --extra molscribe

# uv 可编辑工具，从源码目录执行
uv tool install --python 3.11 --editable --with molscribe --with huggingface-hub .

# 已激活的 pip / Conda 环境
python -m pip install -e ".[molscribe]"
```

安装可选依赖不会替换默认 OSRA 后端。使用 Python API 时显式指定 `backend="molscribe"`；首次运行可能下载模型权重。GPU 模式还需要兼容的 CUDA 版 PyTorch。此操作不会把 MolScribe 添加到已有的便携版 EXE 中。

## 识别、编辑与导出

1. 点击 **Open Image** 或截图，只截取一个分子。**Load SMILES** 不依赖 OSRA，可直接载入 SMILES。
2. 对照原图检查二维结构和 SMILES，尤其是原子标签、环闭合、键级、电荷及立体化学。价态检查通过不代表识别正确；图片包含多个结构时只载入第一个有效结果。
3. 使用工具栏手动修正，或点击 **Retry recognition** 比较其他结果。撤销和重做保留连接关系及立体信息。
4. 点击 **Render** 生成三维坐标；双击预览打开并排比较面板，拖动分隔条调整宽度。三维视图左键拖动旋转、右键拖动平移、滚轮缩放。
5. 修改二维结构后，再次点击 **Render** 更新三维结果。
6. **Copy / Export** 用于 SMILES；**Save xyz / Copy xyz** 保存或复制完整 XYZ 文本，下拉菜单可选 Angstrom（Å，默认）或 Bohr。

注意区分：**View → Fit structure** 只调整二维视图，不改变坐标和键的位置；**Format** 重新生成二维布局；**Clean** 清空工作区；右下角 **Fit** 调整应用窗口大小。

### 复杂结构的重新识别

初次识别结束或失败后，可点击 **Retry recognition**。程序使用原始分辨率图片比较三种本地 OSRA 方案：自适应阈值、100 dpi 解释和灰度阈值 0.35。评分不是正确率，也不会自动替换结果。

确认需要替换时点击 **Use selected**；**Keep current** 或 Esc 保留现有编辑。**Stop retries** 停止继续尝试，但已完成的候选仍可查看。替换可整体撤销。接受新结果后，要重新 Render 才能导出更新后的 XYZ。

每次尝试最多为 15 秒 OSRA 处理加 10 秒进程宽限时间，三次最多约 75 秒，可随时取消。所有候选都可能有误；从原始 PDF/矢量图重新截取更清晰的图片，通常比放大小 PNG 更有效。

### 工具与显示

- **Select：**点击原子替换元素，拖动移动；空白处拖动框选，拖动选区整体移动；点击键循环切换键级。
- **Bond：**下拉选择 Single/Double/Triple/Wedge/Dash；点击原子添加相连原子，拖动原子创建键。楔形键/虚楔键用于表达立体化学。
- **Atom / Eraser：**添加或替换原子／删除原子和键；支持框选后批量删除。
- **Ring：**添加苯环或六、五、四、三元环，可连接到原子或键，或放置独立环；拖动调整方向。
- **Charge ⊕/⊖ / PT：**调整形式电荷／打开周期表选择元素。
- **Undo / Redo：**撤销或恢复原子、键、连接关系、坐标及立体标记。
- 芳香环以凯库勒式交替单、双键显示；普通 O–H、N–H 以 OH、NH、NH₂ 等紧凑标签显示，分子数据和 SMILES 不变。具有同位素、映射、电荷或立体标记的氢仍显式显示。
- 保留 OSRA 识别出的二维坐标、单/双键分配和楔形/虚楔形标记，便于与原图对照；识别错误仍须手动修正。Format 会重新计算布局并检查立体信息，不能代替对原始识别结果的核对。
- 2D 画布滚轮缩放，中键或右键拖动平移。关闭三维比较面板可恢复完整二维画布。

## 快捷键

| 操作 | 快捷键 |
| --- | --- |
| 打开图片 | Ctrl+O |
| 截图 | Ctrl+Shift+S / Alt+Y |
| 导出 SMILES | Ctrl+E |
| 撤销 / 重做 | Ctrl+Z / Ctrl+Shift+Z |
| 退出 | Ctrl+Q |
| 删除选区 | Delete / Backspace |
| 放大 / 缩小界面 | Ctrl+Alt++ / Ctrl+Alt+- |
| 重置界面缩放 | Ctrl+Alt+0 |

原生 Windows 和 Linux 的截图快捷键需要应用拥有焦点；只有上述 WSLg 辅助程序提供全局 Alt+Y。

## 隐私与临时文件

识别在本地进行，不会将图片上传到 NCI OSRA 网站。Windows 截图工具将屏幕和选区保存在内存中，不写入截图文件；Linux 命令行备用工具可能创建临时 PNG，读取后删除。识别过程所需的临时图片在处理后删除。

原始图片保存在应用内存中供 Retry recognition 使用，直到被替换、工作区清空或应用关闭；重试使用原始像素而不是侧栏缩略图。重试临时 PNG 在完成、失败或取消后删除。

## Python API

以下示例用于已安装 Python 包及识别后端的环境，而非直接在 EXE 中运行：

```python
import molrecognizer

# 图片识别为 SMILES 或带坐标的分子对象
smiles = molrecognizer.recognize("molecule.png")
mol = molrecognizer.recognize_to_molecule("molecule.png")
print(smiles, mol.num_atoms, mol.num_bonds)

# SMILES 转换与价态检查
mol = molrecognizer.smiles_to_molecule("CCO")
print(molrecognizer.molecule_to_smiles(mol))
print(molrecognizer.check_valence(mol))
```

可选 MolScribe GPU 模式：

```python
smiles = molrecognizer.recognize(
    "molecule.png", backend="molscribe", device="cuda"
)
```

更多分子编辑示例见[英文 API 说明](README.md#python-api)。

## 常见问题

- **找不到 `molrecognizer`：**uv 工具用户运行 `uv tool update-shell` 后重新打开终端；Conda/venv 用户先激活对应环境。Linux 用 `command -v molrecognizer` 检查实际启动路径。
- **找不到 OSRA：**Windows 检查 `$env:OSRA_EXECUTABLE`、`Get-Command osra.exe`；Linux 检查 `command -v osra`、`printenv OSRA_EXECUTABLE`。旧的环境变量会覆盖便携版自带 OSRA。
- **缺少字典或 DLL：**恢复完整运行时，检查 `chain.txt`、`spelling.txt` 和 `superatom.txt`。不要只复制可执行文件。
- **截图快捷键无反应：**原生 Windows/Linux 先确保应用拥有焦点；WSLg 检查辅助程序权限及快捷键占用。也可用其他获准工具截图后 Open Image。
- **界面尺寸不合适：**在对应显示器上使用 **Fit** 和 **A− / A+**。
- **Linux 无显示或 Qt 插件错误：**在有效的桌面或 WSLg 会话中运行，并检查发行版所需的 Qt 运行库；无图形环境的终端不能显示 GUI。
- **识别错误：**尽量紧密截取单个清晰结构，比较重试候选并人工核对。OSRA 存在已知的立体化学识别错误。

日志位于 Linux 的 `~/.molrecognizer/molrecognizer.log` 或 Windows 的 `%USERPROFILE%\.molrecognizer\molrecognizer.log`，每次启动刷新。[反馈问题](https://github.com/Hengyuan1/molecule-recognizer/issues)时请附版本、复现步骤及可公开分享的示例，勿上传机密研究图片或私人日志。

## 测试与开发文档

在源码目录运行：

```bash
# 快速测试，无需模型或 OSRA
uv run pytest tests/ -m "not slow"

# 可选 MolScribe 集成测试，首次可能下载模型
uv run --extra molscribe pytest tests/ -m slow
```

[完整功能列表](README.md#features) · [项目结构](README.md#project-structure) · [更新记录](CHANGELOG.md) · [Windows 构建指南](packaging/windows/README.md) · [发布验证](packaging/windows/audits/0.3.0-final/VALIDATION.md)（这些详细文档为英文）。自动测试和用户初步测试不等于完整的全新系统测试，也不保证识别准确率。

## 许可证

MolRecognizer 应用代码采用 [MIT 许可证](LICENSE)。Windows 包中的 OSRA 等第三方组件保留各自的许可证；详见[第三方声明](packaging/windows/THIRD-PARTY-NOTICES.md)及 **Help → Third-party licenses**。应用的 MIT 许可证不会替代这些组件的条款。
