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

    # 📛 Find the e-bulletin heading to cut off everything that follows
    cutoff_heading = soup.find("h3", string=re.compile(r"e-bulletin updates", re.I))

    # ✂️ Select cards only BEFORE the e-bulletin section
    articles = []
    for card in soup.select("li.gcweb-card"):
        if cutoff_heading and card.sourceline and cutoff_heading.sourceline and card.sourceline > cutoff_heading.sourceline:
            continue
        articles.append(card)

    fg = FeedGenerator()
    fg.id(url)
    fg.title("UKGC News")
    fg.link(href=url, rel="alternate")
    fg.description("Latest updates and announcements from the UK Gambling Commission")
    fg.language("en")

    for item in articles:
        anchor = item.select_one("a.text.text-top")
        if not anchor:
            continue

        href = anchor.get("href", "")
        full_link = "https://www.gamblingcommission.gov.uk" + href

        # 🎯 Final title selector (confirmed)
        title_elem = anchor.select_one("p.gc-card__description.gcweb-heading-m")
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"

        p_tags = anchor.select("p")
        date_text = p_tags[-1].get_text(strip=True) if p_tags else None

        try:
            dt = datetime.strptime(date_text, "%d %B %Y")
            pub_date = datetime(dt.year, dt.month, dt.day, 23, 59, 0, tzinfo=timezone.utc)
        except Exception as e:
            print(f"⚠️ Date parse failed for '{title}': {e}")
            pub_date = datetime.now(timezone.utc)

        guid = hashlib.md5((title + full_link).encode("utf-8")).hexdigest()

        entry = fg.add_entry()
        entry.id(guid)
        entry.guid(guid, permalink=False)
        entry.title(title)
        entry.link(href=full_link)
        entry.pubDate(pub_date)
        entry.updated(pub_date)

        print(f"✅ {title} — {pub_date.date()}")

    fg.rss_file(filename)
    print(f"📄 Feed saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
