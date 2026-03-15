from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os
import re
import requests

channels = {
    "PTV Sports": "https://ptvsportshd.com/live",
    "ARY Digital": "https://live.arydigital.tv",
    "ARY News": "https://live.arynews.tv",
    "Geo News": "https://live.geo.tv",
    "Samaa News": "https://www.samaa.tv/live",
    "Aaj News": "https://www.aaj.tv/live"
}

def clean_url(url):
    return re.split(r'\.m3u8', url)[0] + ".m3u8"

def is_valid_stream(url):
    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return False

        if "#EXTM3U" in r.text:
            return True

    except:
        pass

    return False


options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

streams = {}

for name, page in channels.items():

    print("Scanning:", name)

    driver.get(page)

    time.sleep(15)

    logs = driver.get_log("performance")

    candidates = []

    for entry in logs:

        msg = json.loads(entry["message"])["message"]

        if msg["method"] != "Network.requestWillBeSent":
            continue

        url = msg["params"]["request"]["url"]

        if ".m3u8" in url:

            clean = clean_url(url)

            if clean not in candidates:
                candidates.append(clean)

    # test each candidate
    for c in candidates:

        if is_valid_stream(c):

            streams[name] = c
            print("Working:", c)
            break

driver.quit()

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u","w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")

print("Channels captured:", len(streams))
