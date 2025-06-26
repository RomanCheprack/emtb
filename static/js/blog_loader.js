async function loadPost(slug) {
    // טוענים את האינדקס
    const idxRes = await fetch('templates/posts/posts.json');
    const posts = await idxRes.json();

    // מוצאים את הפוסט המבוקש לפי slug
    const postMeta = posts.find(p => p.slug === slug);
    if (!postMeta) {
        document.getElementById('blog-post').innerHTML = '<p>פוסט לא נמצא.</p>';
        return;
    }

    // טוענים את HTML של הפוסט
    const htmlRes = await fetch(postMeta.htmlPath);
    const html = await htmlRes.text();

    // מציגים אותו בתוך הדף
    document.getElementById('blog-post').innerHTML = html;

    // אופציונלי: יעד SEO וכן שינוי כותרת הדף
    document.title = postMeta.title;
}

// כשעמוד נטען, תחליט איזה slug לטעון (למשל מה-URL)
document.addEventListener('DOMContentLoaded', () => {
    // דוגמה: URL כמו example.com/?post=cheap-e-mtb
    const params = new URLSearchParams(location.search);
    const slug = params.get('post') || 'cheap-e-mtb';
    loadPost(slug);
});
