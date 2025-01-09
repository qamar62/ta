import json
import time
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

def load_reviews():
    try:
        with open('reviews.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.route('/')
def display_reviews():
    reviews = load_reviews()
    return render_template('reviews.html', reviews=reviews)

if __name__ == '__main__':
    app.run(port=5001)  # Running on different port than main app
