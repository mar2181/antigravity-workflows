import os
import json
import requests
import datetime
from pathlib import Path

# Configuration
CONFIG_PATH = Path("C:/Users/mario/.gemini/antigravity/mcp_config.json")
MEMORY_DIR = Path("C:/Users/mario/.gemini/antigravity/memory")
ARCHIVE_DIR = MEMORY_DIR / "archive"
NOTION_VERSION = "2022-06-28"

def get_notion_config():
    """Extracts Notion config from mcp_config.json"""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        notion_server = config.get("mcpServers", {}).get("notion-mcp-server", {})
        headers_str = notion_server.get("env", {}).get("OPENAPI_MCP_HEADERS", "{}")
        headers = json.loads(headers_str)
        token = headers.get("Authorization", "").replace("Bearer ", "")
        return token
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def sync_file_to_notion(token, database_id, file_path):
    """Syncs a single file's content to a Notion database entry."""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = file_path.name
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": filename}}]},
            "Sync Date": {"date": {"start": datetime.datetime.now().isoformat()}}
        },
        "children": [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "caption": [],
                    "language": "markdown",
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}] # Notion block limit
                }
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

def main():
    token = get_notion_config()
    if not token:
        print("[-] Notion token not found in config.")
        return

    # 1. Check for Atlas Brain database
    print("[*] Searching for Atlas Brain database...")
    search_url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    search_data = {"query": "Atlas Brain", "filter": {"value": "database", "property": "object"}}
    resp = requests.post(search_url, headers=headers, json=search_data)
    
    db_id = None
    if resp.status_code == 200:
        results = resp.json().get("results", [])
        if results:
            db_id = results[0]['id']
            print(f"[+] Found Atlas Brain DB: {db_id}")
        else:
            print("[-] Atlas Brain DB not found. Ensure it is shared with the integration.")
    
    # 2. Local Fallback/Archive
    ARCHIVE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = ARCHIVE_DIR / f"compact_{timestamp}.json"
    
    memory_dump = {}
    files_to_sync = list(MEMORY_DIR.glob("*.md"))
    
    print(f"[*] Compacting {len(files_to_sync)} memory files...")
    for f in files_to_sync:
        with open(f, 'r', encoding='utf-8') as m:
            content = m.read()
            memory_dump[f.name] = content
            if db_id:
                success = sync_file_to_notion(token, db_id, f)
                print(f"  - {f.name}: {'Synced' if success else 'Sync Failed'}")
            else:
                print(f"  - {f.name}: Cached locally (Notion unavailable)")

    with open(archive_file, 'w', encoding='utf-8') as af:
        json.dump(memory_dump, af, indent=2)
    
    print(f"[+] Local archive created: {archive_file}")

if __name__ == "__main__":
    main()
