from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json, time, os, requests, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp


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
# FULL Source discovery (unchanged)
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

                discovered[m.split("/")[2]] = m

        except:
            pass

    return discovered


# ----------------------------
# Helpers
# ----------------------------

def is_stream(url):
    return ".m3u8" in url or ".mpd" in url


# ----------------------------
# 🔥 Interaction Layer
# ----------------------------

def click_live_button(driver):

    keywords = ["live", "watch", "stream", "on air"]

    elements = driver.find_elements("xpath", "//a | //button")

    for el in elements:
        try:
            text = (el.text or "").lower()

            if any(k in text for k in keywords):
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", el)
                print("▶ Clicked live button:", text)
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
        ".vjs-big-play-button",
        ".jw-icon-play",
        ".plyr__control--overlaid",
        ".ytp-large-play-button",
        "button"
    ]

    for sel in selectors:
        try:
            elements = driver.find_elements("css selector", sel)
            for el in elements:
                driver.execute_script("arguments[0].click();", el)
                print("▶ Clicked:", sel)
                return True
        except:
            continue

    return False


def handle_iframes_and_play(driver):

    iframes = driver.find_elements("tag name", "iframe")

    for i, frame in enumerate(iframes):
        try:
            driver.switch_to.frame(frame)
            print(f"🔁 Switched iframe {i}")

            if smart_play(driver):
                return True

            inner_iframes = driver.find_elements("tag name", "iframe")

            for j, inner in enumerate(inner_iframes):
                try:
                    driver.switch_to.frame(inner)
                    print(f"🔁 Nested iframe {i}.{j}")

                    if smart_play(driver):
                        return True

                    driver.switch_to.parent_frame()

                except:
                    continue

            driver.switch_to.default_content()

        except:
            driver.switch_to.default_content()
            continue

    return False


# ----------------------------
# 🔥 Network capture
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

                    if is_stream(url):
                        print("🎯 Found:", url)
                        found.add(url)

            except:
                continue

        if found:
            break

    return list(found)


# ----------------------------
# Selenium worker
# ----------------------------

def scan_channel(name, page):

    print(f"\n🔎 Scanning: {page}")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(page)
        driver.get_log("performance")

        time.sleep(5)

        click_live_button(driver)
        time.sleep(3)

        smart_play(driver)
        handle_iframes_and_play(driver)

        candidates = capture_streams(driver)

        if candidates:
            return name, candidates[0]

    except:
        pass

    driver.quit()
    return name, None


# ----------------------------
# Run parallel scanning
# ----------------------------

channels = discover_live_pages()
streams = {}

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(scan_channel, n, p) for n, p in channels.items()]

    for f in as_completed(futures):
        name, stream = f.result()
        if stream:
            streams[name] = stream


# ----------------------------
# YouTube via yt-dlp
# ----------------------------

def extract_youtube(url):
    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if "url" in info:
                return info["url"]

            if "formats" in info:
                for f in info["formats"]:
                    if f.get("protocol") == "m3u8":
                        return f.get("url")

    except:
        pass

    return None


for name, url in youtube_channels.items():
    print("▶ YouTube:", name)
    s = extract_youtube(url)
    if s:
        streams[name] = s
        print("✅ YouTube OK")


# ----------------------------
# Build playlist
# ----------------------------

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:
    f.write("#EXTM3U\n")

    for name, url in streams.items():
        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(url + "\n")


print("\n🚀 TOTAL CHANNELS:", len(streams))
