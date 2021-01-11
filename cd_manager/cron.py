from cd_manager.models import Package

def check_for_new_commits():
    for pkg in Package.objects.all():
        if pkg.repo_status_check():
            pkg.build()
            #TODO: Speed up process by already excluding dependencies after pkg was built

