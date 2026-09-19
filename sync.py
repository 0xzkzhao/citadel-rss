import os
import re
import time
from curl_cffi import requests
from bs4 import BeautifulSoup

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
            except Exception as e:
                pass
            time.sleep(1)
    return None

def extract_article_content(html):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find(class_="js-single-post-body")
    if not body:
        body = soup.find("article") or soup.find("main")
    if not body:
        return ""
    
    # Clean non-content elements
    for tag in body(["script", "style", "nav", "form", "iframe", "button"]):
        tag.decompose()
        
    return str(body)

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
        print(f"[{i+1}/{len(items)}] Fetching full article: {title}")
        
        art_html = fetch_with_retry(article_url)
        if art_html:
            clean_content = extract_article_content(art_html)
            if clean_content:
                # Update content:encoded
                content_tag = item.find("content:encoded")
                if not content_tag:
                    content_tag = soup.new_tag("content:encoded")
                    item.append(content_tag)
                content_tag.string = f"<![CDATA[{clean_content}]]>"
                
                # Update description with clean text excerpt
                desc_tag = item.find("description")
                plain_text = BeautifulSoup(clean_content, "html.parser").get_text(separator=" ", strip=True)
                summary = (plain_text[:350] + "...") if len(plain_text) > 350 else plain_text
                if desc_tag:
                    desc_tag.string = f"<![CDATA[{summary}]]>"
                print(f"  -> Extracted {len(clean_content)} chars.")
        time.sleep(1)

    result_xml = str(soup)
    result_xml = result_xml.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result_xml)
    print(f"Successfully generated {OUTPUT_FILE} ({len(result_xml)} bytes).")
    return True

if __name__ == "__main__":
    main()
