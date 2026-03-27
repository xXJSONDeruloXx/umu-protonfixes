"""Unit tests for OptiScaler utility functions

These tests can run independently without the full Proton environment.
"""

import configparser
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestOptiScalerFunctions(unittest.TestCase):
    """Test OptiScaler installation and uninstallation functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a temporary game directory
        self.temp_dir = Path(tempfile.mkdtemp())
        self.game_dir = self.temp_dir / 'game'
        self.game_dir.mkdir()

        # Create a temporary OptiScaler source directory
        self.optiscaler_source = self.temp_dir / 'optiscaler'
        self.optiscaler_source.mkdir()

        # Create mock OptiScaler files
        (self.optiscaler_source / 'OptiScaler.dll').write_bytes(b'mock dll content')
        (self.optiscaler_source / 'OptiScaler.ini').write_text(
            '[Upscaler]\nUpscaleRatio = 0.77\n', encoding='utf-8'
        )
        (self.optiscaler_source / 'fakenvapi.dll').write_bytes(b'mock fakenvapi')
        (self.optiscaler_source / 'nvngx.dll').write_bytes(b'mock nvngx')
        (self.optiscaler_source / 'libxess.dll').write_bytes(b'mock libxess')

        # Create plugins directory
        plugins_dir = self.optiscaler_source / 'plugins'
        plugins_dir.mkdir()
        (plugins_dir / 'test_plugin.dll').write_bytes(b'mock plugin')

        # Create an existing DLL in game directory for backup testing
        self.existing_dll = self.game_dir / 'dxgi.dll'
        self.existing_dll.write_bytes(b'original game dll')

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_backup_file_creates_backup(self) -> None:
        """Test that _backup_file creates a .optiscaler.bak file."""
        # Import the function directly - we need to mock dependencies
        from protonfixes import util

        test_file = self.game_dir / 'test.dll'
        test_file.write_bytes(b'test content')

        result = util._backup_file(test_file)

        self.assertTrue(result)
        backup_path = test_file.with_suffix('.dll.optiscaler.bak')
        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.read_bytes(), b'test content')

    def test_backup_file_skips_existing_backup(self) -> None:
        """Test that _backup_file doesn't overwrite existing backup."""
        from protonfixes import util

        test_file = self.game_dir / 'test.dll'
        test_file.write_bytes(b'new content')
        backup_path = test_file.with_suffix('.dll.optiscaler.bak')
        backup_path.write_bytes(b'old backup')

        result = util._backup_file(test_file)

        self.assertFalse(result)
        self.assertEqual(backup_path.read_bytes(), b'old backup')

    def test_backup_file_nonexistent(self) -> None:
        """Test that _backup_file returns False for nonexistent file."""
        from protonfixes import util

        nonexistent = self.game_dir / 'nonexistent.dll'
        result = util._backup_file(nonexistent)

        self.assertFalse(result)

    def test_restore_backup_restores_file(self) -> None:
        """Test that _restore_backup restores from backup."""
        from protonfixes import util

        test_file = self.game_dir / 'test.dll'
        test_file.write_bytes(b'modified content')
        backup_path = test_file.with_suffix('.dll.optiscaler.bak')
        backup_path.write_bytes(b'original content')

        result = util._restore_backup(test_file)

        self.assertTrue(result)
        self.assertEqual(test_file.read_bytes(), b'original content')
        self.assertFalse(backup_path.exists())

    def test_restore_backup_no_backup(self) -> None:
        """Test that _restore_backup returns False when no backup exists."""
        from protonfixes import util

        test_file = self.game_dir / 'test.dll'
        test_file.write_bytes(b'content')

        result = util._restore_backup(test_file)

        self.assertFalse(result)

    def test_modify_optiscaler_ini(self) -> None:
        """Test that _modify_optiscaler_ini modifies INI file correctly."""
        from protonfixes import util

        ini_path = self.game_dir / 'OptiScaler.ini'
        ini_path.write_text('[Upscaler]\nUpscaleRatio = 0.77\n', encoding='utf-8')

        overrides = {
            'Spoofing': {'SpoofHAGS': 'true'},
            'FrameGeneration': {'Enabled': 'true'},
        }

        result = util._modify_optiscaler_ini(ini_path, overrides)

        self.assertTrue(result)

        # Read back and verify
        conf = configparser.ConfigParser()
        conf.read(ini_path, encoding='utf-8')

        self.assertEqual(conf.get('Spoofing', 'SpoofHAGS'), 'true')
        self.assertEqual(conf.get('FrameGeneration', 'Enabled'), 'true')
        # Original value should be preserved
        self.assertEqual(conf.get('Upscaler', 'UpscaleRatio'), '0.77')

    def test_modify_optiscaler_ini_empty_overrides(self) -> None:
        """Test that _modify_optiscaler_ini works with empty overrides."""
        from protonfixes import util

        ini_path = self.game_dir / 'OptiScaler.ini'
        ini_path.write_text('[Upscaler]\nUpscaleRatio = 0.77\n', encoding='utf-8')

        result = util._modify_optiscaler_ini(ini_path, {})

        self.assertTrue(result)

    def test_modify_optiscaler_ini_nonexistent(self) -> None:
        """Test that _modify_optiscaler_ini returns False for nonexistent file."""
        from protonfixes import util

        nonexistent = self.game_dir / 'nonexistent.ini'
        result = util._modify_optiscaler_ini(nonexistent, {'Section': {'Key': 'value'}})

        self.assertFalse(result)

    def test_valid_dll_names(self) -> None:
        """Test that OPTISCALER_VALID_DLL_NAMES contains expected values."""
        from protonfixes import util

        expected = {
            'dxgi.dll',
            'winmm.dll',
            'version.dll',
            'dbghelp.dll',
            'd3d12.dll',
            'wininet.dll',
            'winhttp.dll',
            'OptiScaler.asi',
        }
        self.assertEqual(util.OPTISCALER_VALID_DLL_NAMES, expected)

    def test_install_optiscaler_invalid_dll_name(self) -> None:
        """Test that install_optiscaler rejects invalid dll_name."""
        from protonfixes import util

        with patch.object(util, '_get_optiscaler_source_dir', return_value=self.optiscaler_source):
            result = util.install_optiscaler(
                target_path=str(self.game_dir),
                dll_name='invalid.dll',
            )

        self.assertFalse(result)

    def test_install_optiscaler_nonexistent_target(self) -> None:
        """Test that install_optiscaler fails for nonexistent target."""
        from protonfixes import util

        nonexistent = self.temp_dir / 'nonexistent'
        result = util.install_optiscaler(target_path=str(nonexistent))

        self.assertFalse(result)

    @patch('protonfixes.util.winedll_override')
    def test_install_optiscaler_success(self, mock_override: MagicMock) -> None:
        """Test successful OptiScaler installation."""
        from protonfixes import util

        with patch.object(util, '_get_optiscaler_source_dir', return_value=self.optiscaler_source):
            result = util.install_optiscaler(
                target_path=str(self.game_dir),
                dll_name='dxgi.dll',
                ini_overrides={'Spoofing': {'SpoofHAGS': 'true'}},
            )

        self.assertTrue(result)

        # Verify OptiScaler.dll was copied as dxgi.dll
        dxgi_path = self.game_dir / 'dxgi.dll'
        self.assertTrue(dxgi_path.exists())
        self.assertEqual(dxgi_path.read_bytes(), b'mock dll content')

        # Verify original was backed up
        backup_path = self.game_dir / 'dxgi.dll.optiscaler.bak'
        self.assertTrue(backup_path.exists())
        self.assertEqual(backup_path.read_bytes(), b'original game dll')

        # Verify OptiScaler.ini was copied and modified
        ini_path = self.game_dir / 'OptiScaler.ini'
        self.assertTrue(ini_path.exists())

        # Verify supporting files were copied
        self.assertTrue((self.game_dir / 'fakenvapi.dll').exists())
        self.assertTrue((self.game_dir / 'nvngx.dll').exists())
        self.assertTrue((self.game_dir / 'libxess.dll').exists())

        # Verify plugins directory was copied
        self.assertTrue((self.game_dir / 'plugins' / 'test_plugin.dll').exists())

        # Verify dll override was called
        mock_override.assert_called_once_with('dxgi', util.OverrideOrder.NATIVE)

    @patch('protonfixes.util.winedll_override')
    def test_install_optiscaler_asi_no_override(self, mock_override: MagicMock) -> None:
        """Test that OptiScaler.asi doesn't set dll override."""
        from protonfixes import util

        with patch.object(util, '_get_optiscaler_source_dir', return_value=self.optiscaler_source):
            result = util.install_optiscaler(
                target_path=str(self.game_dir),
                dll_name='OptiScaler.asi',
            )

        self.assertTrue(result)
        mock_override.assert_not_called()

    def test_uninstall_optiscaler_nonexistent_target(self) -> None:
        """Test that uninstall_optiscaler fails for nonexistent target."""
        from protonfixes import util

        nonexistent = self.temp_dir / 'nonexistent'
        result = util.uninstall_optiscaler(target_path=str(nonexistent))

        self.assertFalse(result)

    def test_uninstall_optiscaler_restores_backup(self) -> None:
        """Test that uninstall_optiscaler restores backed up files."""
        from protonfixes import util

        # Simulate installed state
        (self.game_dir / 'dxgi.dll').write_bytes(b'optiscaler dll')
        (self.game_dir / 'dxgi.dll.optiscaler.bak').write_bytes(b'original game dll')
        (self.game_dir / 'OptiScaler.ini').write_text('config', encoding='utf-8')
        (self.game_dir / 'fakenvapi.dll').write_bytes(b'fakenvapi')

        result = util.uninstall_optiscaler(target_path=str(self.game_dir))

        self.assertTrue(result)

        # Original should be restored
        self.assertEqual((self.game_dir / 'dxgi.dll').read_bytes(), b'original game dll')

        # Backup should be removed
        self.assertFalse((self.game_dir / 'dxgi.dll.optiscaler.bak').exists())

        # OptiScaler files should be removed
        self.assertFalse((self.game_dir / 'OptiScaler.ini').exists())
        self.assertFalse((self.game_dir / 'fakenvapi.dll').exists())

    def test_uninstall_optiscaler_removes_plugins(self) -> None:
        """Test that uninstall_optiscaler removes plugins directory."""
        from protonfixes import util

        plugins_dir = self.game_dir / 'plugins'
        plugins_dir.mkdir()
        (plugins_dir / 'plugin.dll').write_bytes(b'plugin')

        result = util.uninstall_optiscaler(target_path=str(self.game_dir))

        self.assertTrue(result)
        self.assertFalse(plugins_dir.exists())

    def test_uninstall_optiscaler_cleans_orphaned_backups(self) -> None:
        """Test that uninstall_optiscaler cleans up orphaned backup files."""
        from protonfixes import util

        # Create orphaned backup
        (self.game_dir / 'some.dll.optiscaler.bak').write_bytes(b'orphaned')

        result = util.uninstall_optiscaler(target_path=str(self.game_dir))

        self.assertTrue(result)
        self.assertFalse((self.game_dir / 'some.dll.optiscaler.bak').exists())

    @patch('protonfixes.util.winedll_override')
    def test_install_optiscaler_backs_up_existing_plugins(
        self, mock_override: MagicMock
    ) -> None:
        """Test that install_optiscaler backs up existing plugins directory."""
        from protonfixes import util

        # Create existing plugins directory in game
        existing_plugins = self.game_dir / 'plugins'
        existing_plugins.mkdir()
        (existing_plugins / 'original_plugin.dll').write_bytes(b'original plugin')

        with patch.object(
            util, '_get_optiscaler_source_dir', return_value=self.optiscaler_source
        ):
            result = util.install_optiscaler(
                target_path=str(self.game_dir),
                dll_name='dxgi.dll',
            )

        self.assertTrue(result)

        # Backup should exist
        backup_plugins = self.game_dir / 'plugins.optiscaler.bak'
        self.assertTrue(backup_plugins.exists())
        self.assertTrue((backup_plugins / 'original_plugin.dll').exists())
        self.assertEqual(
            (backup_plugins / 'original_plugin.dll').read_bytes(),
            b'original plugin',
        )

        # New plugins should be installed
        self.assertTrue((self.game_dir / 'plugins' / 'test_plugin.dll').exists())

    def test_uninstall_optiscaler_restores_plugins_backup(self) -> None:
        """Test that uninstall_optiscaler restores plugins directory backup."""
        from protonfixes import util

        # Simulate installed state with plugins backup
        plugins_dir = self.game_dir / 'plugins'
        plugins_dir.mkdir()
        (plugins_dir / 'optiscaler_plugin.dll').write_bytes(b'optiscaler plugin')

        backup_plugins = self.game_dir / 'plugins.optiscaler.bak'
        backup_plugins.mkdir()
        (backup_plugins / 'original_plugin.dll').write_bytes(b'original plugin')

        result = util.uninstall_optiscaler(target_path=str(self.game_dir))

        self.assertTrue(result)

        # Original plugins should be restored
        self.assertTrue(plugins_dir.exists())
        self.assertTrue((plugins_dir / 'original_plugin.dll').exists())
        self.assertEqual(
            (plugins_dir / 'original_plugin.dll').read_bytes(),
            b'original plugin',
        )

        # Backup should be removed
        self.assertFalse(backup_plugins.exists())

        # OptiScaler plugins should be removed
        self.assertFalse((plugins_dir / 'optiscaler_plugin.dll').exists())


if __name__ == '__main__':
    unittest.main()
