#!/usr/bin/env python3
"""
GitHub Batch Upload Script for AJxAI Oracle Platform
Efficiently uploads multiple files to GitHub repository using REST API
"""

import os
import base64
import json
import requests
from pathlib import Path
import argparse

class GitHubBatchUploader:
    def __init__(self, token, repo_owner, repo_name):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }
    
    def encode_file(self, file_path):
        """Encode file content to base64"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return base64.b64encode(content).decode('utf-8')
        except Exception as e:
            print(f"❌ Error encoding {file_path}: {e}")
            return None
    
    def upload_file(self, local_path, github_path, commit_message):
        """Upload single file to GitHub"""
        encoded_content = self.encode_file(local_path)
        if not encoded_content:
            return False
        
        payload = {
            "message": commit_message,
            "content": encoded_content
        }
        
        url = f"{self.base_url}/{github_path}"
        
        try:
            response = requests.put(url, headers=self.headers, json=payload)
            if response.status_code in [200, 201]:
                print(f"✅ Uploaded: {github_path}")
                return True
            else:
                print(f"❌ Failed to upload {github_path}: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error uploading {github_path}: {e}")
            return False
    
    def batch_upload(self, file_mappings):
        """Upload multiple files in batch"""
        print(f"🚀 Starting batch upload to {self.repo_owner}/{self.repo_name}")
        print(f"📦 Files to upload: {len(file_mappings)}")
        
        success_count = 0
        
        for local_path, github_path, commit_message in file_mappings:
            if os.path.exists(local_path):
                if self.upload_file(local_path, github_path, commit_message):
                    success_count += 1
            else:
                print(f"⚠️  File not found: {local_path}")
        
        print(f"\n📊 Upload Summary: {success_count}/{len(file_mappings)} files uploaded successfully")
        return success_count == len(file_mappings)

def main():
    parser = argparse.ArgumentParser(description='Batch upload files to GitHub')
    parser.add_argument('--token', required=True, help='GitHub personal access token')
    parser.add_argument('--owner', required=True, help='Repository owner')
    parser.add_argument('--repo', required=True, help='Repository name')
    parser.add_argument('--config', help='JSON config file with file mappings')
    
    args = parser.parse_args()
    
    uploader = GitHubBatchUploader(args.token, args.owner, args.repo)
    
    if args.config:
        # Load file mappings from config
        with open(args.config, 'r') as f:
            config = json.load(f)
        file_mappings = config.get('files', [])
    else:
        # Default AJxAI file mappings
        file_mappings = [
            # Core files
            ("README.md", "README.md", "📚 Update README with batch upload instructions"),
            ("requirements.txt", "requirements.txt", "📦 Update Python dependencies"),
            (".gitignore", ".gitignore", "🔒 Update gitignore for security"),
            ("TASK_LOG.md", "TASK_LOG.md", "📋 Update agent task tracking log"),
            
            # Backend core
            ("backend/main.py", "backend/main.py", "🚀 Update FastAPI backend application"),
            ("backend/__init__.py", "backend/__init__.py", "🔧 Backend package init"),
            
            # Data layer
            ("backend/data_layer/__init__.py", "backend/data_layer/__init__.py", "🔧 Data layer package init"),
            ("backend/data_layer/angel.py", "backend/data_layer/angel.py", "🏦 Update Angel One SmartAPI integration"),
            ("backend/data_layer/binance.py", "backend/data_layer/binance.py", "₿ Update Binance API integration"),
            ("backend/data_layer/coingecko.py", "backend/data_layer/coingecko.py", "🦎 Update CoinGecko API integration"),
            
            # Scripts
            ("scripts/github_batch_upload.py", "scripts/github_batch_upload.py", "🔧 Add GitHub batch upload script"),
        ]
    
    uploader.batch_upload(file_mappings)

if __name__ == "__main__":
    main()