from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
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
    "Aaj News": "https://www.aaj.tv/live",
}

def clean_url(url):
    return re.split(r'\.m3u8', url)[0] + ".m3u8"

def test_stream(url):
    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return None

        if "#EXT-X-STREAM-INF" in r.text:
            return "master"

        if "#EXTINF" in r.text:
            return "variant"

    except:
        pass

    return None


def click_play(driver):

    selectors = [
        "button",
        ".vjs-big-play-button",
        ".jw-icon-play",
        ".ytp-large-play-button",
        "[aria-label='Play']"
    ]

    for sel in selectors:

        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            print("Play button clicked")
            return
        except:
            pass


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

    time.sleep(5)

    # try clicking play
    click_play(driver)

    candidates = set()

    for _ in range(3):

        time.sleep(10)

        logs = driver.get_log("performance")

        for entry in logs:

            msg = json.loads(entry["message"])["message"]

            if msg["method"] != "Network.requestWillBeSent":
                continue

            url = msg["params"]["request"]["url"]

            if ".m3u8" in url:

                candidates.add(clean_url(url))

    master = None
    fallback = None

    for c in candidates:

        result = test_stream(c)

        if result == "master":
            master = c
            break

        elif result == "variant" and not fallback:
            fallback = c

    streams[name] = master or fallback

driver.quit()

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u","w") as f:

    f.write("#EXTM3U\n")

    for name, stream in streams.items():

        if stream:

            f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
            f.write(stream + "\n")

print("Channels captured:", len(streams))
