"""
file_storage.py
Rotating JSONL file storage for heavy link data and OCR text.
"""
import os
import json
import logging
from typing import Dict, Any

from datetime import datetime

CONFIG = {
    "storage_folder": "storage",
    "jsonl_max_entries": 1000
}

try:
    import ujson as jsonlib
except ImportError:
    jsonlib = json

def get_storage_folder():
    return CONFIG["storage_folder"]

def get_jsonl_max_entries():
    return CONFIG["jsonl_max_entries"]

def _get_next_file_index(folder: str, prefix: str) -> int:
    files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith('.jsonl')]
    if not files:
        return 1
    nums = [int(f[len(prefix)+1:-6]) for f in files if f[len(prefix)] == '_' and f[-6:] == '.jsonl']
    return max(nums, default=1)

def _get_current_file(folder: str, prefix: str) -> str:
    idx = _get_next_file_index(folder, prefix)
    path = os.path.join(folder, f"{prefix}_{idx}.jsonl")
    if not os.path.exists(path):
        return path
    # Check if file is full
    with open(path, 'r', encoding='utf-8') as f:
        lines = sum(1 for _ in f)
    if lines >= get_jsonl_max_entries():
        idx += 1
        path = os.path.join(folder, f"{prefix}_{idx}.jsonl")
    return path

def store_entry(prefix: str, data: Dict[str, Any]) -> str:
    """Store a dict as a JSONL entry, rotating files as needed. Returns file path."""
    folder = get_storage_folder()
    os.makedirs(folder, exist_ok=True)
    path = _get_current_file(folder, prefix)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(jsonlib.dumps(data) + '\n')
    return path

def store_link_data(link_id: int, ocr_text: str, metadata: Dict[str, Any]) -> str:
    """Store heavy link data and OCR text, return file path and line number."""
    entry = {
        "link_id": link_id,
        "ocr_text": ocr_text,
        "metadata": metadata,
        "timestamp": datetime.utcnow().isoformat()
    }
    file_path = store_entry('links', entry)
    return file_path
# Add more as needed for your bot
