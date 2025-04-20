from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import threading

app = Flask(__name__)

# Configure Selenium options
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Thread-local storage for browser instances
thread_local = threading.local()

def get_thread_local_driver():
    if not hasattr(thread_local, "driver"):
        thread_local.driver = get_driver()
    return thread_local.driver

@app.route('/scrape-conferences', methods=['GET'])
def scrape_conferences():
    category = request.args.get('category', default='engineering-and-technology')
    place = request.args.get('place', default='alexandria')
    
    if not category or not place:
        return jsonify({"error": "Both category and place parameters are required"}), 400
    
    valid_categories = [
        "business-and-economics",
        "medical-and-health-science",
        "mathematics-and-statistics",
        "engineering-and-technology",
        "physical-and-life-sciences",
        "social-sciences-and-humanities",
        "education",
        "law"
    ]
    
    if category not in valid_categories:
        return jsonify({"error": "Invalid category"}), 400

    try:
        driver = get_thread_local_driver()
        url = f"https://allconferencealert.com/{category}/{place}.html"
        
        driver.get(url)
        time.sleep(3)  # Wait for page load
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        table = soup.find('table', class_='table')
        
        if not table:
            return jsonify({"error": "No conferences found for the specified criteria"}), 404
            
        rows = table.find_all("tr", class_="data1")
        data = []
        
        for row in rows:
            date = row.find("td").get_text(strip=True)
            title_td = row.find("td", style="text-align: left")
            title = title_td.get_text(strip=True)
            link = title_td.find("a")["href"]
            venue = row.find("td").find_next("td").find_next("td").get_text(strip=True)
            
            data.append({
                "date": date,
                "title": title,
                "venue": venue,
                "link": link,
                "category": category.replace("-", " ").title(),
                "location": place.title()
            })
        
        # Optionally save to CSV
        if request.args.get('save_csv', default=False):
            df = pd.DataFrame(data)
            filename = f"{category}_{place}_conferences.csv"
            df.to_csv(filename, index=False)
            return jsonify({
                "message": f"Scraped {len(data)} conferences",
                "data": data,
                "csv_file": filename
            })
        
        return jsonify({
            "count": len(data),
            "conferences": data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.teardown_appcontext
def shutdown_driver(exception=None):
    if hasattr(thread_local, "driver"):
        thread_local.driver.quit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)