from openbase_coder_cli.services.definitions import ServiceDefinition
from openbase_coder_cli.services.installation import InstallationConfig
from openbase_coder_cli.services import launchd


def test_generate_wrapper_includes_user_bin_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(launchd, "LAUNCHD_WRAPPER_DIR", tmp_path / "launchd")
    monkeypatch.setattr(launchd, "OPENBASE_BASE_DIR", tmp_path / "openbase")

    service = ServiceDefinition(
        name="sample",
        description="Sample",
        command_template="command -v openbase-coder",
        workdir_template="{workspace}",
    )
    config = InstallationConfig(
        workspace_path=str(tmp_path / "workspace"),
        env_file=str(tmp_path / ".env"),
    )

    wrapper = launchd.generate_wrapper(service, config, {})

    assert (
        'export PATH="$HOME/.local/bin:$HOME/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"'
        in wrapper.read_text()
    )
