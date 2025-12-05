# EMTB Site - Smart Electric Mountain Bike Recommendations

A Flask-based web application for electric mountain bike recommendations, featuring AI-powered comparisons and comprehensive bike filtering.

## Features

- **Smart Bike Filtering**: Advanced filtering by price, battery capacity, motor brand, frame material, and more
- **AI-Powered Comparisons**: Intelligent bike comparisons using OpenAI API
- **Blog System**: Hebrew blog posts about eMTB topics
- **Responsive Design**: Modern, mobile-friendly interface with RTL support for Hebrew
- **Security**: CSRF protection, XSS prevention, and secure file handling

## Project Structure

```
emtb_site/
├── app/                    # Main application package
│   ├── __init__.py        # Application factory
│   ├── config.py          # Configuration settings
│   ├── extensions.py      # Flask extensions
│   ├── models/            # Database models
│   ├── routes/            # Route blueprints
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── templates/             # Jinja2 templates
├── static/               # Static files (CSS, JS, images)
├── data/                 # Data files and scrapers
├── scripts/              # Database and maintenance scripts
└── app.py                # Application entry point
```

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables** (create a `.env` file):
   ```
   FLASK_SECRET_KEY=your_secret_key
   OPENAI_API_KEY=your_openai_api_key
   EMAIL_USER=your_email
   EMAIL_PASS=your_email_password
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Visit the application**:
   - Home: http://localhost:5000
   - Bikes: http://localhost:5000/bikes
   - Blog: http://localhost:5000/blog

## Technology Stack

- **Backend**: Flask, SQLAlchemy, OpenAI API
- **Frontend**: Bootstrap 5, JavaScript, CSS3
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Security**: Flask-WTF (CSRF), Bleach (XSS prevention)
- **Caching**: Flask-Caching
