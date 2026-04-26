"""Aggregate analyzer execution for the top-level CLI."""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from time import monotonic

from commands import config as config_command
from commands import git as git_command
from commands import graph as graph_command
from commands import measure as measure_command
from commands import scan as scan_command
from commands import symbols as symbols_command
from commands import tests as tests_command

COMMANDS: dict[str, dict] = {
    "scan": {
        "fn": scan_command.scan,
        "supports_lang": True,
    },
    "measure": {
        "fn": measure_command.measure,
        "supports_lang": True,
    },
    "config": {
        "fn": config_command.detect,
        "supports_lang": False,
    },
    "git": {
        "fn": git_command.analyze,
        "supports_lang": False,
    },
    "graph": {
        "fn": graph_command.build_graph,
        "supports_lang": True,
    },
    "symbols": {
        "fn": symbols_command.extract_symbols,
        "supports_lang": True,
    },
    "tests": {
        "fn": tests_command.analyze_tests,
        "supports_lang": False,
    },
}

ANALYZER_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 0.1


def _command_kwargs(command_name: str, lang_filter: str | None) -> dict:
    if COMMANDS[command_name]["supports_lang"]:
        return {"lang_filter": lang_filter}

    return {}


def run_all(repo: str, lang_filter: str | None = None) -> dict:
    tasks = {
        name: (metadata["fn"], _command_kwargs(name, lang_filter))
        for name, metadata in COMMANDS.items()
    }
    result: dict = {}
    executor = ThreadPoolExecutor(max_workers=len(tasks))

    try:
        futures = {
            executor.submit(command_fn, repo, **kwargs): name
            for name, (command_fn, kwargs) in tasks.items()
        }
        start_times = {future: monotonic() for future in futures}
        pending = set(futures)

        while pending:
            done, not_done = wait(
                pending,
                timeout=POLL_INTERVAL_SECONDS,
                return_when=FIRST_COMPLETED,
            )

            for future in done:
                name = futures[future]

                try:
                    result[name] = future.result()
                except Exception as exc:
                    result[name] = {"error": str(exc)}

                pending.remove(future)

            now = monotonic()
            timed_out = {
                future
                for future in not_done
                if now - start_times[future] >= ANALYZER_TIMEOUT_SECONDS
            }

            for future in timed_out:
                name = futures[future]
                result[name] = {
                    "error": (f"analyzer timed out after {ANALYZER_TIMEOUT_SECONDS}s")
                }

                future.cancel()
                pending.remove(future)

        return result
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def run_many(repos: list[str], lang_filter: str | None = None) -> dict:
    if len(repos) == 1:
        return run_all(repos[0], lang_filter)

    return {repo: run_all(repo, lang_filter) for repo in repos}
