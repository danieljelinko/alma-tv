
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from pathlib import Path

from alma_tv.cli import app

runner = CliRunner()

@pytest.fixture
def mock_env():
    with patch("shutil.which", return_value="/usr/bin/uv"), \
         patch("getpass.getuser", return_value="testuser"), \
         patch("pathlib.Path.cwd", return_value=Path("/app")), \
         patch("pathlib.Path.home", return_value=Path("/home/testuser")):
        yield

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.database_url = "sqlite:////tmp/test.db"
    settings.log_file = Path("/tmp/test.log")
    with patch("alma_tv.cli.get_settings", return_value=settings):
        yield settings

def test_system_install_dry_run(mock_env, mock_settings):
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value="ExecStart={uv_path} run foo\nUser={user}"), \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("pathlib.Path.write_text") as mock_write:
        
        result = runner.invoke(app, ["system", "install", "--dry-run"])
        
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
            import traceback
            traceback.print_tb(result.exc_info[2])
            
        assert result.exit_code == 0
        assert "--- alma-scheduler.service ---" in result.stdout
        assert "ExecStart=/usr/bin/uv run foo" in result.stdout
        assert "User=testuser" in result.stdout
        
        # Should not write files
        mock_write.assert_not_called()

def test_system_install_real(mock_env, mock_settings):
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value="ExecStart={uv_path} run foo"), \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("pathlib.Path.write_text") as mock_write, \
         patch("subprocess.run") as mock_run:
        
        result = runner.invoke(app, ["system", "install"])
        
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
        
        assert result.exit_code == 0
        assert "Installed alma-scheduler.service" in result.stdout
        
        # Should write files
        assert mock_write.call_count == 4 # 4 services
        
        # Should reload daemon
        mock_run.assert_called_with(["systemctl", "--user", "daemon-reload"], check=True)
