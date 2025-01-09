from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import requests
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt
import io
import base64
import re
import time
import random

app = Flask(__name__)

class TripAdvisorScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }
        self.session.headers.update(self.headers)

    def get_soup(self, url):
        try:
            print(f"Fetching URL: {url}")
            
            # Add a random delay between 2-4 seconds
            time.sleep(random.uniform(2, 4))
            
            # First, try to get the page normally
            response = self.session.get(url, timeout=10)
            
            # If we get a 403 or garbled content, try with additional headers
            if response.status_code == 403 or not response.content.decode('utf-8', 'ignore').strip().startswith('<'):
                print("Initial request failed or returned garbled content. Trying with additional headers...")
                
                # Update headers with referer and additional browser-like headers
                additional_headers = {
                    'Referer': 'https://www.tripadvisor.com/',
                    'Origin': 'https://www.tripadvisor.com',
                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"'
                }
                self.session.headers.update(additional_headers)
                
                # Add a longer delay before retry
                time.sleep(random.uniform(3, 5))
                
                # Try the request again
                response = self.session.get(url, timeout=10)
            
            response.raise_for_status()
            
            # Try to decode content properly
            try:
                content = response.content.decode('utf-8')
            except UnicodeDecodeError:
                print("UTF-8 decode failed, trying with ignore option")
                content = response.content.decode('utf-8', 'ignore')
            
            # Verify we got HTML content
            if not content.strip().startswith('<'):
                print("Warning: Response doesn't look like HTML")
                print("Response preview:", content[:200])
                raise Exception("Invalid HTML content received")
            
            print("Content type:", response.headers.get('Content-Type', 'unknown'))
            print("Content length:", len(content))
            
            # Create soup with lxml parser
            soup = BeautifulSoup(content, 'lxml')
            
            # Verify we can find basic HTML structure
            if not soup.find('body'):
                print("Warning: No <body> tag found in HTML")
                raise Exception("Invalid HTML structure")
            
            return soup
            
        except requests.RequestException as e:
            print(f"Error fetching URL: {str(e)}")
            raise Exception(f"Failed to fetch URL: {str(e)}")

    def scrape_reviews(self, url):
        print("Scraping reviews from:", url)
        soup = self.get_soup(url)
        if not soup:
            return []

        # First try to get reviews from HTML content
        reviews = self._extract_reviews_from_html(soup)
        
        if not reviews:
            # Fallback to JSON-LD data
            reviews = self._extract_reviews_from_jsonld(soup)
        
        return reviews

    def _extract_reviews_from_jsonld(self, soup):
        reviews = []
        json_ld = soup.find('script', {'type': 'application/ld+json'})
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if 'review' in data:
                    for review in data['review']:
                        print(f"Extracted review from JSON-LD: {review['reviewBody'][:50]}...")
                        reviews.append({
                            'reviewer_name': review['author']['name'],
                            'date': review['datePublished'],
                            'title': review['name'],
                            'content': review['reviewBody'],
                            'rating': 5.0,  # Default rating
                            'helpful_votes': '0',
                            'profile_pic': None,
                            'review_images': [],
                            'review_url': None
                        })
            except Exception as e:
                print(f"Error parsing JSON-LD: {str(e)}")
        return reviews

    def _get_high_res_image(self, url):
        """Convert image URL to high resolution version"""
        if not url:
            return url
        # Replace width parameter with 1200px for high resolution
        url = re.sub(r'w=\d+', 'w=1200', url)
        # Remove height constraint for maintaining aspect ratio
        url = re.sub(r'h=[-\d]+', 'h=-1', url)
        return url

    def _extract_reviews_from_html(self, soup):
        reviews = []
        
        # Find all review cards with exact class and data-automation
        review_cards = soup.find_all('div', {'class': '_c', 'data-automation': 'reviewCard'})
        print(f"\nFound {len(review_cards)} review cards from HTML")
        
        for idx, card in enumerate(review_cards, 1):
            try:
                print(f"\n--- Processing Review #{idx} ---")
                
                # Extract profile picture
                profile_pic = None
                profile_div = card.select_one('div.FGwzt.PaRlG picture img')
                if profile_div and profile_div.get('src'):
                    profile_pic = self._get_high_res_image(profile_div['src'])
                    print(f"Found profile pic: {profile_pic}")

                # Extract review images
                review_images = []
                image_divs = card.find_all('div', class_='ajoIU')
                for img_div in image_divs:
                    img = img_div.select_one('picture img')
                    if img:
                        if img.get('srcset'):
                            # Get highest resolution image from srcset
                            srcsets = img['srcset'].split(',')
                            highest_res = srcsets[-1].split(' ')[0] if len(srcsets) > 1 else srcsets[0].split(' ')[0]
                            if highest_res and not highest_res.endswith('default-avatar'):
                                high_res_url = self._get_high_res_image(highest_res)
                                review_images.append(high_res_url)
                                print(f"Added high-res image: {high_res_url}")
                        elif img.get('src'):
                            src = img['src']
                            if src and not src.endswith('default-avatar'):
                                high_res_url = self._get_high_res_image(src)
                                review_images.append(high_res_url)
                                print(f"Added high-res image: {high_res_url}")

                # Extract review URL
                review_url = None
                url_elem = card.find('a', {'href': lambda x: x and 'ShowUserReviews' in str(x)})
                if url_elem and url_elem.get('href'):
                    review_url = 'https://www.tripadvisor.com' + url_elem['href']
                    print(f"Found review URL: {review_url}")

                # Extract other review data
                reviewer_name = card.select_one('a.BMQDV._F.Gv.wSSLS.SwZTJ.FGwzt.ukgoS')
                reviewer_name = reviewer_name.text.strip() if reviewer_name else 'Anonymous'

                title = card.find('span', class_='yCeTE')
                title = title.text.strip() if title else ''

                content = card.find('span', class_='JguWG')
                content = content.text.strip() if content else ''

                date = card.select_one('div.TreSq div.biGQs._P.pZUbB.ncFvv.osNWb')
                date = date.text.strip() if date else ''

                helpful_votes = card.find('span', class_='kLqdM')
                helpful_votes = helpful_votes.text.strip() if helpful_votes else '0'

                review = {
                    'profile_pic': profile_pic,
                    'reviewer_name': reviewer_name,
                    'rating': 5.0,  # Default rating
                    'title': title,
                    'content': content,
                    'date': date,
                    'helpful_votes': helpful_votes,
                    'review_images': review_images,
                    'review_url': review_url
                }
                
                print(f"\nExtracted review data:")
                print(f"Profile pic: {profile_pic}")
                print(f"Review images: {review_images}")
                print(f"Review URL: {review_url}")
                
                reviews.append(review)

            except Exception as e:
                print(f"Error extracting review: {str(e)}")
                continue

        return reviews

    def extract_reviews(self, url, num_pages=5):
        reviews = []
        try:
            reviews = self.scrape_reviews(url)
            
            return reviews
            
        except Exception as e:
            print(f"Error extracting reviews: {str(e)}")
            return []

def generate_analytics(reviews):
    if not reviews:
        return {
            'average_rating': 0,
            'total_reviews': 0,
            'plot': None
        }
    
    df = pd.DataFrame(reviews)
    
    # Calculate average rating
    avg_rating = df['rating'].mean()
    
    # Create rating distribution plot
    plt.figure(figsize=(10, 6))
    df['rating'].value_counts().sort_index().plot(kind='bar')
    plt.title('Rating Distribution')
    plt.xlabel('Rating')
    plt.ylabel('Count')
    
    # Save plot to base64 string
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    analytics = {
        'average_rating': round(avg_rating, 2),
        'total_reviews': len(reviews),
        'plot': plot_url
    }
    
    return analytics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url') if data else None
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        scraper = TripAdvisorScraper()
        reviews = scraper.extract_reviews(url)
        
        if not reviews:
            return jsonify({
                'reviews': [],
                'analytics': {
                    'average_rating': 0,
                    'total_reviews': 0,
                    'plot': None
                },
                'message': 'No reviews found. This could be due to anti-scraping protection or an invalid URL.'
            })
        
        analytics = generate_analytics(reviews)
        
        return jsonify({
            'reviews': reviews,
            'analytics': analytics
        })
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        return jsonify({
            'error': str(e),
            'reviews': [],
            'analytics': {
                'average_rating': 0,
                'total_reviews': 0,
                'plot': None
            }
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
