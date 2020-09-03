import configparser
import os
import shutil

class Confighelper:

    def __init__(self):
        self.setting_path = os.path.join(os.curdir, 'data', 'settings.ini')
        template_path = os.path.join(os.curdir, 'settings.ini.template')
        if not os.path.isfile(self.setting_path):
            if os.path.isfile(template_path):
                shutil.copyfile(template_path, self.setting_path)
            else:
                raise FileNotFoundError("Neither data/settings.ini or settings.ini.template available")
        self.settings = configparser.ConfigParser(interpolation=None)
        self.settings.read(self.setting_path)

    def get_setting(self, name):
        return self.settings['DJANGO'][name]

    def write_setting(self, name, value):
        with open(self.setting_path, 'w') as settingsfile:
            self.settings['DJANGO'][name] = value
            self.settings.write(settingsfile, space_around_delimiters=True)
