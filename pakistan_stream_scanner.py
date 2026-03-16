from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os
import requests
import re

channels = {
    "PTV Sports": "https://ptvsportshd.com/live",
    "Geo News": "https://live.geo.tv",
    "ARY Digital": "https://live.arydigital.tv",
    "ARY News": "https://live.arynews.tv",
    "Samaa News": "https://www.samaa.tv/live",
    "Aaj News": "https://www.aaj.tv/live",
    "Hum News": "https://humnews.pk/live",
    "Hum TV": "https://hum.tv/live",
    "Dunya News": "https://dunyanews.tv/live",
    "GNN": "https://gnnhd.tv/live",
    "92 News": "https://92newshd.tv/live",
    "Bol News": "https://www.bolnetwork.com/live",
    "Express News": "https://express.pk/live",
}

def test_stream(url):
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            if "#EXTM3U" in r.text or "#EXTINF" in r.text:
                return True
    except:
        pass
    return False


def click_play(driver):
    """
    Try multiple ways to trigger player playback
    """

    try:
        video = driver.find_element(By.TAG_NAME, "video")
        driver.execute_script("arguments[0].play()", video)
        return
    except:
        pass

    selectors = [
        "button",
        ".vjs-big-play-button",
        ".jw-icon-play",
        ".plyr__control--overlaid",
        ".play-button"
    ]

    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            return
        except:
            continue


def extract_m3u8_from_logs(driver):

    streams = set()

    logs = driver.get_log("performance")

    for entry in logs:

        msg = json.loads(entry["message"])["message"]

        if msg["method"] != "Network.requestWillBeSent":
            continue

        url = msg["params"]["request"]["url"]

        if ".m3u8" in url:
            streams.add(url)

    return list(streams)


options = webdriver.ChromeOptions()

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

options.set_capability(
    "goog:loggingPrefs",
    {"performance": "ALL"}
)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

streams = {}

for name, page in channels.items():

    print("Scanning:", name)

    try:
        driver.get(page)
    except:
        print("Page failed")
        continue

    # wait page load
    time.sleep(6)

    # click play
    click_play(driver)

    # wait stream request
    time.sleep(15)

    candidates = extract_m3u8_from_logs(driver)

    found = None

    for c in candidates:

        if test_stream(c):
            found = c
            break

    if found:
        streams[name] = found
        print("Found:", found)
    else:
        print("No stream found")


driver.quit()


# Build playlist
os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("Channels captured:", len(streams))
