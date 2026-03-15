import os
import requests
from urllib.parse import quote

OWNER = "amazeyourself"
REPO = "adaptive-streams"
BRANCH = "main"
BASE_PATH = "streams"

API_BASE = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"
RAW_BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}"

OUTPUT_FOLDER = "playlist"
OUTPUT_FILE = "allchannels.m3u"

session = requests.Session()
session.headers.update({
    "Accept": "application/vnd.github+json",
    "User-Agent": "playlist-builder"
})

def list_contents(path):
    url = f"{API_BASE}/{quote(path)}?ref={BRANCH}"
    r = session.get(url)
    r.raise_for_status()
    return r.json()

def collect_streams(path):

    items = list_contents(path)
    streams = []

    for item in items:

        if item["type"] == "dir":
            streams.extend(collect_streams(item["path"]))

        elif item["type"] == "file" and item["name"].endswith(".m3u8"):

            parts = item["path"].split("/")
            country = parts[1] if len(parts) > 1 else "Other"
            channel = os.path.splitext(parts[-1])[0]

            streams.append({
                "name": channel,
                "group": country.upper(),
                "url": f"{RAW_BASE}/{item['path']}"
            })

    return streams


def build_playlist(streams):

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    filepath = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)

    with open(filepath, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for s in streams:
            f.write(f'#EXTINF:-1 group-title="{s["group"]}",{s["name"]}\n')
            f.write(f"{s['url']}\n")


def main():

    streams = collect_streams(BASE_PATH)

    streams.sort(key=lambda x: (x["group"], x["name"]))

    build_playlist(streams)

    print("Playlist updated:", len(streams), "channels")


if __name__ == "__main__":
    main()
