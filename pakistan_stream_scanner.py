from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os
import requests
import re


# ----------------------------
# YouTube Channels
# ----------------------------

youtube_channels = {
    "Geo News": "https://www.youtube.com/@geonews/live",
    "ARY News": "https://www.youtube.com/@arynews/live",
    "Hum News": "https://www.youtube.com/@HumNewsPK/live",
    "Dunya News": "https://www.youtube.com/@DunyaNews/live",
    "Samaa TV": "https://www.youtube.com/@SamaaTV/live",
    "92 News": "https://www.youtube.com/@92NewsHD/live",
    "Bol News": "https://www.youtube.com/@BOLNewsofficial/live",
    "GNN": "https://www.youtube.com/@GNNHD/live",
    "Aaj News": "https://www.youtube.com/@AajTVofficial/live",
    "Express News": "https://www.youtube.com/@ExpressNewsPK/live",
    "PTV News": "https://www.youtube.com/@PTVNewsOfficial/live",
    "PTV Sports": "https://www.youtube.com/@PTVSportsOfficial/live",
}


# ----------------------------
# Source discovery
# ----------------------------

def discover_live_pages():

    sources = [
        "https://www.geo.tv",
        "https://harpalgeo.tv",
        "https://geokahani.tv",
        "https://arynews.tv",
        "https://arydigital.tv",
        "https://aryqtv.tv",
        "https://hum.tv",
        "https://humnews.pk",
        "https://humsitaray.tv",
        "https://hum.tv/masala-tv",
        "https://express.pk",
        "https://expressentertainment.tv",
        "https://dunyanews.tv",
        "https://92newshd.tv",
        "https://gnnhd.tv",
        "https://samaa.tv",
        "https://aaj.tv",
        "https://bolnetwork.com",
        "https://ptv.com.pk",
        "https://ptv.com.pk/ptvnews",
        "https://ptv.com.pk/ptvsports",
        "https://ptv.com.pk/ptvhome",
        "https://khybernews.tv",
        "https://rohi.tv",
        "https://sindhtv.tv",
        "https://madani.tv",
        "https://noortv.pk",
        "https://paighamtv.com",
        "https://city42.tv",
        "https://city41.tv",
        "https://city21.tv",
    ]

    discovered = {}

    for site in sources:
        try:
            r = requests.get(site, timeout=6)

            matches = re.findall(r'href="([^"]*live[^"]*)"', r.text)

            for m in matches:

                if not m.startswith("http"):
                    m = site.rstrip("/") + m

                name = m.split("/")[2]

                discovered[name] = m

        except:
            pass

    return discovered


# ----------------------------
# Search discovery
# ----------------------------

def discover_from_search():

    queries = [
        "site:geo.tv live",
        "site:arynews.tv live",
        "site:hum.tv live",
        "site:dunyanews.tv live",
        "site:samaa.tv live",
        "site:aaj.tv live",
        "site:express.pk live",
        "site:bolnetwork.com live",
        "site:ptv.com.pk live",
        "pakistan tv live stream"
    ]

    discovered = {}

    for q in queries:

        try:
            url = f"https://duckduckgo.com/html/?q={q}"

            r = requests.get(url, timeout=8)

            matches = re.findall(r'href="(https?://[^"]+)"', r.text)

            for m in matches:

                if "live" in m:

                    name = m.split("/")[2]

                    discovered[name] = m

        except:
            pass

    return discovered


channels = discover_live_pages()
channels.update(discover_from_search())


# ----------------------------
# Manifest helpers
# ----------------------------

def fetch_manifest(url):

    try:
        r = requests.get(url, timeout=8)

        if r.status_code == 200:
            return r.text

    except:
        pass

    return None


def test_stream(url):

    text = fetch_manifest(url)

    if not text:
        return False

    if url.endswith(".m3u8") and "#EXTM3U" in text:
        return True

    if url.endswith(".mpd") and "<MPD" in text:
        return True

    return False


def upgrade_to_master(url):

    if not url.endswith(".m3u8"):
        return url

    base = url.rsplit("/", 1)[0]

    candidates = [
        base + "/master.m3u8",
        base + "/playlist.m3u8",
        base + "/index.m3u8",
        base + "/main.m3u8"
    ]

    for c in candidates:

        if test_stream(c):
            return c

    return url


def choose_variant(master_url):

    if not master_url.endswith(".m3u8"):
        return master_url

    text = fetch_manifest(master_url)

    if not text:
        return master_url

    lines = text.splitlines()

    streams = []

    for i, line in enumerate(lines):

        if "#EXT-X-STREAM-INF" in line:

            stream = lines[i + 1].strip()

            if not stream.startswith("http"):
                base = master_url.rsplit("/", 1)[0]
                stream = base + "/" + stream

            streams.append(stream)

    if not streams:
        return master_url

    for s in streams:
        if "480" in s:
            return s

    for s in streams:
        if "720" in s:
            return s

    return streams[0]


# ----------------------------
# Player interaction
# ----------------------------

def click_play(driver):

    selectors = [
        ".vjs-big-play-button",
        ".jw-icon-play",
        ".plyr__control--overlaid",
        ".play-button",
        "button",
        "video"
    ]

    for sel in selectors:

        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            driver.execute_script("arguments[0].click();", el)
            return

        except:
            continue


# ----------------------------
# Stream extraction
# ----------------------------

def extract_from_network(driver):

    streams = set()

    logs = driver.get_log("performance")

    for entry in logs:

        msg = json.loads(entry["message"])["message"]

        if msg["method"] == "Network.responseReceived":

            url = msg["params"]["response"]["url"]

            if ".m3u8" in url or ".mpd" in url:
                streams.add(url)

    return list(streams)


def extract_from_source(driver):

    streams = set()

    try:

        source = driver.page_source

        m3u = re.findall(r'https?://[^"]+\.m3u8[^"]*', source)
        mpd = re.findall(r'https?://[^"]+\.mpd[^"]*', source)

        for m in m3u:
            streams.add(m)

        for m in mpd:
            streams.add(m)

    except:
        pass

    return list(streams)


# ----------------------------
# CDN discovery
# ----------------------------

def generate_cdn_candidates():

    slugs = [
        "geonews","harpalgeo","arynews","arydigital","aryqtv",
        "humtv","humnews","dunyanews","expressnews","bolnews",
        "aajnews","samaanews","92news","gnn","ptvsports"
    ]

    hosts = [
        "https://cdn-live.streamlock.net",
        "https://5centscdn.streamlock.net",
        "https://edge.streamlock.net"
    ]

    playlists = [
        "playlist.m3u8",
        "index.m3u8",
        "master.m3u8"
    ]

    urls = []

    for h in hosts:
        for s in slugs:
            for p in playlists:
                urls.append(f"{h}/{s}/{s}/{p}")

    return urls


# ----------------------------
# YouTube extraction
# ----------------------------

def extract_youtube_stream(url):

    try:

        r = requests.get(url, timeout=8)

        matches = re.findall(r'https://manifest\.googlevideo\.com[^"]+\.m3u8[^"]*', r.text)

        if matches:
            return matches[0]

    except:
        pass

    return None


# ----------------------------
# Selenium setup
# ----------------------------

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


# ----------------------------
# Website scanning
# ----------------------------

for name, page in channels.items():

    print("Scanning:", page)

    try:
        driver.get(page)
        driver.get_log("performance")

    except:
        print("Page failed")
        continue

    time.sleep(6)

    click_play(driver)

    time.sleep(18)

    candidates = set()

    candidates.update(extract_from_network(driver))
    candidates.update(extract_from_source(driver))

    candidates = list(candidates)

    found = None

    for c in candidates:

        upgraded = upgrade_to_master(c)

        if test_stream(upgraded):

            final_stream = choose_variant(upgraded)

            found = final_stream
            break

    if found:

        streams[name] = found
        print("Found:", found)

    else:

        print("No stream found")


driver.quit()


# ----------------------------
# CDN discovery
# ----------------------------

cdn_urls = generate_cdn_candidates()

for url in cdn_urls:

    if test_stream(url):

        name = url.split("/")[3]

        if name not in streams:

            streams[name] = url
            print("CDN discovered:", name)


# ----------------------------
# YouTube discovery
# ----------------------------

for name, url in youtube_channels.items():

    print("Checking YouTube:", name)

    stream = extract_youtube_stream(url)

    if stream:

        if name not in streams:

            streams[name] = stream
            print("YouTube stream found:", stream)


# ----------------------------
# Build playlist
# ----------------------------

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, url in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("Channels captured:", len(streams))
