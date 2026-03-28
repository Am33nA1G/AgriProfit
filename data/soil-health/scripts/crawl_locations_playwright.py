import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL = "https://soilhealth.dac.gov.in/nutrient-dashboard"

# 🚨 WRITE EVERYTHING TO D: DRIVE
OUTPUT_DIR = Path(r"D:\soil-health-data\locations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WAIT = 1200  # ms between actions


# ----------------- FILE HELPERS -----------------

def safe_state_filename(state: str) -> Path:
    name = (
        state.upper()
        .replace("&", "AND")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "_")
    )
    return OUTPUT_DIR / f"{name}.json"


def save_state(state: str, data: dict):
    path = safe_state_filename(state)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------- MUI HELPERS -----------------

def try_open_listbox(page, input_id, retries=3):
    inp = page.locator(f'input#{input_id}')

    for _ in range(retries):
        try:
            inp.click(force=True)
            page.keyboard.press("ArrowDown")
            page.wait_for_selector('ul[role="listbox"]', timeout=5000)
            return page.locator('ul[role="listbox"] li[role="option"]')
        except PlaywrightTimeout:
            page.wait_for_timeout(1000)

    return None


def snapshot_options(page, input_id):
    options = try_open_listbox(page, input_id)
    if options is None:
        raise RuntimeError(f"{input_id} dropdown not ready")

    texts = options.evaluate_all(
        "els => els.map(e => e.textContent.trim())"
    )

    page.keyboard.press("Escape")
    return texts


def select_by_index(page, input_id, index):
    options = try_open_listbox(page, input_id)
    if options is None:
        raise RuntimeError(f"{input_id} dropdown not selectable")

    options.nth(index).click(force=True)
    page.wait_for_timeout(WAIT)


# ----------------- MAIN -----------------

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("Opening dashboard…")
        page.goto(URL, timeout=60000)
        page.wait_for_timeout(5000)

        print("Opening Filter…")
        page.get_by_role("button", name="Filter").click()
        page.wait_for_timeout(WAIT)

        # ========== STATES ==========
        states = snapshot_options(page, "State")
        print(f"Found {len(states)} states")

        for si, state in enumerate(states):
            out_file = safe_state_filename(state)
            if out_file.exists():
                print(f"\nSTATE → {state} (already saved, skipping)")
                continue

            print(f"\nSTATE → {state}")
            state_data = {}

            select_by_index(page, "State", si)

            try:
                districts = snapshot_options(page, "District")
            except:
                save_state(state, state_data)
                continue

            for di, district in enumerate(districts):
                print(f"  DISTRICT → {district}")
                state_data[district] = {}

                try:
                    select_by_index(page, "District", di)
                except:
                    print("    ⚠️ District not selectable, skipping")
                    continue

                try:
                    blocks = snapshot_options(page, "Block")
                except:
                    continue

                for bi, block in enumerate(blocks):
                    print(f"    BLOCK → {block}")
                    state_data[district][block] = []

                    try:
                        select_by_index(page, "Block", bi)
                    except:
                        print("      ⚠️ Block not selectable, skipping")
                        continue

            # ✅ SAVE AFTER EACH STATE
            save_state(state, state_data)
            print(f"✅ Saved {state}")

        browser.close()

    print("DONE ✅ All states processed safely")


# ----------------- SAFE EXIT -----------------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted — already saved states are safe.")
