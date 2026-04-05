# Smart Shopping Assistant

A web application tailored for the Indian market that provides unbiased product recommendations based on multiple criteria including cost-efficiency, quality, safety, customer satisfaction, and environmental sustainability. Prices are displayed in Indian Rupees (₹).

## Features

- Product search with intelligent scoring
- Multi-parameter evaluation (cost, quality, safety, eco-friendliness)
- Product comparison tool
- User-adjustable scoring weights
- Responsive web interface

## Installation

1. Install Python 3.8+
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python app.py`
4. Open http://localhost:5000 in your browser

Note: The app runs in development mode. For production, use a WSGI server like Gunicorn.

## Technologies Used

- Backend: Flask, SQLAlchemy
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- NLP: NLTK for sentiment analysis

## Project Structure

- `app.py`: Main Flask application
- `templates/`: HTML templates
- `static/`: CSS and static files
- `requirements.txt`: Python dependencies

## SRS Compliance

This project implements the requirements specified in the IEEE SRS template, including:
- Product search and data retrieval
- Unified scoring algorithm
- Alternative recommendations
- Side-by-side comparison
- Secure and scalable architecture