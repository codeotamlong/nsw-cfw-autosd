# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import json
import re
import os
import zipfile
import shutil
from string import Template
from pathlib import Path

import requests
from clint.textui import progress


class Base:
    # Foreground:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    # Formatting
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    # End colored text
    END = '\033[0m'
    NC = '\x1b[0m'  # No Color


def dl_component(component: dict, destination: str):
    if "name" in component:
        print(Base.OKBLUE, component["name"], Base.END)

    if "description" in component:
        print(component["description"])

    if "isDisabled" in component:
        if component["isDisabled"]:
            print("Skip as config!")
            return

    if "repo" in component:
        dl_github_latest(component, destination)

    if "link" in component:
        download_to(component["link"], destination)


def download_to(url: str, destination: str):
    if not os.path.exists(destination):
        os.makedirs(destination)  # create folder if it does not exist

    # be careful with file names
    filename = url.split('/')[-1].replace(" ", "_")
    file_path = os.path.join(destination, filename)

    r = requests.get(url, stream=True)
    if r.ok:

        print("saving to", os.path.abspath(file_path))
        with open(file_path, 'wb') as f:
            total_length = int(r.headers.get('content-length'))
            for chunk in progress.bar(r.iter_content(chunk_size=2391975), expected_size=(total_length/1024) + 1):
                # for chunk in r.iter_content(chunk_size=1024 * 8):
                if chunk:
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
    else:  # HTTP status code 4XX/5XX
        print("Download failed: status code {}\n{}".format(r.status_code, r.text))


def dl_github_latest(component: dict, destination: str):
    if not os.path.exists(destination):
        os.makedirs(destination)  # create folder if it does not exist

    response = requests.get(get_github_api_url(component["repo"]))
    res_data = response.json() if response and response.status_code == 200 else None

    if "assets" in res_data:
        for assets in res_data["assets"]:
            print("Found", assets["name"], end="")
            for pattern in component["regex"]:
                print(". Regex", pattern, end="")
                ptn = re.compile(pattern)
                if ptn.match(assets["name"]):
                    print(" => Match! Download:", assets["name"])
                    print("URL:", assets["browser_download_url"])
                    download_to(assets["browser_download_url"], destination)
                else:
                    print(" => Not Match. Skip!")


def get_github_api_url(repo: str):
    api_template = Template(
        "https://api.github.com/repos/$repo/releases/latest")
    url = api_template.substitute({
        'repo': repo
    })
    return url


def setup_component(full_path: str, destination="."):
    path = Path(full_path)
    if path.suffix == ".zip":
        print("Extract", end="")
    else:
        print("Move", end="")
    print(Base.OKGREEN, path.name, Base.END, "to",
          Base.OKGREEN, destination, Base.END)

    if path.suffix == ".zip":
        zip_obj = zipfile.ZipFile(path)  # create zipfile object
        zip_obj.extractall(destination)  # extract file to dir
        zip_obj.close()  # close file

    if (path.suffix in [".bin", ".nro", ".config", ".ovl"]):
        shutil.copy(path, destination)
        if os.path.isfile(destination):
            print("Success")

    return


def write_config_ini(src: list, dst: str):
    path = Path(dst)
    print("Write", Base.OKGREEN, len(src), Base.END,
          "lines(s) to", Base.OKGREEN, path, Base.END)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w") as f:  # Opens file and casts as f
        for line in src:
            f.write(line+"\n")  # Writing
        # File closed automatically
    return


def build(segment: list):
    print(Base.HEADER, Base.BOLD, "###", Base.END)
    print(Base.HEADER, Base.BOLD, "#", segment["description"], Base.END)
    print(Base.HEADER, Base.BOLD, "###", Base.END)
    segment_dl_path = os.path.join(
        dl_path, segment["dl_path"] if ("dl_path" in segment) else "./cfw")
    segment_sd_path = os.path.join(
        sd_path, segment["sd_path"] if ("sd_path" in segment) else ".")

    print(Base.HEADER, "Download components:", Base.END)
    for index, component in enumerate(segment["component"]):
        print(index+1, ". Download", component["name"])
        dl_component(component, segment_dl_path)

    print(Base.HEADER, "Extract these files into the root of your SD card:", Base.END)
    # loop through items in dir
    for index, item in enumerate(os.listdir(segment_dl_path)):
        print(index+1, ".", end="")
        if item.endswith(".zip"):
            setup_component((os.path.join(segment_dl_path, item)), sd_path)
        else:
            setup_component((os.path.join(segment_dl_path, item)),
                            os.path.join(segment_sd_path, item))

    if "config" in segment:
        print(Base.HEADER, "Create .ini file(s)", Base.END)
        for index, cfg in enumerate(segment["config"]):
            dst = os.path.join(sd_path, cfg["location"])
            print(index+1, ". Write", dst)
            if "description" in cfg:
                print(cfg["description"])
            write_config_ini(cfg["content"], dst)

    return


if __name__ == '__main__':

    with open('config.json', 'r') as config_file:
        CONFIG = json.load(config_file)

    dl_path = os.path.join(CONFIG["dl_path"] if (
        "dl_path" in CONFIG) else "./download")
    sd_path = os.path.join(CONFIG["sd_path"] if (
        "sd_path" in CONFIG) else "./sdcard")

    # Try to remove the tree; if it fails, throw an error using try...except.
    try:
        shutil.rmtree(os.path.join(sd_path))
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))

    if "cfw" in CONFIG:
        build(CONFIG["cfw"])

        cfw_dl_path = os.path.join(dl_path, CONFIG["cfw"]["dl_path"] if (
            "dl_path" in CONFIG["cfw"]) else "./cfw")
        cfw_sd_path = os.path.join(sd_path, CONFIG["cfw"]["sd_path"] if (
            "sd_path" in CONFIG["cfw"]) else ".")

        print(Base.HEADER, "Rename hekate_ctcaer_x.x.x.bin to payload.bin.", Base.END)
        ptn = re.compile("hekate_ctcaer_.*.bin")
        for item in os.listdir(cfw_sd_path):  # loop through items in dir
            if ptn.match(item):
                print("Found", item, "=> Rename to payload.bin")
                os.rename(os.path.join(cfw_sd_path, item),
                          os.path.join(cfw_sd_path, "payload.bin"))

        print(Base.HEADER, "Move fusee.bin to /bootloader/payloads/ folder.", Base.END)
        if os.path.exists(os.path.join(cfw_dl_path, "fusee.bin")):
            setup_component(os.path.join(cfw_dl_path, "fusee.bin"), os.path.join(
                sd_path, "bootloader", "payloads", "fusee.bin"))

    if "payload" in CONFIG:
        build(CONFIG["payload"])

    if "homebrew" in CONFIG:
        build(CONFIG["homebrew"])

    if "tesla-overlay" in CONFIG:
        build(CONFIG["tesla-overlay"])

    if "sys-module" in CONFIG:
        build(CONFIG["sys-module"])
