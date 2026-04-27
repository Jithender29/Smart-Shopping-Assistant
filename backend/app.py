from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import random
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import functools
from urllib.parse import quote_plus

USD_TO_INR = 83.0

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here_change_in_production'
db = SQLAlchemy(app)

# Download NLTK data if needed
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    favorites = db.Column(db.Text, default='[]')  # JSON list
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    reviews = db.Column(db.Text, nullable=False)  # JSON list of reviews
    ingredients = db.Column(db.Text, nullable=False)  # JSON list
    eco_score = db.Column(db.Float, nullable=False)  # 0-100
    safety_score = db.Column(db.Float, nullable=False)  # 0-100
    category = db.Column(db.String(50), default='General')
    description = db.Column(db.Text, default='')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'rating': self.rating,
            'reviews': json.loads(self.reviews),
            'ingredients': json.loads(self.ingredients),
            'eco_score': self.eco_score,
            'safety_score': self.safety_score,
            'category': self.category,
            'description': self.description
        }

def generate_random_reviews():
    """Generate diverse, realistic product reviews"""
    positive_reviews = [
        "Excellent quality! Really impressed with the durability and performance. Highly recommend!",
        "Amazing product! Exceeded my expectations. The quality is outstanding and worth every penny.",
        "Love it! Fantastic value for money. Great customer service too!",
        "Perfect! Exactly what I needed. Works as described and arrived quickly.",
        "Outstanding! Best purchase I've made this year. Super satisfied.",
        "Great product! Very reliable and well-made. Good bang for the buck.",
        "Impressive! The quality is better than I expected for the price.",
        "Fantastic! Highly functional and looks great. Definitely worth buying.",
        "Wonderful! Exactly as pictured. Fast shipping and great packaging.",
        "Excellent purchase! Works perfectly. Would buy again.",
        "Love the attention to detail! Premium quality at a reasonable price.",
        "Outstanding value! Better than competitors. Highly satisfied.",
        "Brilliant! Does exactly what it's supposed to. Very impressed.",
        "Perfect quality! Couldn't ask for better. Definitely recommending to friends.",
        "Amazing durability! Still works perfectly after months of daily use."
    ]
    
    neutral_reviews = [
        "Good product. Does what it's supposed to. Decent value.",
        "It's okay. Nothing special but works fine for the price.",
        "Decent quality. Some minor issues but overall satisfied.",
        "Fair product. Not bad, not amazing either.",
        "Acceptable. Gets the job done without any major complaints.",
        "Reasonable quality for the price. Could be better but it works.",
        "Alright product. Works as expected. Nothing exceptional.",
        "Fine purchase. average quality but functional.",
        "Decent enough. Has some flaws but mostly satisfied.",
        "Not bad. Could be improved in some areas but acceptable."
    ]
    
    negative_reviews = [
        "Disappointed. Quality not as advertised. Average at best.",
        "Below expectations. Has durability issues after short use.",
        "Not satisfied. Poor quality for the price. Waste of money.",
        "Regrettable purchase. Doesn't work as promised. Broken after week.",
        "Terrible quality. Stops working after a few uses.",
        "Poor value. Overpriced for the low quality provided.",
        "Defective product. Arrived damaged. Disappointing experience.",
        "Didn't meet expectations. Better options available elsewhere.",
        "Low quality. Expected much better. Dissatisfied with purchase.",
        "Problematic product. Had to return it. Waste of time."
    ]
    
    # Generate 5-8 reviews with realistic distribution
    num_reviews = random.randint(5, 8)
    reviews = []
    
    # Distribute reviews: 60% positive, 25% neutral, 15% negative
    num_positive = int(num_reviews * 0.6)
    num_neutral = int(num_reviews * 0.25)
    num_negative = num_reviews - num_positive - num_neutral
    
    reviews.extend(random.sample(positive_reviews, min(num_positive, len(positive_reviews))))
    reviews.extend(random.sample(neutral_reviews, min(num_neutral, len(neutral_reviews))))
    reviews.extend(random.sample(negative_reviews, min(num_negative, len(negative_reviews))))
    
    return reviews

def generate_realistic_product_name(query, category, index):
    brands = [
        'Natura', 'PureLeaf', 'UrbanGlow', 'EcoNest', 'AquaBloom',
        'VitalCraft', 'GlowMint', 'FreshRoot', 'EverCare', 'PrimeAura'
    ]
    descriptors = [
        'Advanced', 'Herbal', 'Deep Clean', 'Daily Care', 'Ultra Fresh',
        'Hydrating', 'Gentle', 'Premium', 'Active', 'Complete'
    ]

    default_by_category = {
        'Electronics': 'Smart Device',
        'Personal Care': 'Care Essentials',
        'Home & Garden': 'Home Utility',
        'Food & Beverage': 'Nutrition Pack',
        'Fashion': 'Lifestyle Wear',
    }

    normalized_query = ' '.join(query.replace('-', ' ').replace('/', ' ').split()).strip()
    base_name = normalized_query.title() if normalized_query else default_by_category.get(category, 'Product')

    brand = brands[index % len(brands)]
    descriptor = descriptors[index % len(descriptors)]
    return f"{brand} {descriptor} {base_name}"

# Mock data for demonstration
def generate_mock_products(query, product_ids=None, num_products=10):
    categories = ['Electronics', 'Personal Care', 'Home & Garden', 'Food & Beverage', 'Fashion']
    products = []
    
    for i in range(num_products):
        ingredients = ["Water", "Natural Extracts", "Preservatives", "Essential Oils", "Organic Components"]
        selected_category = random.choice(categories)
        product_name = generate_realistic_product_name(query, selected_category, i)
        
        # Generate realistic reviews
        reviews = generate_random_reviews()
        
        product = Product(
            id=product_ids[i] if product_ids and i < len(product_ids) else i+1,
            name=product_name,
            price=round(random.uniform(100, 2000), 2),
            rating=round(random.uniform(3, 5), 1),
            reviews=json.dumps(reviews),
            ingredients=json.dumps(random.sample(ingredients, k=random.randint(2, 5))),
            eco_score=round(random.uniform(50, 100), 1),
            safety_score=round(random.uniform(60, 100), 1),
            category=selected_category,
            description=f"High-quality {product_name} designed for optimal performance and sustainability. Best choice for conscious consumers."
        )
        products.append(product)
    return products

def get_product_field(product, field_name, default=None):
    if isinstance(product, dict):
        return product.get(field_name, default)
    return getattr(product, field_name, default)

def build_fallback_image_url(query, name='', category=''):
    raw_text = ' '.join(part for part in [query, name, category] if part).lower().strip()
    if not raw_text:
        raw_text = 'shopping product'

    stop_words = {
        'product', 'products', 'item', 'items', 'best', 'quality', 'new',
        'source', 'generated', 'data', 'general', 'and', 'for', 'with',
        'the', 'a', 'an'
    }

    cleaned_tokens = []
    for token in raw_text.replace('&', ' ').replace('-', ' ').replace('/', ' ').split():
        cleaned_token = ''.join(character for character in token if character.isalnum())
        if cleaned_token and cleaned_token not in stop_words:
            cleaned_tokens.append(cleaned_token)

    if not cleaned_tokens:
        cleaned_tokens = ['shopping']

    primary_terms = cleaned_tokens[:3]
    image_label = ' '.join(primary_terms).title()

    # DummyImage reliably returns an image and keeps it relevant by embedding the product terms.
    return f'https://dummyimage.com/640x640/e8f1ff/0f172a.png&text={quote_plus(image_label)}'

def build_search_variants(query):
    normalized_query = ' '.join(query.lower().replace('-', ' ').replace('/', ' ').split())
    if not normalized_query:
        return []

    variants = []
    seen = set()

    def add_variant(value):
        cleaned_value = ' '.join(value.split()).strip()
        if cleaned_value and cleaned_value not in seen:
            seen.add(cleaned_value)
            variants.append(cleaned_value)

    add_variant(normalized_query)

    tokens = [token for token in normalized_query.split() if len(token) > 1]
    if tokens:
        add_variant(' '.join(tokens))
        add_variant(tokens[0])
        add_variant(tokens[-1])

    if len(tokens) > 2:
        add_variant(' '.join(tokens[:-1]))
        add_variant(' '.join(tokens[1:]))

    if 'facewash' in normalized_query:
        add_variant(normalized_query.replace('facewash', 'face wash'))
        add_variant(normalized_query.replace('face wash', 'facewash'))
        add_variant('facial wash')
        add_variant('face cleanser')

    if 'shampoo' in normalized_query:
        add_variant(normalized_query.replace('shampoo', 'hair shampoo'))

    if 'cream' in normalized_query:
        add_variant(normalized_query.replace('cream', 'face cream'))

    return variants

def ensure_list(value, default=None):
    if default is None:
        default = []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
            if isinstance(parsed_value, list):
                return parsed_value
        except json.JSONDecodeError:
            pass
    return default

def serialize_product_for_session(product):
    return {
        'id': get_product_field(product, 'id'),
        'name': get_product_field(product, 'name', ''),
        'price': float(get_product_field(product, 'price', 0) or 0),
        'rating': float(get_product_field(product, 'rating', 0) or 0),
        'reviews': ensure_list(get_product_field(product, 'reviews', []), []),
        'ingredients': ensure_list(get_product_field(product, 'ingredients', []), []),
        'eco_score': float(get_product_field(product, 'eco_score', 0) or 0),
        'safety_score': float(get_product_field(product, 'safety_score', 0) or 0),
        'category': get_product_field(product, 'category', 'General'),
        'description': get_product_field(product, 'description', ''),
        'source': get_product_field(product, 'source', 'Generated Mock Data'),
        'source_url': get_product_field(product, 'source_url', ''),
        'image_url': get_product_field(product, 'image_url', ''),
        'unified_score': float(get_product_field(product, 'unified_score', 0) or 0),
    }

def normalize_external_product(raw_product, source_name, index):
    raw_id = raw_product.get('id', index + 1)
    try:
        raw_id = int(raw_id)
    except (TypeError, ValueError):
        raw_id = index + 1

    source_offsets = {
        'DummyJSON': 100000,
        'FakeStoreAPI': 200000,
    }
    product_id = source_offsets.get(source_name, 300000) + raw_id

    reviews = raw_product.get('reviews')
    if isinstance(reviews, list) and reviews:
        normalized_reviews = reviews
    elif isinstance(reviews, str) and reviews.strip():
        try:
            parsed_reviews = json.loads(reviews)
            normalized_reviews = parsed_reviews if isinstance(parsed_reviews, list) else generate_random_reviews()
        except json.JSONDecodeError:
            normalized_reviews = generate_random_reviews()
    else:
        normalized_reviews = generate_random_reviews()

    ingredients = raw_product.get('ingredients')
    if not isinstance(ingredients, list) or not ingredients:
        ingredients = random.sample(
            ['Water', 'Natural Extracts', 'Preservatives', 'Essential Oils', 'Organic Components'],
            k=random.randint(2, 5)
        )

    description = raw_product.get('description') or f'Product sourced from {source_name}. '
    brand = raw_product.get('brand') or source_name
    category = raw_product.get('category') or 'General'
    price_value = float(raw_product.get('price') or 0)

    if source_name in {'DummyJSON', 'FakeStoreAPI'}:
        price_value = round(price_value * USD_TO_INR, 2)

    image_url = raw_product.get('thumbnail') or raw_product.get('image')
    if isinstance(raw_product.get('images'), list) and raw_product['images']:
        image_url = image_url or raw_product['images'][0]
    if not image_url:
        image_url = build_fallback_image_url(
            raw_product.get('search_query', ''),
            raw_product.get('title') or raw_product.get('name') or brand,
            category,
        )

    return {
        'id': product_id,
        'name': raw_product.get('title') or raw_product.get('name') or f'{brand} Product',
        'price': price_value,
        'rating': round(float(raw_product.get('rating') or 0), 1),
        'reviews': normalized_reviews,
        'ingredients': ingredients,
        'eco_score': round(float(raw_product.get('eco_score') or random.uniform(50, 100)), 1),
        'safety_score': round(float(raw_product.get('safety_score') or random.uniform(60, 100)), 1),
        'category': category,
        'description': description,
        'source': source_name,
        'source_url': raw_product.get('source_url') or raw_product.get('product_url') or '',
        'image_url': image_url or '',
    }

def fetch_dummyjson_products(query, limit=6):
    normalized_products = []
    seen_ids = set()

    for search_query in build_search_variants(query):
        response = requests.get(
            'https://dummyjson.com/products/search',
            params={'q': search_query, 'limit': limit},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        products = payload.get('products', [])[:limit]

        for index, raw_product in enumerate(products):
            unique_id = raw_product.get('id')
            if unique_id in seen_ids:
                continue
            seen_ids.add(unique_id)
            normalized_product = normalize_external_product(
                {
                    'id': raw_product.get('id'),
                    'title': raw_product.get('title'),
                    'price': raw_product.get('price'),
                    'rating': raw_product.get('rating'),
                    'description': raw_product.get('description'),
                    'brand': raw_product.get('brand'),
                    'category': raw_product.get('category'),
                    'thumbnail': raw_product.get('thumbnail'),
                    'images': raw_product.get('images', []),
                    'source_url': f"https://dummyjson.com/products/{raw_product.get('id')}",
                },
                'DummyJSON',
                index,
            )
            normalized_products.append(normalized_product)

            if len(normalized_products) >= limit:
                return normalized_products

    return normalized_products

def fetch_fakestoreapi_products(query, limit=6):
    response = requests.get('https://fakestoreapi.com/products', timeout=8)
    response.raise_for_status()
    payload = response.json()
    search_variants = build_search_variants(query)

    matching_products = []
    for raw_product in payload:
        searchable_text = ' '.join([
            str(raw_product.get('title', '')),
            str(raw_product.get('description', '')),
            str(raw_product.get('category', '')),
        ]).lower()
        if search_variants and not any(variant in searchable_text for variant in search_variants):
            continue

        matching_products.append(normalize_external_product(
            {
                'id': raw_product.get('id'),
                'title': raw_product.get('title'),
                'price': raw_product.get('price'),
                'rating': raw_product.get('rating', {}).get('rate', 0),
                'description': raw_product.get('description'),
                'category': raw_product.get('category'),
                'image': raw_product.get('image'),
                'source_url': f"https://fakestoreapi.com/products/{raw_product.get('id')}",
            },
            'FakeStoreAPI',
            len(matching_products),
        ))

        if len(matching_products) >= limit:
            break

    return matching_products

def fetch_ecommerce_products(query, limit=10):
    all_products = []

    try:
        all_products.extend(fetch_dummyjson_products(query, limit=limit // 2 or 1))
    except requests.RequestException:
        pass

    try:
        all_products.extend(fetch_fakestoreapi_products(query, limit=limit // 2 or 1))
    except requests.RequestException:
        pass

    if not all_products:
        fallback_products = generate_mock_products(query, num_products=limit)
        for fallback_product in fallback_products:
            all_products.append({
                'id': fallback_product.id,
                'name': fallback_product.name,
                'price': fallback_product.price,
                'rating': fallback_product.rating,
                'reviews': json.loads(fallback_product.reviews),
                'ingredients': json.loads(fallback_product.ingredients),
                'eco_score': fallback_product.eco_score,
                'safety_score': fallback_product.safety_score,
                'category': fallback_product.category,
                'description': fallback_product.description,
                'source': 'Generated Mock Data',
                'source_url': '',
                'image_url': build_fallback_image_url(query, fallback_product.name, fallback_product.category),
            })

    unique_products = []
    seen_names = set()
    for product in all_products:
        product_name = get_product_field(product, 'name', '').strip().lower()
        if product_name in seen_names:
            continue
        seen_names.add(product_name)
        unique_products.append(product)

    return unique_products[:limit]

def calculate_unified_score(product, weights=None):
    if weights is None:
        weights = {'cost': 0.2, 'quality': 0.3, 'safety': 0.2, 'eco': 0.3}

    price = float(get_product_field(product, 'price', 0) or 0)
    rating = float(get_product_field(product, 'rating', 0) or 0)
    safety_score = float(get_product_field(product, 'safety_score', 0) or 0)
    eco_score = float(get_product_field(product, 'eco_score', 0) or 0)
    reviews = get_product_field(product, 'reviews', [])
    if isinstance(reviews, str):
        try:
            reviews = json.loads(reviews)
        except json.JSONDecodeError:
            reviews = []
    
    # Cost-efficiency: lower price is better, normalize
    cost_score = max(0, 100 - (price / 2000) * 100)
    
    # Quality: rating * sentiment
    sentiment = sia.polarity_scores(' '.join(reviews))['compound'] if reviews else 0
    quality_score = (rating / 5) * 50 + (sentiment + 1) * 25
    
    unified = (weights['cost'] * cost_score + 
               weights['quality'] * quality_score + 
               weights['safety'] * safety_score + 
               weights['eco'] * eco_score)
    return round(unified, 1)

def login_required(f):
    """Decorator to check if user is logged in"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            return render_template('register.html', error='All fields are required')
        
        if len(username) < 3:
            return render_template('register.html', error='Username must be at least 3 characters')
        
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login', success=True))
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error='Registration failed. Please try again.')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('login.html', error='Username and password required')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session.modified = True
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('index.html', user=session.get('username'))

@app.route('/api/favorites', methods=['GET', 'POST'])
def manage_favorites():
    if 'favorites' not in session:
        session['favorites'] = []
    
    if request.method == 'POST':
        product_id = request.json.get('product_id')
        if product_id not in session['favorites']:
            session['favorites'].append(product_id)
        session.modified = True
        return jsonify({'status': 'added', 'favorites': session['favorites']})
    
    return jsonify({'favorites': session['favorites']})

@app.route('/api/favorites/<int:product_id>', methods=['DELETE'])
def remove_favorite(product_id):
    if 'favorites' not in session:
        session['favorites'] = []
    
    if product_id in session['favorites']:
        session['favorites'].remove(product_id)
    session.modified = True
    return jsonify({'status': 'removed', 'favorites': session['favorites']})

@app.route('/api/search-history', methods=['GET', 'POST'])
def manage_search_history():
    if 'search_history' not in session:
        session['search_history'] = []
    
    if request.method == 'POST':
        query = request.json.get('query', '').strip()
        if query and query not in session['search_history']:
            session['search_history'].insert(0, query)
            # Keep only last 10 searches
            session['search_history'] = session['search_history'][:10]
        session.modified = True
        return jsonify({'search_history': session['search_history']})
    
    return jsonify({'search_history': session['search_history']})

@app.route('/api/budget-calculator', methods=['POST'])
def budget_calculator():
    """Calculate savings and suggest best value products"""
    data = request.json
    budget = data.get('budget', 0)
    
    if budget <= 0:
        return jsonify({'error': 'Invalid budget'})
    
    query = data.get('query', '')
    products = generate_mock_products(query)
    
    # Filter by budget and calculate savings
    affordable = []
    for p in products:
        if p.price <= budget:
            p.unified_score = calculate_unified_score(p)
            savings = budget - p.price
            affordable.append({
                'name': p.name,
                'price': p.price,
                'rating': p.rating,
                'savings': round(savings, 2),
                'unified_score': p.unified_score,
                'category': p.category
            })
    
    # Sort by unified score
    affordable.sort(key=lambda x: x['unified_score'], reverse=True)
    
    return jsonify({
        'budget': budget,
        'products_within_budget': len(affordable),
        'recommendations': affordable[:5],
        'average_price': round(sum(p['price'] for p in affordable) / len(affordable), 2) if affordable else 0
    })

@app.route('/api/sentiment-analysis/<int:product_id>', methods=['GET'])
def product_sentiment(product_id):
    """Analyze sentiment distribution of reviews"""
    products = generate_mock_products("analysis")
    if product_id > len(products):
        return jsonify({'error': 'Product not found'})
    
    product = products[product_id - 1]
    reviews = json.loads(product.reviews)
    
    positive = sum(1 for r in reviews if any(word in r.lower() for word in 
        ['excellent', 'amazing', 'great', 'outstanding', 'love', 'fantastic', 'brilliant', 'perfect', 'wonderful']))
    negative = sum(1 for r in reviews if any(word in r.lower() for word in 
        ['disappointed', 'poor', 'waste', 'terrible', 'broken', 'defective', 'problematic']))
    neutral = len(reviews) - positive - negative
    
    return jsonify({
        'total_reviews': len(reviews),
        'positive': positive,
        'neutral': neutral,
        'negative': negative,
        'positive_percent': round((positive / len(reviews)) * 100, 1),
        'neutral_percent': round((neutral / len(reviews)) * 100, 1),
        'negative_percent': round((negative / len(reviews)) * 100, 1)
    })

@app.route('/deals')
def deals():
    """Show best deals and discounted products"""
    # Generate products with price variations
    categories = ['Electronics', 'Personal Care', 'Home & Garden', 'Food & Beverage', 'Fashion']
    
    deals = []
    for i in range(15):
        original_price = round(random.uniform(500, 3000), 2)
        discount_percent = random.choice([10, 15, 20, 25, 30, 40, 50])
        discounted_price = round(original_price * (1 - discount_percent / 100), 2)
        
        deal = {
            'id': i + 1,
            'name': f'Deal Product {i+1}',
            'original_price': original_price,
            'discounted_price': discounted_price,
            'discount_percent': discount_percent,
            'savings': round(original_price - discounted_price, 2),
            'rating': round(random.uniform(3, 5), 1),
            'category': random.choice(categories),
            'eco_score': round(random.uniform(50, 100), 1),
            'stock': random.choice(['In Stock', 'Low Stock', 'Limited Time'])
        }
        deals.append(deal)
    
    # Sort by discount
    deals.sort(key=lambda x: x['discount_percent'], reverse=True)
    
    return render_template('deals.html', deals=deals)

@app.route('/recommendations/<product_name>')
def recommendations(product_name):
    """Get similar products and recommendations"""
    products = generate_mock_products(product_name)
    
    recommendations_list = []
    for p in products:
        p.unified_score = calculate_unified_score(p)
        recommendations_list.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'rating': p.rating,
            'similarity': round(random.uniform(75, 99), 1),
            'unified_score': p.unified_score,
            'eco_score': p.eco_score,
            'category': p.category
        })
    
    # Sort by similarity
    recommendations_list.sort(key=lambda x: x['similarity'], reverse=True)
    
    return render_template('recommendations.html', 
                         product_name=product_name,
                         recommendations=recommendations_list[:8])

@app.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == 'GET':
        query = request.args.get('query', '')
    else:
        query = request.form.get('query', '')
    
    if not query:
        return render_template('index.html', error="Please enter a product name.")
    
    # Get filter and sort parameters
    min_price = request.args.get('min_price', type=float, default=0)
    max_price = request.args.get('max_price', type=float, default=5000)
    min_rating = request.args.get('min_rating', type=float, default=0)
    min_eco = request.args.get('min_eco', type=float, default=0)
    sort_by = request.args.get('sort_by', 'unified')
    category = request.args.get('category', '')
    
    # Fetch products from external ecommerce APIs first, then fall back to mock data.
    products = fetch_ecommerce_products(query)
    
    # Calculate scores
    for p in products:
        if isinstance(p, dict):
            p['unified_score'] = calculate_unified_score(p)
        else:
            p.unified_score = calculate_unified_score(p)
    
    # Apply filters
    filtered_products = []
    for p in products:
        price = get_product_field(p, 'price', 0)
        rating = get_product_field(p, 'rating', 0)
        eco_score = get_product_field(p, 'eco_score', 0)
        product_category = get_product_field(p, 'category', '')

        if (min_price <= price <= max_price and 
            rating >= min_rating and 
            eco_score >= min_eco and
            (not category or product_category == category)):
            filtered_products.append(p)
    
    # Apply sorting
    if sort_by == 'price_low':
        filtered_products.sort(key=lambda x: get_product_field(x, 'price', 0))
    elif sort_by == 'price_high':
        filtered_products.sort(key=lambda x: get_product_field(x, 'price', 0), reverse=True)
    elif sort_by == 'rating':
        filtered_products.sort(key=lambda x: get_product_field(x, 'rating', 0), reverse=True)
    elif sort_by == 'eco':
        filtered_products.sort(key=lambda x: get_product_field(x, 'eco_score', 0), reverse=True)
    else:  # unified
        filtered_products.sort(key=lambda x: get_product_field(x, 'unified_score', 0), reverse=True)
    
    # Get unique categories for filter
    categories = sorted(list(set(get_product_field(p, 'category', 'General') for p in products)))

    session['last_search_products'] = [serialize_product_for_session(product) for product in filtered_products]
    session['last_search_query'] = query
    session.modified = True
    
    return render_template('results.html', 
                         products=filtered_products, 
                         query=query,
                         categories=categories,
                         filters={
                             'min_price': min_price,
                             'max_price': max_price,
                             'min_rating': min_rating,
                             'min_eco': min_eco,
                             'category': category,
                             'sort_by': sort_by
                         })

@app.route('/compare', methods=['POST'])
def compare():
    raw_ids = request.form.getlist('product_ids')
    try:
        ids = sorted({int(product_id) for product_id in raw_ids})
    except ValueError:
        ids = []

    if len(ids) < 2:
        return render_template('compare.html', products=[])

    stored_products = session.get('last_search_products', [])
    if stored_products:
        selected_products = [product for product in stored_products if product.get('id') in ids]
    else:
        selected_products = []

    if len(selected_products) < 2:
        query = request.form.get('query', 'Product')
        fallback_products = generate_mock_products(query, product_ids=ids, num_products=len(ids))
        selected_products = [serialize_product_for_session(product) for product in fallback_products]

    for product in selected_products:
        product['reviews'] = ensure_list(product.get('reviews', []))
        product['ingredients'] = ensure_list(product.get('ingredients', []))
        product['unified_score'] = calculate_unified_score(product)

    return render_template('compare.html', products=selected_products)

@app.route('/favorites')
def view_favorites():
    if 'favorites' not in session or not session['favorites']:
        return render_template('favorites.html', products=[], message="No favorites yet!")
    
    # Generate mock products for favorites
    all_products = generate_mock_products("favorite")
    products = [p for p in all_products if p.id in session['favorites']][:5]
    
    for p in products:
        p.unified_score = calculate_unified_score(p)
    
    return render_template('favorites.html', products=products, message="")

@app.route('/feature-upcoming-display')
def feature_upcoming_display():
    product_name = request.args.get('product', 'Selected Product')
    return render_template('feature_upcoming_display.html', product_name=product_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)