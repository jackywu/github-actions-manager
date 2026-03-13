.PHONY: build clean install

build:
	uv run --all-groups -m PyInstaller -y main.spec

install:
	chmod +x dist/github-artifact-downloader
	cp ./dist/github-artifact-downloader ~/Applications/
	@echo "✅ Installed to ~/Applications/github-artifact-downloader"

clean:
	rm -rf build/ dist/ *.spec.bak

.DEFAULT_GOAL := build
