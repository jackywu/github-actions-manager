.PHONY: build build-cli build-gui clean install

build: build-cli build-gui

build-cli:
	uv run --all-groups -m PyInstaller -y cli.spec

build-gui:
	uv run --all-groups -m PyInstaller -y gui.spec

install:
	chmod +x dist/github-actions-manager
	cp ./dist/github-actions-manager ~/Applications/
	@echo "✅ Installed to ~/Applications/github-actions-manager"

clean:
	rm -rf build/ dist/ *.spec.bak

.DEFAULT_GOAL := build
