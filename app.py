from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import random
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Download NLTK data if needed
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    reviews = db.Column(db.Text, nullable=False)  # JSON list of reviews
    ingredients = db.Column(db.Text, nullable=False)  # JSON list
    eco_score = db.Column(db.Float, nullable=False)  # 0-100
    safety_score = db.Column(db.Float, nullable=False)  # 0-100

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'rating': self.rating,
            'reviews': json.loads(self.reviews),
            'ingredients': json.loads(self.ingredients),
            'eco_score': self.eco_score,
            'safety_score': self.safety_score
        }

# Mock data for demonstration
def generate_mock_products(query):
    products = []
    for i in range(10):
        reviews = [f"Review {j}: This product is {'great' if random.random() > 0.5 else 'okay'}." for j in range(5)]
        ingredients = ["Water", "Soap", "Fragrance", "Preservatives"]
        product = Product(
            name=f"{query} Product {i+1}",
            price=random.uniform(100, 2000),
            rating=random.uniform(3, 5),
            reviews=json.dumps(reviews),
            ingredients=json.dumps(ingredients),
            eco_score=random.uniform(50, 100),
            safety_score=random.uniform(60, 100)
        )
        products.append(product)
    return products

def calculate_unified_score(product, weights=None):
    if weights is None:
        weights = {'cost': 0.2, 'quality': 0.3, 'safety': 0.2, 'eco': 0.3}
    
    # Cost-efficiency: lower price is better, normalize
    cost_score = max(0, 100 - (product.price / 2000) * 100)
    
    # Quality: rating * sentiment
    sentiment = sia.polarity_scores(' '.join(json.loads(product.reviews)))['compound']
    quality_score = (product.rating / 5) * 50 + (sentiment + 1) * 25
    
    safety_score = product.safety_score
    eco_score = product.eco_score
    
    unified = (weights['cost'] * cost_score + 
               weights['quality'] * quality_score + 
               weights['safety'] * safety_score + 
               weights['eco'] * eco_score)
    return unified

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    if not query:
        return render_template('index.html', error="Please enter a product name.")
    
    # In real app, fetch from APIs, here mock
    products = generate_mock_products(query)
    
    # Calculate scores
    for p in products:
        p.unified_score = calculate_unified_score(p)
    
    # Sort by unified score descending
    products.sort(key=lambda x: x.unified_score, reverse=True)
    
    return render_template('results.html', products=products, query=query)

@app.route('/compare', methods=['POST'])
def compare():
    ids = request.form.getlist('product_ids')
    if len(ids) < 2:
        return jsonify({'error': 'Select at least 2 products'})
    
    products = Product.query.filter(Product.id.in_(ids)).all()
    for p in products:
        p.unified_score = calculate_unified_score(p)
    
    return render_template('compare.html', products=products)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()