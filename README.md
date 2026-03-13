# github-actions-manager

Manage GitHub Actions workflows: download artifacts and delete workflow runs.

By default, all artifact files are flattened into a single output directory. The outer `artifact.zip` wrapper is automatically removed.

## Features

- ⏳ **Auto-wait for workflows**: Waits for the workflow to complete before downloading artifacts.
- ✅ **Status validation**: Only downloads artifacts if the workflow concluded successfully.
- 🔔 **Desktop notifications**: Sends desktop notifications on Linux when workflow completes.
- 🎯 **Smart flattening**: Automatically flattens artifact directory structure (configurable).
- 🗑️ **Run management**: Delete all workflow runs in a repository with a single command.
- 🔐 **Flexible authentication**: Supports both `GITHUB_TOKEN` env var and `ghtoken` package.

## Installation

### Option 1: Install pre-built binary

```bash
make install
```

This builds and installs the executable to `~/Applications/github-actions-manager`.

### Option 2: Build from source

```bash
make build
```

This creates an executable in the `dist/` directory. You can then copy it to your `PATH`:

```bash
cp dist/github-actions-manager ~/.local/bin/
```

## Usage

### Requirements

You need a GitHub token with appropriate permissions. Set it via:

```bash
export GITHUB_TOKEN=your_github_token
```

### Commands

The tool uses subcommands for different tasks:

#### 1. Download Artifacts

Download artifacts from a specific workflow run.

```bash
# Basic usage
github-actions-manager download wisdom-valley/knowlify-ai 19810307537

# Using full URL
github-actions-manager download https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537

# Custom output directory
github-actions-manager download wisdom-valley/knowlify-ai 19810307537 ./my-artifacts
```

**Options:**
- `--no-flatten`: Keep artifacts in separate subdirectories.
- `--no-wait`: Download immediately without waiting for completion.
- `--poll-interval <sec>`: Polling interval (default: 60).
- `--timeout <sec>`: Maximum wait time (default: 1800).

#### 2. Delete Workflow Runs

Delete all workflow runs in a repository.

```bash
# Using owner/repo
github-actions-manager delete-runs wisdom-valley/knowlify-ai

# Using Actions URL
github-actions-manager delete-runs https://github.com/wisdom-valley/knowlify-ai/actions
```

## Desktop Notifications

Supports desktop notifications on Linux via `plyer` or `notify-send`. Notifications are sent when a tracked workflow completes (success/failure/timeout).

## Development

### Setup

```bash
uv sync --all-groups
```

### Build

```bash
make build    # Build executable to dist/
make install  # Build and install
make clean    # Clean build artifacts
```

## Changelog

### v0.1.0
- ✨ **New**: Renamed to `github-actions-manager`
- ✨ **New**: Added `delete-runs` subcommand to clear workflow history
- ✨ **New**: Refactored to use subcommands (`download`, `delete-runs`)
- 🔧 **Improved**: Updated documentation and help messages
