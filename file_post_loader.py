import os
import json

def load_post_from_ref(file_ref):
    """
    Given a file reference in the format 'json_file:index', load and return the post dict.
    """
    if ':' not in file_ref:
        raise ValueError('Invalid file reference format')
    json_file, idx = file_ref.rsplit(':', 1)
    idx = int(idx)
    json_path = os.path.join('storage', 'posts', os.path.basename(json_file))
    with open(json_path, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    return posts[idx]
