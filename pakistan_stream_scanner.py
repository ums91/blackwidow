import json, time, os, requests, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp

from selenium import webdriver


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
# Sources (ALL intact)
# ----------------------------

def discover_live_pages():
    sources = [
        "https://www.geo.tv","https://live.arydigital.tv","https://webtv.92newshd.tv","https://www.express.pk/live","https://humnews.pk/live","https://harpalgeo.tv","https://geokahani.tv",
        "https://arynews.tv","https://arydigital.tv","https://www.dawateislami.net/pk/islam/streaming/watch-live-madani-channel.htm","https://live.aryqtv.tv/",
        "https://hum.tv","https://humnews.pk","https://humsitaray.tv",
        "https://hum.tv/masala-tv","https://express.pk","https://expressentertainment.tv",
        "https://dunyanews.tv","https://92newshd.tv","https://gnnhd.tv",
        "https://samaa.tv","https://aaj.tv","https://bolnetwork.com",
        "https://ptv.com.pk","https://ptv.com.pk/ptvnews","https://ptv.com.pk/ptvsports",
        "https://ptv.com.pk/ptvhome","https://khybernews.tv","https://rohi.tv",
        "https://sindhtv.tv","https://madani.tv","https://noortv.pk",
        "https://paighamtv.com","https://city42.tv","https://city41.tv","https://city21.tv",
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


def is_stream(url):
    return ".m3u8" in url or ".mpd" in url


# ----------------------------
# Interaction
# ----------------------------

def click_live_button(driver):
    keywords = ["live", "watch", "stream", "on air"]

    for el in driver.find_elements("xpath", "//a | //button"):
        try:
            text = (el.text or "").lower()
            if any(k in text for k in keywords):
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", el)
                return True
        except:
            continue
    return False


def smart_play(driver):
    try:
        driver.execute_script("document.querySelector('video')?.play()")
    except:
        pass

    selectors = [
        ".vjs-big-play-button",".jw-icon-play",
        ".plyr__control--overlaid",".ytp-large-play-button","button"
    ]

    for sel in selectors:
        try:
            for el in driver.find_elements("css selector", sel):
                driver.execute_script("arguments[0].click();", el)
                return True
        except:
            continue
    return False


def handle_iframes(driver):
    for frame in driver.find_elements("tag name", "iframe"):
        try:
            driver.switch_to.frame(frame)

            if smart_play(driver):
                return True

            for inner in driver.find_elements("tag name", "iframe"):
                try:
                    driver.switch_to.frame(inner)
                    if smart_play(driver):
                        return True
                    driver.switch_to.parent_frame()
                except:
                    continue

            driver.switch_to.default_content()
        except:
            driver.switch_to.default_content()

    return False


# ----------------------------
# Network capture
# ----------------------------

def capture_streams(driver, timeout=25):
    found = set()
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(2)

        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])["message"]
                if msg["method"] == "Network.responseReceived":
                    url = msg["params"]["response"]["url"]
                    if is_stream(url):
                        found.add(url)
            except:
                continue

        if found:
            break

    return list(found)


# ----------------------------
# Driver factory (stable)
# ----------------------------

def create_driver():
    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    for _ in range(3):
        try:
            return webdriver.Chrome(options=options)
        except:
            time.sleep(2)

    return None


# ----------------------------
# Worker
# ----------------------------

def scan(name, page):

    driver = create_driver()
    if not driver:
        return name, None

    try:
        driver.get(page)
        driver.get_log("performance")

        time.sleep(5)

        click_live_button(driver)
        time.sleep(3)

        smart_play(driver)
        handle_iframes(driver)

        streams = capture_streams(driver)

        if streams:
            return name, streams[0]

    except:
        pass

    driver.quit()
    return name, None


# ----------------------------
# Run parallel
# ----------------------------

channels = discover_live_pages()
streams = {}

with ThreadPoolExecutor(max_workers=5) as ex:
    futures = [ex.submit(scan, n, p) for n, p in channels.items()]

    for f in as_completed(futures):
        name, url = f.result()
        if url:
            streams[name] = url


# ----------------------------
# YouTube
# ----------------------------

def yt_stream(url):
    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url")
    except:
        return None


for n, u in youtube_channels.items():
    s = yt_stream(u)
    if s:
        streams[n] = s


# ----------------------------
# Playlist
# ----------------------------

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:
    f.write("#EXTM3U\n")

    for name, url in streams.items():
        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("TOTAL CHANNELS:", len(streams))
