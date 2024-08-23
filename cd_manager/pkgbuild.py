""" Thankfully stolen and extended from python-pkgbuild https://github.com/z3ntu/python-pkgbuild/
    File under MIT License"""

import re
from enum import Enum
from collections import defaultdict

SourceParts = Enum('SourceParts', 'folder vcs url fragment')

# pkgname can actually be multiple if one pkgbase for 2 packages
single_value = ('pkgbase', 'pkgdesc', 'pkgver', 'pkgrel', 'epoch', 'url')


class SRCINFO:

    def __init__(self, filepath):
        """
        Parses and holds data of a .SRCINFO file.
        ;param filepath: Path to a .SRCINFO file
        Access the data with the object 'content'
        """
        return_dict = defaultdict(list)
        with open(filepath, 'r') as file:
            for line in file:
                # ignore commented or empty lines
                if line.startswith("#") or line == "\n":
                    continue
                line = line.replace('\n', '')  # remove newlines and tabs
                line = line.replace('\t', '')
                array = line.split(" = ")
                key = array[0]
                value = array[1]
                if key in single_value:
                    return_dict[key] = value
                elif not return_dict.get(key):
                    return_dict[key] = [value]  # set new value
                else:
                    return_dict[key].append(value)  # append to array
        self._content = return_dict

    def getcontent(self):
        return self._content

    def getrundeps(self):
        rundeps = self.getcontent().get('depends')
        return rundeps if rundeps else []

    def getmakedeps(self):
        makedeps = self.getcontent().get('makedepends')
        return makedeps if makedeps else []

    def getcheckdeps(self):
        checkdeps = self.getcontent().get('checkdepends')
        return checkdeps if checkdeps else []


def parse_source_field(source_text, source_parts):
    """
    Parse the source text from PKGBUILD or .SRCINFO file and return desired parts
    :param source_text: The text (see https://wiki.archlinux.org/index.php/VCS_package_guidelines#VCS_sources)
    :param source_parts: Which part to return; use the SourceParts enum
    """
    if not isinstance(source_parts, SourceParts):
        return None
    if source_parts is SourceParts.folder:
        if "::" in source_text:
            # return source_text.split("::")[0]
            return re.search('(.+?)::', source_text).group(1)
        return None
    elif source_parts is SourceParts.vcs:
        if "+" in source_text:
            return re.search('(?:.*::)?(.+?)\\+', source_text).group(1)
    elif source_parts is SourceParts.url:
        if "#" in source_text:
            # TODO: Make simpler without if
            return re.search('(?:.*\\+)?(.+?)#', source_text).group(1)
        return re.search('(?:.*\\+)?(.*)', source_text).group(1)
    elif source_parts is SourceParts.fragment:
        if "#" in source_text:
            return re.search('#(.*)', source_text).group(1)


if __name__ == '__main__':
    # srcinfo = SRCINFO(sys.argv[1])
    # print(json.dumps(srcinfo.content))
    print(parse_source_field(
        "git+http://project_url#branch=project_branch", SourceParts.folder))
    print(parse_source_field(
        "project_name::git+http://project_url#branch=project_branch", SourceParts.vcs))
    print(parse_source_field("project_name::git+http://project_url", SourceParts.url))
    print(parse_source_field(
        "project_name::git+http://project_url", SourceParts.fragment))
    print(parse_source_field(
        "project_name::git+http://project_url#branch=project_branch", SourceParts.fragment))
