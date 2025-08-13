import os
import json

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'user_settings.json')

class UserSettings:
    def __init__(self):
        self.settings = {}
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

    def save(self):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

# Singleton instance
user_settings = UserSettings()
