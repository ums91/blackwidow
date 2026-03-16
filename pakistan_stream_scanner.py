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
    selectors = [
        ".vjs-big-play-button",
        ".jw-icon-play",
        ".plyr__control--overlaid",
        ".play-button",
        "video"
    ]

    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", el)
            return
        except:
            continue


def extract_from_html(driver):
    streams = set()

    try:
        source = driver.page_source
        matches = re.findall(r'https?://[^"]+\.m3u8[^"]*', source)

        for m in matches:
            streams.add(m)
    except:
        pass

    return streams


def extract_from_network(driver):
    streams = set()

    logs = driver.get_log("performance")

    for entry in logs:

        msg = json.loads(entry["message"])["message"]

        if msg["method"] == "Network.responseReceived":

            url = msg["params"]["response"]["url"]

            if ".m3u8" in url:
                streams.add(url)

    return streams


def scan_iframes(driver):

    streams = set()

    try:

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for frame in iframes:

            src = frame.get_attribute("src")

            if not src:
                continue

            driver.switch_to.frame(frame)

            click_play(driver)

            time.sleep(10)

            streams |= extract_from_html(driver)
            streams |= extract_from_network(driver)

            driver.switch_to.default_content()

    except:
        pass

    return streams


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

        # clear previous logs
        driver.get_log("performance")

    except:

        print("Page unreachable")
        continue


    time.sleep(6)

    click_play(driver)

    time.sleep(20)


    found = set()

    found |= extract_from_html(driver)
    found |= extract_from_network(driver)
    found |= scan_iframes(driver)


    working = None

    for url in found:

        if test_stream(url):

            working = url
            break


    if working:

        streams[name] = working
        print("FOUND:", working)

    else:

        print("No stream detected")


driver.quit()


# Build playlist

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("Channels captured:", len(streams))
