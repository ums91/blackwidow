import os
import requests
from urllib.parse import quote

OWNER = "amazeyourself"
REPO = "adaptive-streams"
BRANCH = "main"
BASE_PATH = "streams"

API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"
RAW = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}"

OUTPUT_FOLDER = "playlist"
OUTPUT_FILE = "allchannels.m3u"

session = requests.Session()
session.headers.update({"User-Agent": "playlist-builder"})


def list_contents(path):

    url = f"{API}/{quote(path)}?ref={BRANCH}"
    r = session.get(url)
    r.raise_for_status()

    return r.json()


def extract_from_m3u8(url):

    streams = []

    try:
        r = session.get(url, timeout=20)

        for line in r.text.splitlines():

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "http" in line:
                streams.append(line)

    except:
        pass

    return streams


def scan(path):

    items = list_contents(path)

    collected = []

    for item in items:

        if item["type"] == "dir":

            collected.extend(scan(item["path"]))

        elif item["type"] == "file" and item["name"].endswith(".m3u8"):

            file_url = f"{RAW}/{item['path']}"

            parts = item["path"].split("/")
            group = parts[1] if len(parts) > 1 else "Other"

            streams = extract_from_m3u8(file_url)

            for s in streams:
                collected.append({
                    "group": group.upper(),
                    "name": item["name"].replace(".m3u8", ""),
                    "url": s
                })

    return collected


def build_playlist(streams):

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)

    with open(path, "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")

        for s in streams:
            f.write(f'#EXTINF:-1 group-title="{s["group"]}",{s["name"]}\n')
            f.write(f"{s['url']}\n")


def main():

    print("Scanning repository...")

    streams = scan(BASE_PATH)

    streams.sort(key=lambda x: (x["group"], x["name"]))

    build_playlist(streams)

    print("Playlist created with", len(streams), "streams")


if __name__ == "__main__":
    main()
