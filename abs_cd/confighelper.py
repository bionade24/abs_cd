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
                self.setting_path = '/opt/abs_cd/data/settings.ini'
                if not os.path.isfile(self.setting_path):
                    raise FileNotFoundError("Neither data/settings.ini or settings.ini.template available")
        self.settings = configparser.ConfigParser(interpolation=None)
        self.settings.read(self.setting_path)

    def get_setting(self, name, default=None):
        try:
            val = self.settings['DJANGO'][name]
        except KeyError:
            self.write_setting(name, '')
            return self.get_setting(name, default)
        if val == '' and default is not None:
            val = default
            self.write_setting(name, val)
        return val

    def write_setting(self, name, value):
        with open(self.setting_path, 'w') as settingsfile:
            self.settings['DJANGO'][name] = value
            self.settings.write(settingsfile, space_around_delimiters=True)
