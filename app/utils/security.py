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
        'img', 'a', 'div', 'span', 'table', 'thead', 'tbody',
        'tr', 'td', 'th', 'hr', 'sub', 'sup'
    ]
    
    allowed_attributes = {
        'img': ['src', 'alt', 'title', 'width', 'height', 'style', 'class'],
        'a': ['href', 'title', 'target', 'rel', 'class'],
        'div': ['class', 'style', 'id'],
        'span': ['class', 'style', 'id'],
        'p': ['class', 'style', 'id'],
        'h1': ['class', 'style', 'id'],
        'h2': ['class', 'style', 'id'],
        'h3': ['class', 'style', 'id'],
        'h4': ['class', 'style', 'id'],
        'h5': ['class', 'style', 'id'],
        'h6': ['class', 'style', 'id'],
        'table': ['class', 'style', 'border', 'cellpadding', 'cellspacing'],
        'tr': ['class', 'style'],
        'td': ['class', 'style', 'colspan', 'rowspan'],
        'th': ['class', 'style', 'colspan', 'rowspan'],
        'ul': ['class', 'style'],
        'ol': ['class', 'style'],
        'li': ['class', 'style'],
        'blockquote': ['class', 'style'],
        'pre': ['class', 'style'],
        'code': ['class', 'style']
    }
    
    # Clean the HTML content
    cleaned_content = bleach.clean(
        content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    return cleaned_content
