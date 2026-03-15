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
    "Harpal Geo": "https://harpalgeo.tv/live",
    "Madani Channel": "https://madani.tv/live",
    "Khyber News": "https://khybernews.tv/live",
    "Sindh TV": "https://sindhtv.tv/live",
    "Rohi TV": "https://rohi.tv/live",
    "Pashto 1": "https://pashto1.tv/live",
    "City42": "https://city42.tv/live",
    "City41": "https://city41.tv/live",
    "City21": "https://city21.tv/live"
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


def extract_m3u8_from_source(driver):

    urls = set()

    try:

        source = driver.page_source

        matches = re.findall(r'https?://[^"]+\.m3u8[^"]*', source)

        for m in matches:
            urls.add(m)

    except:
        pass

    return list(urls)


def generate_cdn_candidates():

    slugs = [
        "geonews","harpalgeo","arynews","arydigital","aryqtv",
        "humtv","humnews","dunyanews","expressnews","bolnews",
        "aajnews","samaanews","92news"
    ]

    patterns = [
        "https://cdn-live.streamlock.net/{}/{}/playlist.m3u8",
        "https://5centscdn.streamlock.net/{}/{}/playlist.m3u8",
        "https://cdn-live.streamlock.net/{}/{}/index.m3u8",
        "https://5centscdn.streamlock.net/{}/{}/index.m3u8"
    ]

    urls = []

    for slug in slugs:
        for p in patterns:
            urls.append(p.format(slug, slug))

    return urls


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


# -------------------
# Website scanning
# -------------------

for name, page in channels.items():

    print("Scanning:", name)

    try:
        driver.get(page)
    except:
        print("Page unreachable")
        continue

    time.sleep(12)

    found_stream = None

    # Source scan
    source_streams = extract_m3u8_from_source(driver)

    for s in source_streams:

        if test_stream(s):

            found_stream = s
            break


    # Iframe scan
    if not found_stream:

        targets = get_iframe_sources(driver)

        for target in targets:

            try:
                driver.get(target)
            except:
                continue

            time.sleep(10)

            iframe_streams = extract_m3u8_from_source(driver)

            for s in iframe_streams:

                if test_stream(s):

                    found_stream = s
                    break

            if found_stream:
                break


    # Network scan
    if not found_stream:

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

        streams[name] = found_stream
        print("Found:", found_stream)

    else:

        print("No stream detected")


driver.quit()


# -------------------
# CDN discovery
# -------------------

cdn_urls = generate_cdn_candidates()

for url in cdn_urls:

    if test_stream(url):

        name = url.split("/")[3]

        if name not in streams:

            streams[name] = url
            print("CDN discovered:", name)


# -------------------
# Build playlist
# -------------------

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("Channels captured:", len(streams))
