import requests
import json
import os
import re
import sys

# Configurable limits
ITEM_LIMIT = 4  # Set to 0 for no limit
OUTPUT_DIR = ".output"
RESUME_FILE = "site_status.json"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load settings
print("Loading settings...")
with open("settings.json") as f:
    settings = json.load(f)

TOKEN = settings["token"]
BASE_URL = settings["base_url"]
headers = {"Authorization": f"Token {TOKEN}"}
totalImages = 0

# Load completed site list
if os.path.exists(RESUME_FILE):
    with open(RESUME_FILE) as f:
        completed_sites = set(json.load(f))
else:
    completed_sites = set()

# Get accessible sites
self_resp = requests.get(f"{BASE_URL}/self", headers=headers)
self_resp.raise_for_status()
site_info = self_resp.json()
sites = [s for s in site_info.get("privileges", []) if isinstance(s, dict) and s.get("scope") == "site"]

if ITEM_LIMIT:
    sites = sites[:ITEM_LIMIT]

print(f"Found {len(sites)} site(s).")

# Process each site
for site_index, site in enumerate(sites, start=1):
    site_name = site.get("name")
    site_id = site.get("site_id")

    if site_name in completed_sites:
        print(f"  Skipping Site {site_index:03}/{len(sites):03}...")
        continue

    aps_url = f"{BASE_URL}/sites/{site_id}/devices"
    aps_resp = requests.get(aps_url, headers=headers)
    aps_resp.raise_for_status()
    aps = aps_resp.json()

    if ITEM_LIMIT:
        aps = aps[:ITEM_LIMIT]

    site_dir = os.path.join(OUTPUT_DIR, site_name.replace(" ", "_"))
    os.makedirs(site_dir, exist_ok=True)

    for ap_index, ap in enumerate(aps, start=1):
        ap_name = re.sub(r'[\\/:*?"<>|\t\n\r]', '_', ap.get("name", "unknown_ap")).replace(" ", "_")

        print(f"Processing Site {site_index:03}/{len(sites):03}, AP {ap_index:02}/{len(aps):02}...", end='', flush=True)

        for i in range(1, 10):
            image_url = ap.get(f"image{i}_url")
            if not image_url:
                break

            filename = f"{ap_name}-image-{i:02}.jpg"
            image_path = os.path.join(site_dir, filename)

            if os.path.exists(image_path):
                continue

            resp = requests.get(image_url, headers=headers)
            if resp.status_code == 200:
                with open(image_path, "wb") as f:
                    f.write(resp.content)
                totalImages += 1
            else:
                print(f"\nERROR: Failed to download image {image_url} (status {resp.status_code})")
                sys.exit(1)

        print(" DONE. (Total images downloaded: {:,})".format(totalImages))

    completed_sites.add(site_name)
    with open(RESUME_FILE, "w") as f:
        json.dump(sorted(completed_sites), f, indent=2)
