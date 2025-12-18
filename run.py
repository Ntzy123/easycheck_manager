# run.py

import os, sys, subprocess
from lib.webdriver_manager import WebDriverManager

if __name__ == '__main__':

    wd = WebDriverManager()
    wd.start()

    subprocess.run("auto_easycheck.exe")