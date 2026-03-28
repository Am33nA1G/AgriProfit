import csv
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError

# ================= CONFIG =================

URL = "https://soilhealth.dac.gov.in/nutrient-dashboard"

OUT_DIR = Path(r"D:\soil-health-data\nutrients")
OUT_DIR.mkdir(parents=True, exist_ok=True)

WAIT_SHORT = 1200
WAIT_LONG = 3500

# ================= UTILITIES =================

def safe_filename(text: str) -> str:
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def existing_blocks():
    """
    Resume support: read already-saved CSVs
    """
    done = set()
    for f in OUT_DIR.glob("*.csv"):
        parts = f.stem.rsplit("_", 3)
        if len(parts) == 4:
            state, district, block, cycle = parts
            done.add((cycle, state, district, block))
    return done


# ================= MUI HELPERS =================

def combobox_by_label(page, label_text):
    label = page.locator("label", has_text=label_text)
    if label.count() == 0:
        raise RuntimeError(f"Label not found: {label_text}")

    input_id = label.first.get_attribute("for")
    return page.locator(f"input#{input_id}")


def open_listbox(page, label_text):
    cb = combobox_by_label(page, label_text)
    cb.click(force=True)
    page.keyboard.press("ArrowDown")
    page.wait_for_selector("ul[role='listbox']", timeout=8000)
    return page.locator("ul[role='listbox'] li[role='option']")


def snapshot_options(page, label_text, retries=3):
    for _ in range(retries):
        try:
            opts = open_listbox(page, label_text)
            values = opts.evaluate_all(
                "els => els.map(e => e.textContent.trim())"
            )
            page.keyboard.press("Escape")
            return values
        except TimeoutError:
            page.wait_for_timeout(1500)

    print(f"⚠️ Dropdown not ready: {label_text}, skipping")
    return []


def select_option(page, label_text, value):
    try:
        opts = open_listbox(page, label_text)
    except TimeoutError:
        return False

    for i in range(opts.count()):
        if opts.nth(i).inner_text().strip() == value:
            opts.nth(i).click(force=True)
            page.wait_for_timeout(WAIT_SHORT)
            return True
    return False


# ================= DATA EXTRACTION =================

def scrape_cards(page):
    page.wait_for_timeout(WAIT_LONG)
    cards = page.locator(".MuiCard-root")
    rows = []

    for i in range(cards.count()):
        c = cards.nth(i)
        try:
            nutrient = c.locator("h6").inner_text().strip()
            nums = c.locator("span").all_inner_texts()
            if len(nums) >= 3:
                rows.append((nutrient, nums[0], nums[1], nums[2]))
        except:
            pass

    return rows


# ================= CYCLE RESET =================

def reset_for_cycle(page):
    page.goto(URL, timeout=60000)
    page.wait_for_timeout(5000)


# ================= MAIN =================

def main():
    completed = existing_blocks()
    print(f"Resuming — {len(completed)} blocks already saved")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        reset_for_cycle(page)
        print("Opening dashboard…")

        cycles = snapshot_options(page, "Select Cycle")[:3]
        print("Cycles →", cycles)

        for cycle in cycles:
            print(f"\nCYCLE → {cycle}")

            # 🔁 HARD RESET PER CYCLE
            reset_for_cycle(page)

            if not select_option(page, "Select Cycle", cycle):
                print(f"⚠️ Could not select cycle {cycle}, skipping")
                continue

            page.get_by_role("button", name="Filter").click()
            page.wait_for_timeout(WAIT_SHORT)

            states = snapshot_options(page, "Select State")
            for state in states:
                print(f"  STATE → {state}")

                if not select_option(page, "Select State", state):
                    continue

                districts = snapshot_options(page, "Select District")
                for district in districts:

                    if not select_option(page, "Select District", district):
                        print(f"    ⚠️ District disappeared, skipping: {district}")
                        continue

                    blocks = snapshot_options(page, "Select Block")
                    if not blocks:
                        continue

                    for block in blocks:
                        key = (
                            cycle,
                            safe_filename(state),
                            safe_filename(district),
                            safe_filename(block),
                        )

                        if key in completed:
                            continue

                        print(f"    BLOCK → {block}")

                        if not select_option(page, "Select Block", block):
                            continue

                        rows = scrape_cards(page)
                        if not rows:
                            continue

                        fname = (
                            f"{safe_filename(state)}_"
                            f"{safe_filename(district)}_"
                            f"{safe_filename(block)}_"
                            f"{cycle}.csv"
                        )

                        out = OUT_DIR / fname
                        with open(out, "w", newline="", encoding="utf-8") as f:
                            w = csv.writer(f)
                            w.writerow([
                                "cycle",
                                "state",
                                "district",
                                "block",
                                "nutrient",
                                "high",
                                "medium",
                                "low",
                            ])
                            for r in rows:
                                w.writerow([cycle, state, district, block, *r])

                        completed.add(key)
                        print(f"      Saved → {out.name}")

        browser.close()
        print("\nDONE ✅ Nutrient crawl complete")


if __name__ == "__main__":
    main()
