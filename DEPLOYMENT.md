# Production Deployment Guide

## Static File Issues in Production

If static files (images, CSS, JS) are not loading in production but work in development, follow these steps:

### 1. Environment Variables

Set the following environment variables in production:

```bash
export FLASK_ENV=production
export FLASK_DEBUG=False
```

### 2. Using Gunicorn (Recommended)

Install gunicorn:
```bash
pip install gunicorn
```

Run the application:
```bash
gunicorn --bind 0.0.0.0:8000 wsgi:application
```

### 3. Using Flask Development Server (Not Recommended for Production)

```bash
export FLASK_ENV=production
python app.py
```

### 4. Debug Static File Issues

Visit these URLs to debug static file serving:

- `/debug/static-test` - Shows static file configuration
- `/debug/static/images/blog/electric_bike_alps_man_riding.jpg` - Direct file access

### 5. Common Issues and Solutions

#### Issue: Static files return 404
**Solution**: Ensure the static folder path is correct:
```python
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
```

#### Issue: Images not loading in CSS
**Solution**: Use absolute paths in CSS:
```css
background: url('/static/images/blog/electric_bike_alps_man_riding.jpg') center/cover;
```

#### Issue: File permissions
**Solution**: Ensure proper file permissions:
```bash
chmod -R 755 static/
chmod 644 static/images/blog/*.jpg
```

### 6. Nginx Configuration (If using Nginx)

Add this to your nginx configuration:

```nginx
location /static/ {
    alias /path/to/your/project/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 7. Apache Configuration (If using Apache)

Add this to your Apache configuration:

```apache
Alias /static/ /path/to/your/project/static/
<Directory /path/to/your/project/static/>
    Require all granted
</Directory>
```

### 8. Testing

After deployment, test these URLs:
- `https://yourdomain.com/static/images/blog/electric_bike_alps_man_riding.jpg`
- `https://yourdomain.com/debug/static-test`

## File Structure Verification

Ensure your production server has this structure:
```
your_project/
├── static/
│   ├── images/
│   │   └── blog/
│   │       └── electric_bike_alps_man_riding.jpg
│   ├── styles/
│   └── js/
├── templates/
├── app/
├── wsgi.py
└── app.py
```
