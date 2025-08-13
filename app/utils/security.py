import bleach

def sanitize_html_content(content):
    """
    Sanitize HTML content to prevent XSS attacks while allowing safe HTML tags.
    Only allows specific HTML tags and attributes that are safe for blog content.
    """
    # Define allowed HTML tags and attributes
    allowed_tags = [
        'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'strong', 'b', 'em', 'i', 'u', 'strike', 'del',
        'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
        'img', 'a', 'div', 'span'
    ]
    
    allowed_attributes = {
        'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
        'a': ['href', 'title', 'target', 'rel'],
        'div': ['class', 'style'],
        'span': ['class', 'style'],
        'p': ['class', 'style'],
        'h1': ['class', 'style'],
        'h2': ['class', 'style'],
        'h3': ['class', 'style'],
        'h4': ['class', 'style'],
        'h5': ['class', 'style'],
        'h6': ['class', 'style']
    }
    
    # Clean the HTML content
    cleaned_content = bleach.clean(
        content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    return cleaned_content
