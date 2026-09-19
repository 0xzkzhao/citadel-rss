import os
import sys
import re
import time
from curl_cffi import requests
from bs4 import BeautifulSoup, CData

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

FEED_URL = "https://www.citadelsecurities.com/news-and-insights/category/market-insights/feed/"
OUTPUT_FILE = "feed.xml"

IMPERSONATES = ["safari17_2_ios", "safari15_5", "safari17_0"]

def fetch_with_retry(url, is_xml=False):
    for imp in IMPERSONATES:
        for attempt in range(2):
            try:
                r = requests.get(url, impersonate=imp, timeout=15)
                if r.status_code == 200:
                    if is_xml and ("<rss" in r.text or "<?xml" in r.text):
                        return r.text
                    elif not is_xml and len(r.text) > 1000:
                        return r.text
            except Exception:
                pass
            time.sleep(1)
    return None

def clean_citadel_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    body = soup.find(class_="js-single-post-body")
    if not body:
        body = soup.find("article") or soup.find("main")
    if not body:
        return "", ""
        
    # Remove unwanted / tracking / layout-breaking tags
    for tag in body(["script", "style", "nav", "form", "iframe", "button"]):
        tag.decompose()
        
    for span in body.find_all("span", class_="anchor"):
        span.decompose()

    # Extract clean text for summary
    plain_text = ' '.join(body.get_text(separator=' ', strip=True).split())
    summary = (plain_text[:280] + '...') if len(plain_text) > 280 else plain_text
    
    # Collect semantic elements
    elements = body.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "blockquote", "figure", "img", "table"])
    
    clean_soup = BeautifulSoup("<div class='citadel-article'></div>", "html.parser")
    container = clean_soup.div
    
    seen_elements = set()
    for el in elements:
        if any(parent in seen_elements for parent in el.parents):
            continue
        seen_elements.add(el)
        container.append(el)
        
    clean_html = str(container)
    return clean_html, summary

def main():
    print("Fetching Citadel Securities Market Insights Feed...")
    feed_xml = fetch_with_retry(FEED_URL, is_xml=True)
    if not feed_xml:
        print("Error: Failed to fetch feed XML.")
        return False

    soup = BeautifulSoup(feed_xml, "xml")
    items = soup.find_all("item")
    print(f"Found {len(items)} items in feed.")

    for i, item in enumerate(items):
        link_tag = item.find("link")
        if not link_tag or not link_tag.text:
            continue
        article_url = link_tag.text.strip()
        title_tag = item.find("title")
        title = title_tag.text.strip() if title_tag else article_url
        print(f"[{i+1}/{len(items)}] Processing: {title}")
        
        art_html = fetch_with_retry(article_url)
        if art_html:
            clean_html, summary = clean_citadel_html(art_html)
            if clean_html:
                # 1. Update content:encoded using CData
                content_tag = item.find("content:encoded")
                if not content_tag:
                    content_tag = soup.new_tag("content:encoded")
                    item.append(content_tag)
                content_tag.clear()
                content_tag.append(CData(clean_html))
                
                # 2. Update description with pure text summary
                desc_tag = item.find("description")
                if not desc_tag:
                    desc_tag = soup.new_tag("description")
                    item.append(desc_tag)
                desc_tag.clear()
                desc_tag.append(CData(summary))
                
                # 3. Update guid with version suffix to force Folo cache refresh
                guid_tag = item.find("guid")
                if guid_tag and guid_tag.text:
                    if not guid_tag.text.endswith("-v2"):
                        guid_tag.string = guid_tag.text + "-v2"
                        
                print(f"  -> Extracted {len(clean_html)} chars.")
        time.sleep(1)

    result_xml = str(soup)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result_xml)
    print(f"Successfully generated clean {OUTPUT_FILE} ({len(result_xml)} bytes).")
    return True

if __name__ == "__main__":
    main()
