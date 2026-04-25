"""Commands and workflow extraction from project configs."""

import re
from pathlib import Path
from typing import Dict, List, Optional


def extract_commands(repo_path: str) -> Dict:
    """Extract build, test, and dev commands from project configs."""
    repo = Path(repo_path)
    commands = {
        "build": [],
        "test": [],
        "lint": [],
        "format": [],
        "dev": [],
        "deploy": [],
        "install": [],
        "ci": [],
    }

    _extract_from_package_json(repo, commands)
    _extract_from_makefile(repo, commands)
    _extract_from_justfile(repo, commands)
    _extract_from_cargo(repo, commands)
    _extract_from_pyproject(repo, commands)
    _extract_from_setup_py(repo, commands)
    _extract_from_requirements(repo, commands)
    _extract_from_tox(repo, commands)
    _extract_from_scripts(repo, commands)
    _extract_from_docker(repo, commands)
    _extract_from_github_actions(repo, commands)

    return {k: v for k, v in commands.items() if v}


def _extract_from_package_json(repo: Path, commands: Dict):
    """Extract scripts from package.json."""
    pkg = repo / "package.json"
    if not pkg.exists():
        return

    try:
        import json
        data = json.loads(pkg.read_text(errors='ignore'))
        scripts = data.get("scripts", {})

        script_map = {
            "build": ["build", "build:prod", "build:production", "compile"],
            "test": ["test", "test:ci", "test:coverage", "test:watch", "test:all"],
            "lint": ["lint", "lint:fix", "eslint", "tslint", "check"],
            "format": ["format", "fmt", "prettier", "prettier:write"],
            "dev": ["dev", "start", "serve", "develop", "watch"],
            "deploy": ["deploy", "deploy:prod", "deploy:staging"],
            "install": ["postinstall", "prepare"],
        }

        for category, keys in script_map.items():
            for key in keys:
                if key in scripts:
                    commands[category].append({
                        "name": key,
                        "command": scripts[key],
                        "source": "package.json",
                    })
    except Exception:
        pass


def _extract_from_makefile(repo: Path, commands: Dict):
    """Extract targets from Makefile."""
    makefile = repo / "Makefile"
    if not makefile.exists():
        return

    try:
        content = makefile.read_text(errors='ignore')
        targets = re.findall(r'^([a-zA-Z_-]+):\s*$', content, re.MULTILINE)

        target_map = {
            "build": ["build", "all", "compile", "dist", "bundle"],
            "test": ["test", "test-all", "check", "spec"],
            "lint": ["lint", "lint-fix", "analyze"],
            "format": ["fmt", "format"],
            "dev": ["run", "serve", "dev"],
            "deploy": ["deploy", "deploy-prod", "release", "publish"],
            "install": ["install", "setup"],
            "ci": ["ci"],
        }

        for category, names in target_map.items():
            for name in names:
                if name in targets:
                    commands[category].append({
                        "name": name,
                        "command": f"make {name}",
                        "source": "Makefile",
                    })
    except Exception:
        pass


def _extract_from_justfile(repo: Path, commands: Dict):
    """Extract recipes from justfile."""
    justfile = repo / "justfile"
    if not justfile.exists():
        justfile = repo / "Justfile"
    if not justfile.exists():
        return

    try:
        content = justfile.read_text(errors='ignore')
        recipes = re.findall(r'^([a-zA-Z_-]+)(?:\s*.*?):\s*$', content, re.MULTILINE)

        recipe_map = {
            "build": ["build", "all", "compile", "bundle"],
            "test": ["test", "check", "spec"],
            "lint": ["lint", "analyze"],
            "format": ["fmt", "format"],
            "dev": ["run", "serve", "dev", "watch"],
            "deploy": ["deploy", "release", "publish"],
            "install": ["install", "setup"],
        }

        for category, names in recipe_map.items():
            for name in names:
                if name in recipes:
                    commands[category].append({
                        "name": name,
                        "command": f"just {name}",
                        "source": "justfile",
                    })
    except Exception:
        pass


def _extract_from_cargo(repo: Path, commands: Dict):
    """Extract commands from Cargo.toml metadata."""
    cargo = repo / "Cargo.toml"
    if not cargo.exists():
        return

    commands["build"].append({
        "name": "build",
        "command": "cargo build",
        "source": "Cargo.toml",
    })
    commands["test"].append({
        "name": "test",
        "command": "cargo test",
        "source": "Cargo.toml",
    })
    commands["lint"].append({
        "name": "clippy",
        "command": "cargo clippy",
        "source": "Cargo.toml",
    })
    commands["format"].append({
        "name": "fmt",
        "command": "cargo fmt",
        "source": "Cargo.toml",
    })

    try:
        content = cargo.read_text(errors='ignore')
        if "bench" in content:
            commands["test"].append({
                "name": "bench",
                "command": "cargo bench",
                "source": "Cargo.toml",
            })
    except Exception:
        pass


def _extract_from_pyproject(repo: Path, commands: Dict):
    """Extract commands from pyproject.toml."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.exists():
        return

    try:
        content = pyproject.read_text(errors='ignore')

        if "[tool.poetry]" in content:
            commands["install"].append({
                "name": "install",
                "command": "poetry install",
                "source": "pyproject.toml",
            })
        elif "[tool.flit]" in content:
            commands["install"].append({
                "name": "install",
                "command": "pip install .",
                "source": "pyproject.toml",
            })

        if "[tool.pytest" in content or "pytest" in content:
            commands["test"].append({
                "name": "test",
                "command": "pytest",
                "source": "pyproject.toml",
            })

        if "black" in content:
            commands["format"].append({
                "name": "black",
                "command": "black .",
                "source": "pyproject.toml",
            })

        if "ruff" in content or "mypy" in content:
            commands["lint"].append({
                "name": "lint",
                "command": "ruff check ." if "ruff" in content else "mypy .",
                "source": "pyproject.toml",
            })
    except Exception:
        pass


def _extract_from_setup_py(repo: Path, commands: Dict):
    """Extract install/test commands from setup.py."""
    setup_py = repo / "setup.py"
    if not setup_py.exists():
        return

    commands["install"].append({
        "name": "pip install",
        "command": "pip install -e .",
        "source": "setup.py",
    })
    commands["install"].append({
        "name": "setup.py install",
        "command": "python setup.py install",
        "source": "setup.py",
    })

    try:
        content = setup_py.read_text(errors='ignore')
        if "test_suite" in content or "pytest" in content or "unittest" in content:
            commands["test"].append({
                "name": "setup.py test",
                "command": "python setup.py test",
                "source": "setup.py",
            })
    except Exception:
        pass


def _extract_from_requirements(repo: Path, commands: Dict):
    """Extract install command from requirements.txt."""
    req = repo / "requirements.txt"
    req_dev = repo / "requirements-dev.txt"

    if req.exists():
        commands["install"].append({
            "name": "pip install requirements",
            "command": "pip install -r requirements.txt",
            "source": "requirements.txt",
        })

    if req_dev.exists():
        commands["install"].append({
            "name": "pip install dev requirements",
            "command": "pip install -r requirements-dev.txt",
            "source": "requirements-dev.txt",
        })


def _extract_from_tox(repo: Path, commands: Dict):
    """Extract test environments from tox.ini."""
    tox_ini = repo / "tox.ini"
    if not tox_ini.exists():
        return

    commands["test"].append({
        "name": "tox",
        "command": "tox",
        "source": "tox.ini",
    })

    try:
        content = tox_ini.read_text(errors='ignore')
        # Extract environment names like [testenv:py312] or [testenv:lint]
        envs = re.findall(r'\[testenv:([^\]]+)\]', content)
        for env in envs[:5]:
            commands["test"].append({
                "name": f"tox -e {env}",
                "command": f"tox -e {env}",
                "source": "tox.ini",
            })
    except Exception:
        pass


def _extract_from_scripts(repo: Path, commands: Dict):
    """Extract CLI entry points from scripts/ folder and setup.py console_scripts."""
    scripts_dir = repo / "scripts"
    if scripts_dir.exists() and scripts_dir.is_dir():
        for script in sorted(scripts_dir.iterdir())[:10]:
            if script.is_file() and not script.name.startswith('.'):
                commands["dev"].append({
                    "name": script.name,
                    "command": f"python {scripts_dir.name}/{script.name}",
                    "source": f"{scripts_dir.name}/",
                })

    # Also check setup.py for console_scripts
    setup_py = repo / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text(errors='ignore')
            entry_points = re.findall(r'console_scripts\s*=\s*\[(.*?)\]', content, re.DOTALL)
            for ep_block in entry_points:
                # Extract "name = module.path:function" patterns
                eps = re.findall(r'["\']([\w-]+)["\']\s*=\s*["\']([\w.]+):', ep_block)
                for name, module in eps:
                    commands["dev"].append({
                        "name": name,
                        "command": name,
                        "source": "setup.py console_scripts",
                    })
        except Exception:
            pass


def _extract_from_docker(repo: Path, commands: Dict):
    """Extract Docker-related commands."""
    if (repo / "Dockerfile").exists():
        commands["deploy"].append({
            "name": "docker build",
            "command": "docker build -t app .",
            "source": "Dockerfile",
        })

    if (repo / "docker-compose.yml").exists() or (repo / "docker-compose.yaml").exists():
        compose_file = "docker-compose.yml" if (repo / "docker-compose.yml").exists() else "docker-compose.yaml"
        commands["dev"].append({
            "name": "docker-compose up",
            "command": f"docker-compose -f {compose_file} up",
            "source": compose_file,
        })


def _extract_from_github_actions(repo: Path, commands: Dict):
    """Extract CI commands from GitHub Actions workflows."""
    workflows_dir = repo / ".github" / "workflows"
    if not workflows_dir.exists():
        return

    ci_commands = set()

    for workflow in workflows_dir.glob("*.yml"):
        try:
            content = workflow.read_text(errors='ignore')

            # Extract run commands from workflow steps
            runs = re.findall(r'-\s*run:\s*[\'"]?(.+?)[\'"]?\s*$', content, re.MULTILINE)
            for run_cmd in runs:
                run_cmd = run_cmd.strip()
                if len(run_cmd) < 100:
                    ci_commands.add(run_cmd)
        except Exception:
            continue

    if ci_commands:
        commands["ci"] = [
            {"name": f"ci-{i}", "command": cmd, "source": "GitHub Actions"}
            for i, cmd in enumerate(sorted(ci_commands)[:10], 1)
        ]