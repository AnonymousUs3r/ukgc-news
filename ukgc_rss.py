import re
import hashlib
import asyncio
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from playwright.async_api import async_playwright

async def main():
    url = "https://www.gamblingcommission.gov.uk/news"
    filename = "ukgc_feed.xml"

    print("🚀 Scraping UKGC news page...")
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        content = await page.content()
        await browser.close()

    print("🔍 Parsing HTML...")
    soup = BeautifulSoup(content, "html.parser")
    articles = soup.select("ul.gc-news-list > li")

    fg = FeedGenerator()
    fg.id(url)
    fg.title("UKGC News")
    fg.link(href=url, rel="alternate")
    fg.description("Latest updates and announcements from the UK Gambling Commission")
    fg.language("en")

    for item in articles:
        a_tag = item.select_one("a")
        time_tag = item.select_one("time")

        if not a_tag or not time_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag["href"]
        full_link = "https://www.gamblingcommission.gov.uk" + href if href.startswith("/") else href

        raw_date = time_tag.get("datetime", "")
        try:
            pub_dt = datetime.fromisoformat(raw_date).replace(tzinfo=timezone.utc)
            pub_dt = pub_dt.replace(hour=23, minute=59, second=0)
        except Exception as e:
            print(f"⚠️ Date parse failed: {raw_date} ({e})")
            pub_dt = datetime.now(timezone.utc)

        # Stable GUID from title + link
        guid_source = f"{title}{full_link}"
        guid_hash = hashlib.md5(guid_source.encode("utf-8")).hexdigest()

        entry = fg.add_entry()
        entry.id(guid_hash)
        entry.guid(guid_hash, permalink=False)
        entry.title(title)
        entry.link(href=full_link)
        entry.pubDate(pub_dt)
        entry.updated(pub_dt)

        print(f"✅ Added: {title} – {pub_dt.isoformat()}")

    fg.rss_file(filename)
    print(f"📄 Feed saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
