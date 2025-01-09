# TripAdvisor Review Scraper

A Python web application that scrapes TripAdvisor reviews and provides basic analytics.

## Features

- Scrape reviews from any TripAdvisor URL
- Extract reviewer name, date, rating, title, content, and helpful votes
- Automatic pagination to collect multiple pages of reviews
- Basic analytics including average rating and rating distribution
- Clean and responsive web interface

## Setup

1. Activate the virtual environment:
   ```
   .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Open your browser and navigate to `http://localhost:5000`

## Credentials Setup

1. Copy `credentials.json.example` to `credentials.json`:
   ```bash
   cp credentials.json.example credentials.json
   ```

2. Update `credentials.json` with your Google Cloud Service Account credentials:
   - Go to Google Cloud Console
   - Create a new Service Account or use an existing one
   - Generate new JSON key
   - Copy the contents to your `credentials.json`

**Important**: Never commit `credentials.json` to version control. It's already added to `.gitignore`.

## Usage

1. Copy a TripAdvisor URL for a hotel, restaurant, or attraction
2. Paste the URL into the input field
3. Click "Scrape Reviews"
4. Wait for the results to load
5. View the reviews and analytics

## Note

Please be mindful of TripAdvisor's terms of service and implement appropriate delays between requests to avoid being blocked.
"# tripadvisor" 
"# ta"
