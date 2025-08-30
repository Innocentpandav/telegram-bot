import os
import json
from datetime import datetime, timezone

POSTS_DIR = os.path.join('storage', 'posts')
POSTS_PER_FILE = 10000


def get_latest_posts_file():
    os.makedirs(POSTS_DIR, exist_ok=True)
    files = [f for f in os.listdir(POSTS_DIR) if f.startswith('posts_') and f.endswith('.json')]
    if not files:
        return os.path.join(POSTS_DIR, 'posts_1.json')
    files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    return os.path.join(POSTS_DIR, files[-1])


def add_post_to_json(post_meta):
    """Add a post to the latest posts JSON file, rolling over if needed."""
    latest_file = get_latest_posts_file()
    if not os.path.exists(latest_file):
        posts = []
    else:
        with open(latest_file, 'r', encoding='utf-8') as f:
            try:
                posts = json.load(f)
            except Exception:
                posts = []
    if len(posts) >= POSTS_PER_FILE:
        # Roll over to new file
        idx = int(os.path.basename(latest_file).split('_')[1].split('.')[0]) + 1
        latest_file = os.path.join(POSTS_DIR, f'posts_{idx}.json')
        posts = []
    posts.append(post_meta)
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(posts, f)
    return latest_file, len(posts) - 1  # file path, index
