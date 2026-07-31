import os


def app_home():
    return os.path.join(os.path.expanduser("~"), ".dd-code-analysis")
