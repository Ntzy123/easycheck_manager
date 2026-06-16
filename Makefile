# ============================================================================
# Makefile - easycheck_manager
# Cross-platform (Windows / Linux / macOS)
# ============================================================================

# --- OS detection ---
ifeq ($(OS),Windows_NT)
    PYTHON      = python
    VENV_PYTHON = .venv\Scripts\python
    VENV_PIP    = .venv\Scripts\pip
    SEP         = ;
    NULL        = nul
else
    PYTHON      = python3
    VENV_PYTHON = .venv/bin/python
    VENV_PIP    = .venv/bin/pip
    SEP         = :
    NULL        = /dev/null
endif

APP_NAME = easycheck_manager

.PHONY: help setup mirror run build test

# --- File target: only creates venv when the Python interpreter is missing ---
$(VENV_PYTHON):
	$(PYTHON) -m venv .venv

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "  setup    Create venv and install dependencies"
	@echo "  mirror   Switch pip to Tsinghua mirror"
	@echo "  run      Run the application"
	@echo "  test     Run tests with pytest"
	@echo "  build    Package with PyInstaller (timestamped name)"
	@echo "  help     Show this help"

setup: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install --upgrade pip > $(NULL) 2>&1
	$(VENV_PIP) install -e .
	@echo "Setup complete."

mirror: $(VENV_PYTHON)
	$(VENV_PIP) config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
	@echo "Mirror set."

run: $(VENV_PYTHON)
	@$(VENV_PYTHON) -m $(APP_NAME)

test: $(VENV_PYTHON)
	$(VENV_PIP) install pytest pytest-cov 2>&1
	$(VENV_PYTHON) -m pytest tests/ -v --cov=src/$(APP_NAME) --cov-report=term-missing

build: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install --upgrade pip > $(NULL) 2>&1
	$(VENV_PIP) install -e .
	$(VENV_PYTHON) -m PyInstaller --onefile --name=$(APP_NAME)_$(shell $(PYTHON) -c "import datetime;print(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))") --icon=res/$(APP_NAME).ico --add-data "res/sound.mp3$(SEP)res" --add-data "res/$(APP_NAME).ico$(SEP)res" -c src/$(APP_NAME)/__main__.py
	@echo "Build complete: dist/"
