from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os
import requests


channels = {
    "PTV Sports": "https://ptvsportshd.com/live",
    "ARY Digital": "https://live.arydigital.tv",
    "ARY News": "https://live.arynews.tv",
    "Geo News": "https://live.geo.tv",
    "Samaa News": "https://www.samaa.tv/live",
    "Aaj News": "https://www.aaj.tv/live"
}


def test_stream(url):

    try:

        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return False

        if "#EXTM3U" in r.text or "#EXTINF" in r.text:
            return True

    except:
        pass

    return False


def get_iframe_sources(driver):

    sources = []

    try:

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for frame in iframes:

            src = frame.get_attribute("src")

            if src:
                sources.append(src)

    except:
        pass

    return sources


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

    time.sleep(8)

    targets = [page]

    # detect iframe players
    targets += get_iframe_sources(driver)

    found_stream = None

    for target in targets:

        try:

            driver.get(target)

            time.sleep(8)

            logs = driver.get_log("performance")

            for entry in logs:

                msg = json.loads(entry["message"])["message"]

                if msg["method"] != "Network.requestWillBeSent":
                    continue

                url = msg["params"]["request"]["url"]

                if ".m3u8" in url:

                    if test_stream(url):

                        found_stream = url
                        break

            if found_stream:
                break

        except:
            pass

    if found_stream:

        streams[name] = found_stream

        print("Found:", found_stream)

    else:

        print("No stream detected")


driver.quit()


os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')

        f.write(url + "\n")


print("Channels captured:", len(streams))
