from playwright.sync_api import sync_playwright
import time

def scrape_strategies():
    strategies = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for page_idx in range(1, 240):
            url = f"https://www.fmz.com/square/lang:5/{page_idx}"
            page.goto(url)
            
            try:
                # Wait for elements to load
                page.wait_for_selector(".ant-table-row", timeout=5000)  # Added timeout to avoid infinite wait
                
                # Extract strategy content
                strategy_elements = page.query_selector_all(".ant-table-row")
                
                if not strategy_elements:
                    print(f"No strategies found on page {page_idx}, stopping.")
                    break
                
                for strategy in strategy_elements:
                    row_key = strategy.get_attribute("data-row-key") or "No Row Key"
                    title_element = strategy.query_selector(".sc-dcJsrY")
                    title = title_element.inner_text().strip() if title_element else "No Title"
                    
                    strategies.append({"row_key": row_key, "title": title})
                    print(f"Page {page_idx}: {title} ({row_key})")
            except Exception as e:
                print(f"Error on page {page_idx}: {e}")
                break
        
        browser.close()
    
    return strategies

if __name__ == "__main__":
    strategies = scrape_strategies()
    for strat in strategies:
        print(f"Row Key: {strat['row_key']}")
        print(f"Title: {strat['title']}")
        print("-" * 50)
