.PHONY: build clean install

build:
	uv run --all-groups -m PyInstaller -y main.spec

install:
	chmod +x dist/github-actions-manager
	cp ./dist/github-actions-manager ~/Applications/
	@echo "✅ Installed to ~/Applications/github-actions-manager"

clean:
	rm -rf build/ dist/ *.spec.bak

.DEFAULT_GOAL := build
