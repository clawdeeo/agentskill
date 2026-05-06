from test_support import create_sample_repo

from agentskill.lib.output_profiles import (
    DEFAULT_OUTPUT_PROFILE,
    SUPPORTED_OUTPUT_PROFILES,
    validate_output_profile,
)
from agentskill.main import main


class TestValidateOutputProfile:
    def test_concise_is_valid(self):
        assert validate_output_profile("concise") == "concise"

    def test_comprehensive_is_valid(self):
        assert validate_output_profile("comprehensive") == "comprehensive"

    def test_split_is_valid(self):
        assert validate_output_profile("split") == "split"

    def test_default_is_concise(self):
        assert DEFAULT_OUTPUT_PROFILE == "concise"

    def test_supported_profiles_include_all_three(self):
        assert set(SUPPORTED_OUTPUT_PROFILES) == {"concise", "comprehensive", "split"}

    def test_invalid_profile_raises_value_error(self):
        try:
            validate_output_profile("verbose")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output profile" in str(exc)

    def test_empty_profile_raises_value_error(self):
        try:
            validate_output_profile("")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output profile" in str(exc)

    def test_normalizes_uppercase(self):
        assert validate_output_profile("Concise") == "concise"

    def test_normalizes_whitespace(self):
        assert validate_output_profile("  concise  ") == "concise"

    def test_error_message_lists_allowed_values(self):
        try:
            validate_output_profile("detailed")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "concise, comprehensive, split" in str(exc)


class TestGenerateProfileDefaults:
    def test_generate_defaults_to_concise(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo)])

        assert exit_code == 0
        assert "## 1. Overview\n" in capsys.readouterr().out

    def test_generate_explicit_concise(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "concise"])

        assert exit_code == 0
        assert "## 1. Overview\n" in capsys.readouterr().out

    def test_generate_comprehensive_succeeds(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "comprehensive"])

        assert exit_code == 0
        output = capsys.readouterr().out
        assert output.startswith("# AGENTS.md\n\n## 1. Overview\n")

    def test_generate_split_is_accepted_but_not_implemented(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err and "not implemented yet" in err

    def test_generate_invalid_profile_fails(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "verbose"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_generate_concise_matches_default_output(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)

        exit_code_default = main(["generate", str(repo)])
        assert exit_code_default == 0
        default_out = capsys.readouterr().out

        exit_code_concise = main(["generate", str(repo), "--profile", "concise"])
        assert exit_code_concise == 0
        concise_out = capsys.readouterr().out

        assert default_out == concise_out


class TestUpdateProfileDefaults:
    def test_update_defaults_to_concise(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo)])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()

    def test_update_explicit_concise(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "concise"])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()

    def test_update_comprehensive_succeeds(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "comprehensive"])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()

    def test_update_split_is_accepted_but_not_implemented(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err and "not implemented yet" in err

    def test_update_invalid_profile_fails(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "verbose"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_update_concise_matches_default_output(self, tmp_path):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        exit_code_default = main(["update", str(repo_a)])
        assert exit_code_default == 0
        default_text = (repo_a / "AGENTS.md").read_text()

        exit_code_concise = main(["update", str(repo_b), "--profile", "concise"])
        assert exit_code_concise == 0
        concise_text = (repo_b / "AGENTS.md").read_text()

        assert default_text == concise_text
