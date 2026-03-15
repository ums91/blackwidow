from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os
import re

channels = {
    "PTV Sports": "https://ptvsportshd.com/live",
    "ARY Digital": "https://live.arydigital.tv",
    "ARY News": "https://live.arynews.tv",
    "Geo News": "https://live.geo.tv",
    "Samaa News": "https://www.samaa.tv/live",
    "Aaj News": "https://www.aaj.tv/live",
    "Dunya News": "https://dunyanews.tv/en/Live",
    "Express News": "https://www.express.pk/live/",
    "Bol News": "https://live.bolnetwork.com/",
    "92 News": "https://92newshd.tv/live",
    "Hum TV": "https://www.hum.tv/live",
    "Hum News": "https://humnews.pk/live/",
    "GNN": "https://gnnhd.tv/live",
    "PTV Home": "https://ptv.com.pk/ptvhome/livestream",
    "PTV News": "https://ptv.com.pk/ptvnews/livestream",
    "PTV World": "https://ptv.com.pk/ptvworld/livestream",
    "Madani Channel": "https://madani.tv/live/",
    "Sindh TV": "https://sindhtv.tv/live",
    "Khyber TV": "https://khybernews.tv/live",
    "Pashto 1": "https://pashto1.tv/live"
}

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

    try:

        driver.get(page)

        time.sleep(15)

        logs = driver.get_log("performance")

        for entry in logs:

            msg = json.loads(entry["message"])["message"]

            if msg["method"] != "Network.requestWillBeSent":
                continue

            url = msg["params"]["request"]["url"]

            if ".m3u8" in url:

                clean = re.split(r'\.m3u8', url)[0] + ".m3u8"

                streams[name] = clean

    except:
        pass

driver.quit()

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u", "w") as f:

    f.write("#EXTM3U\n")

    for name, stream in streams.items():

        f.write(f'#EXTINF:-1 group-title="Pakistan",{name}\n')
        f.write(stream + "\n")

print("Channels captured:", len(streams))
