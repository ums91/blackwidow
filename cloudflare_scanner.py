import re
import requests
import os

pages = [
    "https://ptvsportshd.com/live",
    "https://live.arydigital.tv",
    "https://live.arynews.tv",
    "https://live.geo.tv"
]

pattern = r"[a-f0-9]{32}"

found = set()

for page in pages:

    try:
        r = requests.get(page, timeout=20)

        ids = re.findall(pattern, r.text)

        for vid in ids:
            found.add(vid)

    except:
        pass


streams = []

for vid in found:

    url = f"https://customer-jfpjrgh1mi5y63cd.cloudflarestream.com/{vid}/manifest/video.m3u8"

    streams.append(url)


os.makedirs("playlist", exist_ok=True)

with open("playlist/pakistan_cloudflare.m3u","w") as f:

    f.write("#EXTM3U\n")

    for i, s in enumerate(streams):

        f.write(f"#EXTINF:-1,Pakistan Channel {i+1}\n{s}\n")

print("Streams found:", len(streams))
