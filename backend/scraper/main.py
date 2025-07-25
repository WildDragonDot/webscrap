import json
import time
import urllib.request
import urllib.error
import pandas as pd
import os
import re

# --- Config ---
PROJECTS_API = "https://dorahacks.io/api/hackathon-buidls/wchl25-qualification-round/?page={}&page_size=10"
HACKERS_API = "https://dorahacks.io/api/hackathon/wchl25-qualification-round/hackers/?page={}&page_size=10"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json',
    'Referer': 'https://dorahacks.io/',
    'Origin': 'https://dorahacks.io',
    'Accept-Language': 'en-US,en;q=0.9'
}
MAX_RETRIES = 5
RETRY_DELAY = 2
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
print("📂 Data directory:", DATA_DIR)
EXCEL_FILE = os.path.join(BASE_DIR, "final_dorahacks_data.xlsx")


# --- Helpers ---
def clean_text(value):
    if not isinstance(value, str):
        return value
    return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)


def save_json(data, filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved {len(data)} items to {filepath}")
    except Exception as e:
        print(f"❌ Failed to save JSON to {filepath}: {e}")


def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Corrupted JSON file: {filename}. Starting fresh.")
        except Exception as e:
            print(f"❌ Failed to read {filename}: {e}")
    return []


def fetch_paginated_data(url_template, label="", cache_file=None, key_field="id"):
    print(f"📡 Fetching {label} data from API...")
    old_data = load_json(cache_file)
    seen_ids = {d.get(key_field) for d in old_data}
    new_data = []

    page = 1
    while True:
        url = url_template.format(page)
        req = urllib.request.Request(url, headers=HEADERS)

        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req) as res:
                    if res.status != 200:
                        raise urllib.error.HTTPError(url, res.status, "Invalid status", res.headers, None)

                    data = json.loads(res.read())
                    results = data.get("results", data)

                    if not isinstance(results, list):
                        print(f"⚠️ Unexpected format for {label} on page {page}: {type(results)}")
                        return save_and_return(cache_file, new_data, old_data, label)

                    if not results:
                        print(f"✅ No more {label} data after page {page}")
                        return save_and_return(cache_file, new_data, old_data, label)

                    for item in results:
                        item_id = item.get(key_field)
                        if item_id in seen_ids:
                            print(f"🛑 Duplicate {label} ID {item_id} found. Ending fetch.")
                            return save_and_return(cache_file, new_data, old_data, label)
                        new_data.append(item)

                    print(f"✅ {label} Page {page}: {len(results)} item(s) fetched")
                    page += 1
                    break

            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                print(f"❌ Network error on {label} page {page}, attempt {attempt + 1}: {e}")
                time.sleep(RETRY_DELAY)
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON on {label} page {page}: {e}")
                break
            except Exception as e:
                print(f"❌ Unexpected error on {label} page {page}: {e}")
                break
        else:
            print(f"🚫 Failed to fetch {label} after {MAX_RETRIES} retries.")
            break

    return save_and_return(cache_file, new_data, old_data, label)


def save_and_return(cache_file, new_data, old_data, label):
    combined = new_data + old_data
    if cache_file:
        save_json(combined, cache_file)
    print(f"📦 Total {label} records after merge: {len(combined)}\n")
    return combined


def build_hacker_username_to_org_map(hackers):
    print("🔍 Building username → org mapping...")
    mapping = {}
    for h in hackers:
        try:
            hacker = h.get("hacker", {})
            username = hacker.get("username")
            if username:
                mapping[username] = hacker.get("org", "").strip()
        except Exception as e:
            print(f"⚠️ Skipped malformed hacker record: {e}")
    return mapping


def merge_data(projects, hacker_org_map):
    print("🧩 Merging project and hacker org data...")
    rows = []
    for idx, project in enumerate(projects, start=1):
        try:
            members = project.get("project_members", [])
            orgs = []

            for m in members:
                member = m.get("member")
                if member:
                    username = member.get("username")
                    if username:
                        org = hacker_org_map.get(username, "").strip()
                        if org:
                            orgs.append(org)

            orgs = list(set(orgs))
            full_orgs = [o for o in orgs if len(o.split()) > 1]
            project_org = max(full_orgs, key=len) if full_orgs else (max(orgs, key=len) if orgs else "")

            row = {
                "BUIDL ID": project.get("id"),
                "BUIDL name": clean_text(project.get("name")),
                "BUIDL profile": f'https://dorahacks.io/buidl/{project.get("id")}',
                "Contact email": clean_text(project.get("email")),
                "BUIDL last updated time (UTC)": project.get("update_time") or "",
                "Submission time (UTC)": project.get("submission_time") or "",
                "BUIDL demo link": project.get("demo_link"),
                "BUIDL GitHub": project.get("github_page"),
                "Track": project.get("track_obj", {}).get("name", ""),
                "Bounties": ", ".join(b.get("title", "") for b in (project.get("bounty") or [])),
                "Team members": ", ".join(
                    member.get("username", "")
                    for m in members
                    if (member := m.get("member")) and member.get("username")
                ),
                "Team description": clean_text(project.get("project_description")),
                "Which HUB are you competing with?": clean_text(project.get("hub", {}).get("name", "Global Participant")),
                "Team Details": clean_text(project.get("team_description")),
                "Review status": project.get("review_status", ""),
                "Org": project_org
            }

            rows.append(row)
        except Exception as e:
            print(f"⚠️ Skipping invalid project record: {e}")
        print(f"🔄 Processed {idx}/{len(projects)} projects", end="\r")

    print("\n✅ All projects merged successfully.\n")
    return sorted(rows, key=lambda r: r["BUIDL last updated time (UTC)"], reverse=True)


# --- Main ---
def main():
    print("🚀 DoraHacks Scraper Started")

    print("\n📂 Step 1: Load & fetch user (hacker) data...")
    hackers = fetch_paginated_data(HACKERS_API, "Hackers", "user.json", "id")

    print("\n📂 Step 2: Load & fetch project (build) data...")
    projects = fetch_paginated_data(PROJECTS_API, "Projects", "build.json", "id")

    print("\n🔗 Step 3: Merge hacker + project data and enrich with org info...")
    hacker_org_map = build_hacker_username_to_org_map(hackers)
    final_data = merge_data(projects, hacker_org_map)

    print("\n📊 Step 4: Exporting to Excel...")
    try:
        df = pd.DataFrame(final_data)
        df.to_excel(EXCEL_FILE, index=False)
        print(f"\n✅ Done! Excel saved to: {EXCEL_FILE}\n")
    except Exception as e:
        print(f"❌ Failed to export Excel: {e}")

    # ✅ NEW Step 5
    try:
        save_json(final_data, "merged.json")
        print(f"✅ JSON saved to: {os.path.join(DATA_DIR, 'merged.json')}")
    except Exception as e:
        print(f"❌ Failed to save merged.json: {e}")

if __name__ == "__main__":
    main()
