import json
import os

CONFIG_FILE = "config.json"

class ConfigManager:
    def __init__(self):
        self.default_config = {
            "theme": "dark",
            "base_currency": "USD",
            "language": "zh",
            "default_fees": {
                "commission_rate": 10.24,
                "service_fee_rate": 2.5,
                "affiliate_fee_rate": 1.64
            },
            "funding_percent": 65
        }
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # Ensure all default keys exist
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    
                    # Special check for nested dicts
                    if "default_fees" not in config:
                        config["default_fees"] = self.default_config["default_fees"]
                    else:
                        for fee_key, fee_val in self.default_config["default_fees"].items():
                            if fee_key not in config["default_fees"]:
                                config["default_fees"][fee_key] = fee_val
                                
                    return config
            except Exception as e:
                print(f"Error loading config.json: {e}")
                return self.default_config.copy()
        else:
            self.save_config(self.default_config)
            return self.default_config.copy()

    def save_config(self, config_data=None):
        if config_data is None:
            config_data = self.config
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving config.json: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def get_fee(self, key, default=0.0):
        return self.config.get("default_fees", {}).get(key, default)

    def set_fee(self, key, value):
        if "default_fees" not in self.config:
            self.config["default_fees"] = {}
        self.config["default_fees"][key] = value
        self.save_config()
