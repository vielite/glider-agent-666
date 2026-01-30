#!/usr/bin/env python3
"""
Simple RAG Bot for API Documentation
Updated for Gemini 2.5 Flash
"""

import os
import re
import json
from collections import defaultdict
import requests
import time

# ... [SimpleRAG and parse_documents classes remain the same as before] ...
class SimpleRAG:
    def __init__(self, documents):
        self.documents = documents
        self.index = self._build_index()
    
    def _build_index(self):
        index = {}
        for idx, doc in enumerate(self.documents):
            words = re.findall(r'\w+', doc['content'].lower())
            word_freq = defaultdict(int)
            for word in words:
                if len(word) > 2: word_freq[word] += 1
            index[idx] = dict(word_freq)
        return index
    
    def search(self, query, top_k=3):
        query_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
        scores = []
        for idx, doc in enumerate(self.documents):
            word_freq = self.index[idx]
            score = 0
            for word in query_words:
                if word in word_freq: score += word_freq[word]
            title_lower = doc['title'].lower()
            for word in query_words:
                if word in title_lower: score += 10
            if score > 0: scores.append((score, idx, doc))
        scores.sort(reverse=True, key=lambda x: x[0])
        return [doc for _, _, doc in scores[:top_k]]

def parse_documents(markdown_text):
    chunks = []
    sections = re.split(r'^---$', markdown_text, flags=re.MULTILINE)
    for i, section in enumerate(sections):
        section = section.strip()
        if not section: continue
        title_match = re.search(r'^#\s+(.+)$', section, re.MULTILINE)
        title = title_match.group(1) if title_match else f"Section {i}"
        chunks.append({'title': title, 'content': section, 'id': i})
    return chunks

def query_gemini(prompt, api_key):
    """Query Google Gemini API using the 2.5 Flash model"""
    # The error indicated 2.0 has 0 quota, so we move to 2.5-flash
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(f"{url}?key={api_key}", headers=headers, json=data)
    
    if response.status_code == 429:
        raise Exception("Rate limit exceeded. Please wait about 30 seconds before trying again.")
    elif response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    result = response.json()
    try:
        return result['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        return "AI returned an empty response. Check if your prompt is too long or violates safety filters."

def main():
    print("=" * 70)
    print("🤖 RAG Bot - Gemini 2.5 Flash Edition")
    print("=" * 70)
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        api_key = input("Please enter your Google API key: ").strip()
    
    try:
        with open('api-docs-merged.md', 'r', encoding='utf-8') as f:
            doc_text = f.read()
    except FileNotFoundError:
        print("❌ Could not find api-docs-merged.md")
        return
    
    documents = parse_documents(doc_text)
    rag = SimpleRAG(documents)
    print(f"✅ Indexed {len(documents)} sections.")

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()
            if not user_input or user_input.lower() in ['quit', 'exit', 'q']: break
            
            relevant_docs = rag.search(user_input, top_k=3)
            if not relevant_docs:
                print("❌ No relevant documentation found.")
                continue
            
            context = "\n\n---\n\n".join([f"[Doc: {d['title']}]\n{d['content']}" for d in relevant_docs])
            prompt = f"Context:\n{context}\n\nQuestion: {user_input}\n\nAnswer based on the docs."
            
            print("🤖 Thinking (Gemini 2.5 Flash)...")
            answer = query_gemini(prompt, api_key)
            print(f"\n🤖 Assistant:\n{answer}")
            
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"\n❌ {e}")

if __name__ == "__main__":
    main()
