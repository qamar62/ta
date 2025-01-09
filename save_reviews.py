import json
import time
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from app import TripAdvisorScraper
from datetime import datetime

# Load environment variables
load_dotenv()

# Google Sheets Configuration
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
RANGE_NAME = os.getenv('RANGE_NAME')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def load_existing_reviews():
    try:
        with open('reviews.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_reviews_to_json(reviews):
    try:
        with open('reviews.json', 'w') as f:
            json.dump(reviews, f, indent=4)
    except Exception as e:
        print(f"Error saving reviews to JSON: {e}")

def save_to_google_sheets(reviews, is_update=False):
    try:
        # Set up Google Sheets credentials
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)

        # Prepare the data
        values = []
        for review in reviews:
            row = [
                review['reviewer_name'],
                review['date'],
                review['content'],
                review.get('profile_pic', ''),
                ','.join(review.get('review_images', [])),
                review.get('review_url', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            values.append(row)

        body = {
            'values': values
        }

        # Append the data to the sheet
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        print(f"{'Updated' if is_update else 'Added'} {len(values)} rows to Google Sheets")
        return True
    except Exception as e:
        print(f"Error saving to Google Sheets: {e}")
        return False

def has_new_reviews(old_reviews, new_reviews):
    def get_review_id(review):
        return (
            review['reviewer_name'],
            review['date'],
            review['content'],
            review.get('profile_pic', ''),
            ','.join(review.get('review_images', [])),
            review.get('review_url', '')
        )
    
    old_ids = {get_review_id(r): r for r in old_reviews}
    new_ids = {get_review_id(r): r for r in new_reviews}
    
    # Find reviews that are in new_ids but not in old_ids
    new_review_ids = set(new_ids.keys()) - set(old_ids.keys())
    new_reviews_to_add = [new_ids[review_id] for review_id in new_review_ids]
    
    return new_reviews_to_add

def monitor_and_save_reviews(url):
    scraper = TripAdvisorScraper()
    old_reviews = load_existing_reviews()
    
    # First, send all existing reviews to Google Sheets
    if old_reviews:
        print(f"Sending all {len(old_reviews)} existing reviews to Google Sheets...")
        if save_to_google_sheets(old_reviews):
            print("Successfully saved all existing reviews to Google Sheets")
        else:
            print("Failed to save existing reviews to Google Sheets")
    
    while True:
        try:
            print("Fetching reviews...")
            new_reviews = scraper.scrape_reviews(url)
            
            # Get only the new reviews that need to be added
            reviews_to_add = has_new_reviews(old_reviews, new_reviews)
            
            if reviews_to_add:
                print(f"Found {len(reviews_to_add)} new reviews!")
                # Save all reviews to JSON file
                save_reviews_to_json(new_reviews)
                
                # Save only new reviews to Google Sheets
                if save_to_google_sheets(reviews_to_add):
                    print("Successfully saved new reviews to Google Sheets")
                    old_reviews = new_reviews
                else:
                    print("Failed to save to Google Sheets")
            else:
                print("No new reviews found")
                
            # Wait for 5 minutes before checking again
            time.sleep(300)
            
        except Exception as e:
            print(f"Error in monitor_and_save_reviews: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == "__main__":
    url = "https://www.tripadvisor.com/AttractionProductReview-g295424-d12980677-Wow_Arabian_Nights_Tours_Desert_Safari_Program_with_BBQ_Dinner-Dubai_Emirate_of_Du.html"
    monitor_and_save_reviews(url)
