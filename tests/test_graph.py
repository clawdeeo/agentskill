from commands.graph import build_graph
from test_support import create_repo, create_sample_repo


def test_graph_detects_python_import_edge(tmp_path):
    repo = create_sample_repo(tmp_path)
    result = build_graph(str(repo), "python")
    edges = result["python"]["edges"]

    assert {"from": "pkg.main", "to": "pkg.util", "line": 1} in edges


def test_graph_detects_relative_imports_cycles_and_parse_errors(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "pkg/__init__.py": "\n",
            "pkg/a.py": "from .b import run_b\n\n\ndef run_a():\n    return run_b()\n",
            "pkg/b.py": "from .a import run_a\n\n\ndef run_b():\n    return run_a()\n",
            "pkg/bad.py": "def broken(:\n",
        },
    )

    result = build_graph(str(repo), "python")

    assert {"from": "pkg.a", "to": "pkg.b", "line": 1} in result["python"]["edges"]
    assert result["python"]["circular_dependencies"]
    assert "pkg/bad.py" in result["python"]["parse_errors"]


def test_graph_detects_ts_go_and_monorepo_boundaries(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "package.json": "{}\n",
            "src/util.ts": "export function util() { return 1 }\n",
            "src/app.ts": "import './util'\nconst util = require('./util')\n",
            "go.mod": "module example.com/demo\n",
            "pkg/helper/helper.go": "package helper\n",
            "pkg/main.go": 'package main\nimport (\n    "example.com/demo/pkg/helper"\n)\n',
            "services/api/main.py": "\n",
            "services/web/main.py": "\n",
        },
    )

    result = build_graph(str(repo))

    assert {"from": "src/app.ts", "to": "src/util.ts", "line": 1} in result[
        "typescript"
    ]["edges"]

    assert {"from": "pkg", "to": "pkg/helper", "line": 2} in result["go"]["edges"]
    assert result["monorepo_boundaries"]["detected"] is True


def test_graph_detects_java_and_kotlin_internal_imports(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/main/java/com/acme/App.java": (
                "package com.acme;\n\n"
                "import com.acme.service.UserService;\n"
                "import java.util.List;\n\n"
                "public class App {}\n"
            ),
            "src/main/java/com/acme/service/UserService.java": (
                "package com.acme.service;\n\npublic class UserService {}\n"
            ),
            "src/main/kotlin/com/acme/Main.kt": (
                "package com.acme\n\n"
                "import com.acme.service.UserService\n"
                "import kotlinx.coroutines.runBlocking\n\n"
                "fun main() {}\n"
            ),
            "src/main/kotlin/com/acme/service/UserService.kt": (
                "package com.acme.service\n\nclass UserService\n"
            ),
        },
    )

    result = build_graph(str(repo))

    assert {
        "from": "src/main/java/com/acme/App.java",
        "to": "src/main/java/com/acme/service/UserService.java",
        "line": 3,
    } in result["java"]["edges"]

    assert {
        "from": "src/main/kotlin/com/acme/Main.kt",
        "to": "src/main/kotlin/com/acme/service/UserService.kt",
        "line": 3,
    } in result["kotlin"]["edges"]


def test_graph_detects_csharp_and_c_family_internal_edges(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/App.cs": (
                "using System;\n"
                "using Acme.Service.Core;\n\n"
                "namespace Acme.Service;\n\n"
                "public class App {}\n"
            ),
            "src/Core/UserService.cs": (
                "namespace Acme.Service.Core;\n\npublic class UserService {}\n"
            ),
            "src/main.c": (
                '#include "util.h"\n'
                '#include "../include/project/config.h"\n'
                "#include <stdio.h>\n"
            ),
            "src/util.h": "int add(int a, int b);\n",
            "include/project/config.h": '#define APP_NAME "demo"\n',
            "src/app.cpp": '#include "project/service.hpp"\n#include <vector>\n',
            "include/project/service.hpp": "class UserService {};\n",
        },
    )

    result = build_graph(str(repo))

    assert {
        "from": "src/App.cs",
        "to": "src/Core/UserService.cs",
        "line": 2,
    } in result["csharp"]["edges"]

    assert {"from": "src/main.c", "to": "src/util.h", "line": 1} in result["c"]["edges"]

    assert {
        "from": "src/main.c",
        "to": "include/project/config.h",
        "line": 2,
    } in result["c"]["edges"]

    assert {
        "from": "src/app.cpp",
        "to": "include/project/service.hpp",
        "line": 1,
    } in result["cpp"]["edges"]


def test_graph_reports_invalid_repo_paths(tmp_path):
    missing = tmp_path / "missing"

    assert build_graph(str(missing)) == {
        "error": f"path does not exist: {missing}",
        "script": "graph",
    }
