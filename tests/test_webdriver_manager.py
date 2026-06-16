# tests/test_webdriver_manager.py

import os
import sys
import platform
import subprocess
import zipfile
import requests
import pytest
from unittest.mock import patch, MagicMock, call, PropertyMock

from easycheck_manager.lib.webdriver_manager import WebDriverManager


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def win_wd():
    """Windows 环境的 WebDriverManager 实例（未设置 edge_version）"""
    with patch.object(platform, 'system', return_value='Windows'):
        wd = WebDriverManager()
        return wd


@pytest.fixture
def linux_wd():
    """Linux 环境（Edge 已安装）的 WebDriverManager 实例"""
    with patch.object(platform, 'system', return_value='Linux'):
        with patch('shutil.which', return_value='/usr/bin/microsoft-edge'):
            wd = WebDriverManager()
            return wd


@pytest.fixture
def linux_wd_no_edge():
    """Linux 环境（Edge 未安装）的 WebDriverManager 实例"""
    with patch.object(platform, 'system', return_value='Linux'):
        with patch('shutil.which', return_value=None):
            wd = WebDriverManager()
            return wd


# ====================================================================
# __init__
# ====================================================================

class TestInit:
    def test_windows_paths(self, win_wd):
        assert win_wd.is_windows is True
        assert 'msedge.exe' in win_wd.EDGE_PATH
        assert 'WebDriver' in win_wd.BASE_DIR
        assert win_wd.EDGEDRIVER_PATH.endswith('msedgedriver.exe')
        assert 'edgedriver_win64' in win_wd.EDGEDRIVER_PATH

    def test_windows_custom_env_path(self):
        with patch.object(platform, 'system', return_value='Windows'):
            with patch.dict(os.environ, {'EDGE_PATH': r'D:\Custom\msedge.exe'}):
                wd = WebDriverManager()
                assert wd.EDGE_PATH == r'D:\Custom\msedge.exe'

    def test_linux_paths_edge_found(self, linux_wd):
        assert linux_wd.is_windows is False
        assert linux_wd.EDGE_PATH == '/usr/bin/microsoft-edge'
        assert linux_wd.CACHE_DIR == '/tmp/msedgedriver'
        assert linux_wd.EDGEDRIVER_PATH == '/usr/local/bin/msedgedriver'
        assert not hasattr(linux_wd, 'BASE_DIR')

    def test_linux_paths_edge_missing(self, linux_wd_no_edge):
        assert linux_wd_no_edge.EDGE_PATH is None

    def test_linux_ignores_edge_env_var(self):
        """Linux 不使用 EDGE_PATH 环境变量，只用 shutil.which"""
        with patch.object(platform, 'system', return_value='Linux'):
            with patch.dict(os.environ, {'EDGE_PATH': '/should/be/ignored'}):
                with patch('shutil.which', return_value='/usr/bin/microsoft-edge-stable'):
                    wd = WebDriverManager()
                    assert wd.EDGE_PATH == '/usr/bin/microsoft-edge-stable'

    def test_edge_version_default_none(self):
        """使用全新实例，不经过 fixture 注入版本号"""
        with patch.object(platform, 'system', return_value='Windows'):
            wd = WebDriverManager()
            assert wd.edge_version is None

    def test_windows_webdriver_dir_env(self):
        with patch.object(platform, 'system', return_value='Windows'):
            with patch.dict(os.environ, {'WEBDRIVER_DIR': r'E:\Tools'}):
                wd = WebDriverManager()
                assert 'E:\\Tools' in wd.BASE_DIR


# ====================================================================
# _find_edge_linux
# ====================================================================

class TestFindEdgeLinux:
    def test_finds_microsoft_edge(self):
        with patch('shutil.which', side_effect=lambda x: {
            'microsoft-edge': '/usr/bin/microsoft-edge',
            'microsoft-edge-stable': None,
        }.get(x)):
            wd = WebDriverManager.__new__(WebDriverManager)
            result = wd._find_edge_linux()
            assert result == '/usr/bin/microsoft-edge'

    def test_finds_microsoft_edge_stable_as_fallback(self):
        with patch('shutil.which', side_effect=lambda x: {
            'microsoft-edge': None,
            'microsoft-edge-stable': '/usr/bin/microsoft-edge-stable',
        }.get(x)):
            wd = WebDriverManager.__new__(WebDriverManager)
            result = wd._find_edge_linux()
            assert result == '/usr/bin/microsoft-edge-stable'

    def test_returns_none_if_not_found(self):
        with patch('shutil.which', return_value=None):
            wd = WebDriverManager.__new__(WebDriverManager)
            result = wd._find_edge_linux()
            assert result is None

    def test_only_searches_two_binaries(self):
        with patch('shutil.which', return_value=None) as mock_which:
            wd = WebDriverManager.__new__(WebDriverManager)
            wd._find_edge_linux()
            assert mock_which.call_args_list == [
                call('microsoft-edge'),
                call('microsoft-edge-stable'),
            ]


# ====================================================================
# get_file_version
# ====================================================================

class TestGetFileVersion:
    def test_windows_delegates_to_win(self, win_wd):
        with patch.object(win_wd, '_get_file_version_win', return_value='1.2.3.4') as mock:
            result = win_wd.get_file_version("Edge", r"C:\edge.exe")
            mock.assert_called_once_with("Edge", r"C:\edge.exe")
            assert result == '1.2.3.4'

    def test_linux_delegates_to_linux(self, linux_wd):
        with patch.object(linux_wd, '_get_file_version_linux', return_value='5.6.7.8') as mock:
            result = linux_wd.get_file_version("Edge", "/usr/bin/edge")
            mock.assert_called_once_with("Edge", "/usr/bin/edge")
            assert result == '5.6.7.8'


# ====================================================================
# _get_file_version_win
# ====================================================================

@pytest.mark.skipif(sys.platform != 'win32', reason="需要 Windows 的 win32api 模块")
class TestGetFileVersionWin:
    def test_returns_version(self, win_wd):
        mock_info = {
            'FileVersionMS': (149 << 16) | 0,
            'FileVersionLS': (4022 << 16) | 69,
        }
        with patch('os.path.exists', return_value=True):
            with patch('win32api.GetFileVersionInfo', return_value=mock_info):
                with patch('win32api.HIWORD', side_effect=lambda v: v >> 16):
                    with patch('win32api.LOWORD', side_effect=lambda v: v & 0xFFFF):
                        result = win_wd._get_file_version_win("Edge", r"C:\edge.exe")
                        assert result == "149.0.4022.69"

    def test_file_not_found(self, win_wd):
        with patch('os.path.exists', return_value=False):
            result = win_wd._get_file_version_win("Edge", r"C:\nonexistent.exe")
            assert "没有找到" in result

    def test_api_error(self, win_wd):
        with patch('os.path.exists', return_value=True):
            with patch('win32api.GetFileVersionInfo', side_effect=Exception("access denied")):
                result = win_wd._get_file_version_win("Edge", r"C:\edge.exe")
                assert "读取" in result
                assert "出错" in result


# ====================================================================
# _get_file_version_linux
# ====================================================================

class TestGetFileVersionLinux:
    def test_parses_edge_version(self, linux_wd):
        mock_result = subprocess.CompletedProcess(
            args=['/usr/bin/microsoft-edge', '--version'],
            returncode=0,
            stdout='Microsoft Edge 149.0.4022.69\n',
            stderr='',
        )
        with patch('os.path.exists', return_value=True):
            with patch('subprocess.run', return_value=mock_result):
                result = linux_wd._get_file_version_linux("Edge", "/usr/bin/microsoft-edge")
                assert result == "149.0.4022.69"

    def test_parses_edgedriver_version(self, linux_wd):
        mock_result = subprocess.CompletedProcess(
            args=['/usr/local/bin/msedgedriver', '--version'],
            returncode=0,
            stdout='Microsoft Edge WebDriver 149.0.4022.69\n',
            stderr='',
        )
        with patch('os.path.exists', return_value=True):
            with patch('subprocess.run', return_value=mock_result):
                result = linux_wd._get_file_version_linux("EdgeDriver", "/usr/local/bin/msedgedriver")
                assert result == "149.0.4022.69"

    def test_path_is_none(self, linux_wd_no_edge):
        result = linux_wd_no_edge._get_file_version_linux("Edge", None)
        assert "没有找到" in result

    def test_binary_not_found(self, linux_wd):
        with patch('os.path.exists', return_value=False):
            with patch('shutil.which', return_value=None):
                result = linux_wd._get_file_version_linux("Edge", "/nonexistent/edge")
                assert "没有找到" in result

    def test_subprocess_fails(self, linux_wd):
        mock_result = subprocess.CompletedProcess(
            args=['/usr/bin/edge', '--version'],
            returncode=1,
            stdout='',
            stderr='error',
        )
        with patch('os.path.exists', return_value=True):
            with patch('subprocess.run', return_value=mock_result):
                result = linux_wd._get_file_version_linux("Edge", "/usr/bin/edge")
                assert "失败" in result

    def test_unparseable_output(self, linux_wd):
        mock_result = subprocess.CompletedProcess(
            args=['/usr/bin/edge', '--version'],
            returncode=0,
            stdout='Microsoft Edge unknown\n',
            stderr='',
        )
        with patch('os.path.exists', return_value=True):
            with patch('subprocess.run', return_value=mock_result):
                result = linux_wd._get_file_version_linux("Edge", "/usr/bin/edge")
                assert "无法解析" in result

    def test_subprocess_exception(self, linux_wd):
        with patch('os.path.exists', return_value=True):
            with patch('subprocess.run', side_effect=Exception("timeout")):
                result = linux_wd._get_file_version_linux("Edge", "/usr/bin/edge")
                assert "出错" in result

    def test_uses_shutil_which_when_path_not_exists(self, linux_wd):
        """二进制在 PATH 中但传入路径不存在时，fallback 到 shutil.which"""
        mock_result = subprocess.CompletedProcess(
            args=['msedgedriver', '--version'],
            returncode=0,
            stdout='Microsoft Edge WebDriver 149.0.4022.69\n',
            stderr='',
        )
        with patch('os.path.exists', side_effect=[False, True]):
            with patch('shutil.which', return_value='msedgedriver'):
                with patch('subprocess.run', return_value=mock_result) as mock_run:
                    linux_wd._get_file_version_linux("EdgeDriver", "msedgedriver")
                    mock_run.assert_called_once_with(
                        ['msedgedriver', '--version'],
                        capture_output=True, text=True, timeout=10
                    )


# ====================================================================
# set_permanent_path
# ====================================================================

class TestSetPermanentPath:
    def test_windows_calls_win_method(self, win_wd):
        with patch.object(win_wd, '_set_permanent_path_win') as mock:
            win_wd.set_permanent_path()
            mock.assert_called_once_with(
                os.path.dirname(win_wd.EDGEDRIVER_PATH)
            )

    def test_linux_skips(self, linux_wd):
        """Linux 下 set_permanent_path 不执行任何操作"""
        with patch.object(linux_wd, '_set_permanent_path_win') as mock:
            linux_wd.set_permanent_path()
            mock.assert_not_called()


# ====================================================================
# _set_permanent_path_win
# ====================================================================

@pytest.mark.skipif(sys.platform != 'win32', reason="需要 Windows 的 winreg 模块")
class TestSetPermanentPathWin:
    def test_adds_path_when_not_exists(self, win_wd):
        with patch('winreg.OpenKey'):
            with patch('winreg.QueryValueEx', side_effect=FileNotFoundError):
                with patch('winreg.SetValueEx') as mock_set:
                    with patch('winreg.CloseKey'):
                        win_wd._set_permanent_path_win(r"D:\Custom\Path")
                        mock_set.assert_called_once()

    def test_skips_when_already_in_path(self, win_wd):
        with patch('winreg.OpenKey'):
            with patch('winreg.QueryValueEx', return_value=(
                r"D:\Program Files\WebDriver\edgedriver_win64", 1
            )):
                with patch('winreg.SetValueEx') as mock_set:
                    with patch('winreg.CloseKey'):
                        win_wd._set_permanent_path_win(
                            r"D:\Program Files\WebDriver\edgedriver_win64"
                        )
                        mock_set.assert_not_called()


# ====================================================================
# download_edgedriver
# ====================================================================

class TestDownloadEdgedriver:
    def test_windows_delegates_to_win(self, win_wd):
        win_wd.edge_version = "149.0.4022.69"
        with patch.object(win_wd, '_download_edgedriver_win') as mock:
            win_wd.download_edgedriver()
            mock.assert_called_once()

    def test_linux_delegates_to_linux(self, linux_wd):
        linux_wd.edge_version = "149.0.4022.69"
        with patch.object(linux_wd, '_download_edgedriver_linux') as mock:
            linux_wd.download_edgedriver()
            mock.assert_called_once()

    def test_url_contains_correct_zip_for_windows(self, win_wd):
        win_wd.edge_version = "149.0.4022.69"
        with patch.object(win_wd, '_download_edgedriver_win') as mock:
            win_wd.download_edgedriver()
            url = mock.call_args[0][0]
            assert 'edgedriver_win64.zip' in url
            assert '149.0.4022.69' in url

    def test_url_contains_correct_zip_for_linux(self, linux_wd):
        linux_wd.edge_version = "149.0.4022.69"
        with patch.object(linux_wd, '_download_edgedriver_linux') as mock:
            linux_wd.download_edgedriver()
            url = mock.call_args[0][0]
            assert 'edgedriver_linux64.zip' in url
            assert '149.0.4022.69' in url


# ====================================================================
# _download_edgedriver_win
# ====================================================================

class TestDownloadEdgedriverWin:
    def test_full_success_flow(self, win_wd):
        win_wd.edge_version = "149.0.4022.69"
        with patch('os.makedirs'):
            with patch.object(win_wd, '_download_file'):
                with patch('os.path.exists', return_value=True):
                    with patch('shutil.rmtree'):
                        with patch('shutil.unpack_archive'):
                            with patch.object(win_wd, '_cleanup_zip') as mock_cleanup:
                                win_wd._download_edgedriver_win("https://example.com/driver.zip")
                                mock_cleanup.assert_called_once()

    def test_skips_rmtree_if_no_old_driver(self, win_wd):
        win_wd.edge_version = "149.0.4022.69"
        with patch('os.makedirs'):
            with patch.object(win_wd, '_download_file'):
                with patch('os.path.exists', return_value=False):
                    with patch('shutil.rmtree') as mock_rmtree:
                        with patch('shutil.unpack_archive'):
                            with patch.object(win_wd, '_cleanup_zip'):
                                win_wd._download_edgedriver_win("https://example.com/driver.zip")
                                mock_rmtree.assert_not_called()

    @pytest.mark.parametrize("exc", [
        FileNotFoundError("access denied"),
        PermissionError("permission denied"),
        Exception("generic error"),
    ])
    def test_rmtree_failure_exits(self, win_wd, exc):
        win_wd.edge_version = "149.0.4022.69"
        with patch('os.makedirs'):
            with patch.object(win_wd, '_download_file'):
                with patch('os.path.exists', return_value=True):
                    with patch('shutil.rmtree', side_effect=exc):
                        with pytest.raises(SystemExit):
                            win_wd._download_edgedriver_win("https://example.com/driver.zip")


# ====================================================================
# _download_edgedriver_linux
# ====================================================================

class TestDownloadEdgedriverLinux:
    def _make_zip_entry(self, name):
        entry = MagicMock(spec_set=zipfile.ZipInfo)
        entry.filename = name
        return entry

    def _setup_linux_mocks(self, linux_wd, zip_entries, chmod_side_effect=None):
        """统一设置 Linux 下载所需的 mock"""
        linux_wd.edge_version = "149.0.4022.69"
        mock_zip = MagicMock(spec=zipfile.ZipFile)
        mock_zip.infolist.return_value = zip_entries
        mock_zip.__enter__.return_value = mock_zip

        patches = {
            'os.makedirs': patch('os.makedirs'),
            '_download_file': patch.object(linux_wd, '_download_file'),
            'zipfile.ZipFile': patch('zipfile.ZipFile', return_value=mock_zip),
            'os.chmod': patch('os.chmod'),
            '_cleanup_zip': patch.object(linux_wd, '_cleanup_zip'),
        }
        for key, p in patches.items():
            p.start()
        return patches

    def _teardown_mocks(self, patches):
        for p in reversed(list(patches.values())):
            p.stop()

    def test_full_success_flow(self, linux_wd):
        entry = self._make_zip_entry('edgedriver_linux64/msedgedriver')
        patches = self._setup_linux_mocks(linux_wd, [entry])
        try:
            linux_wd._download_edgedriver_linux("https://example.com/driver.zip")
            # 验证 msedgedriver 从 zip 中被提取
            assert entry.filename == 'msedgedriver'
        finally:
            self._teardown_mocks(patches)

    def test_extract_strips_directory_prefix(self, linux_wd):
        entry = self._make_zip_entry('edgedriver_linux64/msedgedriver')
        patches = self._setup_linux_mocks(linux_wd, [entry])
        try:
            linux_wd._download_edgedriver_linux("https://example.com/driver.zip")
            assert entry.filename == 'msedgedriver'
        finally:
            self._teardown_mocks(patches)

    def test_raises_when_binary_not_in_zip(self, linux_wd):
        patches = self._setup_linux_mocks(
            linux_wd,
            [self._make_zip_entry('edgedriver_linux64/LICENSE')]
        )
        try:
            with pytest.raises(SystemExit):
                linux_wd._download_edgedriver_linux("https://example.com/driver.zip")
        finally:
            self._teardown_mocks(patches)

    def test_permission_error_exits(self, linux_wd):
        entry = self._make_zip_entry('edgedriver_linux64/msedgedriver')
        # 让 os.chmod 抛出 PermissionError
        linux_wd.edge_version = "149.0.4022.69"
        mock_zip = MagicMock(spec=zipfile.ZipFile)
        mock_zip.infolist.return_value = [entry]
        mock_zip.__enter__.return_value = mock_zip
        with patch('os.makedirs'):
            with patch.object(linux_wd, '_download_file'):
                with patch('zipfile.ZipFile', return_value=mock_zip):
                    with patch('os.chmod', side_effect=PermissionError):
                        with patch.object(linux_wd, '_cleanup_zip'):
                            with pytest.raises(SystemExit):
                                linux_wd._download_edgedriver_linux("https://example.com/driver.zip")


# ====================================================================
# _download_file
# ====================================================================

class TestDownloadFile:
    def test_successful_download(self, win_wd):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raw = MagicMock()

        with patch('requests.get', return_value=mock_response) as mock_get:
            with patch('shutil.copyfileobj') as mock_copy:
                with patch('builtins.open', MagicMock()):
                    win_wd._download_file("https://example.com/driver.zip", "/tmp/driver.zip")
                    mock_get.assert_called_once_with(
                        "https://example.com/driver.zip", stream=True, timeout=30
                    )
                    mock_copy.assert_called_once()

    def test_http_error_exits(self, win_wd):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('requests.get', return_value=mock_response):
            with pytest.raises(SystemExit):
                win_wd._download_file("https://example.com/driver.zip", "/tmp/driver.zip")

    def test_network_error_exits(self, win_wd):
        """requests 内置异常会触发 sys.exit"""
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(SystemExit):
                win_wd._download_file("https://example.com/driver.zip", "/tmp/driver.zip")


# ====================================================================
# _cleanup_zip
# ====================================================================

class TestCleanupZip:
    def test_successful_cleanup(self, win_wd):
        with patch('os.remove') as mock_remove:
            win_wd._cleanup_zip("/tmp/driver.zip")
            mock_remove.assert_called_once_with("/tmp/driver.zip")

    def test_failure_prints_message_not_exits(self, win_wd):
        """清理失败只打印错误，不退出"""
        with patch('os.remove', side_effect=Exception("access denied")):
            win_wd._cleanup_zip("/tmp/driver.zip")


# ====================================================================
# start
# ====================================================================

class TestStart:
    def test_full_flow_versions_match(self, win_wd):
        """版本一致时不下载"""
        with patch.object(win_wd, 'set_permanent_path'):
            with patch.object(win_wd, 'get_file_version', side_effect=[
                "149.0.4022.69", "149.0.4022.69"
            ]):
                with patch.object(win_wd, 'download_edgedriver') as mock_dl:
                    with patch('os.system'):
                        with patch('time.sleep'):
                            win_wd.start()
                            assert win_wd.edge_version == "149.0.4022.69"
                            mock_dl.assert_not_called()

    def test_full_flow_versions_mismatch(self, win_wd):
        """版本不一致时调用 download_edgedriver"""
        with patch.object(win_wd, 'set_permanent_path'):
            with patch.object(win_wd, 'get_file_version', side_effect=[
                "149.0.4022.69", "148.0.1234.56"
            ]):
                with patch.object(win_wd, 'download_edgedriver') as mock_dl:
                    win_wd.start()
                    mock_dl.assert_called_once()

    def test_clear_screen_windows(self, win_wd):
        with patch.object(win_wd, 'set_permanent_path'):
            with patch.object(win_wd, 'get_file_version', return_value="1.0.0.0"):
                with patch('time.sleep'):
                    with patch('os.system') as mock_system:
                        win_wd.start()
                        mock_system.assert_called_once_with('cls')

    def test_clear_screen_linux(self, linux_wd):
        with patch.object(linux_wd, 'set_permanent_path'):
            with patch.object(linux_wd, 'get_file_version', return_value="1.0.0.0"):
                with patch('time.sleep'):
                    with patch('os.system') as mock_system:
                        linux_wd.start()
                        mock_system.assert_called_once_with('clear')
