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
        "https://www.geo.tv","https://harpalgeo.tv","https://geokahani.tv",
        "https://arynews.tv","https://arydigital.tv","https://aryqtv.tv",
        "https://hum.tv","https://humnews.pk","https://humsitaray.tv",
        "https://hum.tv/masala-tv","https://express.pk","https://expressentertainment.tv",
        "https://dunyanews.tv","https://92newshd.tv","https://gnnhd.tv",
        "https://samaa.tv","https://aaj.tv","https://bolnetwork.com",
        "https://ptv.com.pk","https://ptv.com.pk/ptvnews","https://ptv.com.pk/ptvsports",
    ]

    discovered = {}

    for site in sources:
        try:
            r = requests.get(site, timeout=6)
            matches = re.findall(r'href="([^"]*live[^"]*)"', r.text)

            for m in matches:
                if not m.startswith("http"):
                    m = site.rstrip("/") + m
                discovered[m.split("/")[2]] = m
        except:
            pass

    return discovered


def discover_from_search():
    queries = ["pakistan tv live stream"]
    discovered = {}

    for q in queries:
        try:
            url = f"https://duckduckgo.com/html/?q={q}"
            r = requests.get(url, timeout=8)
            matches = re.findall(r'href="(https?://[^"]+)"', r.text)

            for m in matches:
                if "live" in m:
                    discovered[m.split("/")[2]] = m
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
    return "#EXTM3U" in text or "<MPD" in text


def upgrade_to_master(url):
    if not url.endswith(".m3u8"):
        return url

    base = url.rsplit("/", 1)[0]

    for p in ["master.m3u8", "playlist.m3u8", "index.m3u8"]:
        test = base + "/" + p
        if test_stream(test):
            return test

    return url


def choose_variant(master_url):
    text = fetch_manifest(master_url)
    if not text:
        return master_url

    lines = text.splitlines()
    streams = []

    for i, line in enumerate(lines):
        if "#EXT-X-STREAM-INF" in line:
            s = lines[i+1].strip()
            if not s.startswith("http"):
                s = master_url.rsplit("/", 1)[0] + "/" + s
            streams.append(s)

    if not streams:
        return master_url

    for s in streams:
        if "720" in s:
            return s
    for s in streams:
        if "480" in s:
            return s

    return streams[0]


# ----------------------------
# Player interaction
# ----------------------------

def click_play(driver):
    try:
        driver.execute_script("document.querySelector('video')?.play()")
    except:
        pass


# ----------------------------
# 🔥 NEW: Continuous network capture
# ----------------------------

def capture_streams(driver, timeout=25):
    found = set()
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(2)

        logs = driver.get_log("performance")

        for entry in logs:
            try:
                msg = json.loads(entry["message"])["message"]

                if msg["method"] == "Network.responseReceived":
                    url = msg["params"]["response"]["url"]

                    if ".m3u8" in url or ".mpd" in url:
                        print("Captured:", url)
                        found.add(url)

            except:
                continue

        if found:
            break

    return list(found)


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

    print("\nScanning:", page)

    try:
        driver.get(page)
        driver.get_log("performance")  # clear logs
    except:
        print("Page failed")
        continue

    time.sleep(5)

    click_play(driver)

    candidates = capture_streams(driver)

    for c in candidates:

        upgraded = upgrade_to_master(c)

        if test_stream(upgraded):
            final = choose_variant(upgraded)
            streams[name] = final
            print("✅ Found:", final)


driver.quit()


# ----------------------------
# YouTube (basic extraction)
# ----------------------------

def extract_youtube_stream(url):
    try:
        r = requests.get(url, timeout=8)
        matches = re.findall(r'https://manifest\.googlevideo\.com[^"]+', r.text)
        if matches:
            return matches[0]
    except:
        pass
    return None


for name, url in youtube_channels.items():
    print("Checking YouTube:", name)
    s = extract_youtube_stream(url)
    if s:
        streams[name] = s


# ----------------------------
# Build playlist
# ----------------------------

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:
    f.write("#EXTM3U\n")

    for name, url in streams.items():
        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("\n🔥 Channels captured:", len(streams))
