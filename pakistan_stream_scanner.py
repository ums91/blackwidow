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
    "Aaj News": "https://www.aaj.tv/live"
}

cdn_candidates = {
    "Geo News": "https://live.geo.tv/geonews/index.m3u8",
    "Aaj News": "https://stream.aaj.tv/aajnews/aajnews/index.m3u8",
    "Samaa News": "https://stream.samaa.tv/samaa/samaa3/index.m3u8",
    "PTV News": "https://live.ptv.com.pk/PTVNewsHD/index.m3u8",
    "PTV World": "https://live.ptv.com.pk/PTVWorldHD/index.m3u8",
}

def clean_url(url):
    return re.split(r'\.m3u8', url)[0] + ".m3u8"


def test_stream(url):

    try:

        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return False

        if "#EXTM3U" in r.text:
            return True

    except:
        pass

    return False


def derive_cloudflare_master(url):

    if "cloudflarestream.com" in url:

        parts = url.split("/")

        if "manifest" in parts:

            idx = parts.index("manifest")

            video_id = parts[idx - 1]

            return f"https://{parts[2]}/{video_id}/manifest/video.m3u8"

    return None


def switch_iframe(driver):

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for frame in iframes:
            driver.switch_to.frame(frame)
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

# ---- Selenium scanning ----
for name, page in channels.items():

    print("Scanning page:", name)

    driver.get(page)

    time.sleep(8)

    switch_iframe(driver)

    candidates = set()

    for _ in range(3):

        logs = driver.get_log("performance")

        for entry in logs:

            msg = json.loads(entry["message"])["message"]

            if msg["method"] != "Network.requestWillBeSent":
                continue

            url = msg["params"]["request"]["url"]

            if ".m3u8" in url:

                candidates.add(clean_url(url))

        time.sleep(5)

    for c in candidates:

        master = derive_cloudflare_master(c)

        if master and test_stream(master):

            streams[name] = master
            break

        if test_stream(c):

            streams[name] = c
            break


driver.quit()

# ---- CDN discovery ----
for name, url in cdn_candidates.items():

    if name not in streams:

        if test_stream(url):

            streams[name] = url

            print("CDN stream found:", name)


os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("Total channels:", len(streams))
