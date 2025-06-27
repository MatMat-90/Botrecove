import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

async def main():
    stealth = Stealth()
    async with stealth.use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        )
        # Add the cookie to the browser context
        cookie = {
            "name": "v_udt",
            "value": "WE40eExkOTRoNXArT1ZaNXlJeVVuWS9LNkVRSC0tMTRWakVpUzFjOHlnQWR5eC0tWjVhZ0lwNVpUellvWlFpdkNXcWYwdz09",
            "domain": ".vinted.fr",
            "path": "/"
        }
        await context.add_cookies([cookie])

        page = await context.new_page()

        # The URL we want to access
        url = "https://www.vinted.fr/api/v2/catalog/items?search_text=chaussures%20nike&per_page=5"

        try:
            await page.goto(url, wait_until="domcontentloaded")
            
            body_content = await page.locator("body").inner_text()
            print("--- Page Content ---")
            print(body_content)
            print("--------------------")

            data = json.loads(body_content)
            print("Successfully parsed JSON.")

            for item in data.get("items", []):
                print(f"Title: {item.get('title')}")
                print(f"Price: {item.get('price')} {item.get('currency')}")
                print(f"URL: {item.get('url')}")
                print(f"Available: {'Yes' if not item.get('is_reserved') else 'No'}")
                print("-" * 20)

        except Exception as e:
            print(f"An error occurred: {e}")
            # Save the page content for debugging
            full_content = await page.content()
            with open("error_page.html", "w", encoding="utf-8") as f:
                f.write(full_content)
            print("Full page content saved to error_page.html for debugging.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())