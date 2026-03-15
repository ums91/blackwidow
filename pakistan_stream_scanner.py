from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os

pages = [
    "https://ptvsportshd.com/live",
    "https://live.arydigital.tv",
    "https://live.arynews.tv",
    "https://live.geo.tv",
    "https://www.samaa.tv/live",
    "https://www.aaj.tv/live"
]

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

streams = set()

for page in pages:

    driver.get(page)

    time.sleep(15)

    logs = driver.get_log("performance")

    for entry in logs:

        msg = json.loads(entry["message"])["message"]

        if msg["method"] != "Network.requestWillBeSent":
            continue

        url = msg["params"]["request"]["url"]

        if ".m3u8" in url:
            streams.add(url)

driver.quit()

os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan.m3u","w") as f:

    f.write("#EXTM3U\n")

    for i, s in enumerate(streams):
        f.write(f"#EXTINF:-1 group-title=\"Pakistan\",Channel {i+1}\n{s}\n")

print("Streams found:", len(streams))
