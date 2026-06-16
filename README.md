# Easycheck Manager

> 版本: 1.0.0 | 许可: MIT

**Easycheck Manager** 是一个跨平台的 EdgeDriver 自动化管理工具，负责自动检测本地 Microsoft Edge 版本、下载匹配的 EdgeDriver 并设置环境变量，确保 Selenium 自动化脚本始终使用正确的 WebDriver。

---

## 安装

```bash
pip install easycheck-manager

# 如需运行测试
pip install easycheck-manager[test]

# 如需打包为独立可执行文件
pip install easycheck-manager[build]
```

## 快速开始

```python
from easycheck_manager import WebDriverManager

manager = WebDriverManager()
manager.start()
```

## 项目模块结构

```
easycheck_manager/
├── __main__.py              # CLI 入口
├── core.py                  # （预留）
├── utils.py                 # （预留）
└── lib/
    ├── __init__.py
    ├── webdriver_manager.py  # WebDriverManager — 核心类
    └── easycheck_manager.py  # EasycheckManager — （开发中）
```

## 平台支持

| 功能 | Windows | Linux |
|------|---------|-------|
| Edge 路径检测 | 注册表默认路径 / `EDGE_PATH` 环境变量 | `shutil.which()` 搜索 `microsoft-edge`、`microsoft-edge-stable` |
| EdgeDriver 安装目录 | `D:\Program Files\WebDriver\edgedriver_win64\` | `/usr/local/bin/msedgedriver` |
| EdgeDriver 下载地址 | `edgedriver_win64.zip` | `edgedriver_linux64.zip` |
| PATH 设置 | 注册表 `HKCU\Environment` | 无需设置（`/usr/local/bin` 默认在 PATH） |
| 版本获取 | `win32api.GetFileVersionInfo()` | `--version` 命令输出解析 |
| 依赖 | 需要 `pywin32` | 无需 Windows 专有依赖 |

> **路径覆盖（Windows）**：可通过环境变量 `EDGE_PATH` 和 `WEBDRIVER_DIR` 自定义。
