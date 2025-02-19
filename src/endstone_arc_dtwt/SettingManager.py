import os
from pathlib import Path

MAIN_PATH = 'config/ARCDTWT'

class SettingManager:
    setting_dict = {}  # Class variable to store all settings

    def __init__(self):
        self.setting_file_path = Path(MAIN_PATH) / "DTWTConfig.yml"
        self._load_setting_file()

    def _initialize_default_settings(self):
        """Write the default settings into the config file if it doesn't exist."""
        default_settings = {
            "DEFAULT_LANGUAGE_CODE": "ZH-CN",
            "DATABASE_PATH": "DTWTdata.db",
            "TOTAL_BLACK_TILE_NUM": "20"
        }

        # Write default settings to the file
        with self.setting_file_path.open("w", encoding="utf-8") as f:
            for key, value in default_settings.items():
                f.write(f"{key}={value}\n")

        # Update the in-memory settings dictionary
        SettingManager.setting_dict.update(default_settings)

    def _load_setting_file(self):
        # Create config directory if not exists
        self.setting_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if the file exists; if not, create it and initialize default settings
        if not self.setting_file_path.exists():
            self._initialize_default_settings()
        else:
            # Load settings file content
            with self.setting_file_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        SettingManager.setting_dict[key.strip()] = value.strip()


    def GetSetting(self, key):
        # If key doesn't exist in settings, add it
        if key not in SettingManager.setting_dict:
            with self.setting_file_path.open("a", encoding="utf-8") as f:
                f.write(f"\n{key}=")
            SettingManager.setting_dict[key] = ""

        return None if not SettingManager.setting_dict[key] else SettingManager.setting_dict[key]

    def SetSetting(self, key, value):
        # Update setting in memory
        SettingManager.setting_dict[key] = str(value)

        # Rewrite entire file with updated settings
        with self.setting_file_path.open("w", encoding="utf-8") as f:
            for k, v in SettingManager.setting_dict.items():
                f.write(f"{k}={v}\n")