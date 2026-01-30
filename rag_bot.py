#!/usr/bin/env python3
import os
import re
import json
from collections import defaultdict
import requests

# NEW: Import Rich components
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live

console = Console()

class SimpleRAG:
    """Simple TF-IDF based document retrieval system"""
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
    model_id = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    response = requests.post(f"{url}?key={api_key}", headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"API Error: {response.text}")
    
    result = response.json()
    return result['candidates'][0]['content']['parts'][0]['text']

def main():
    console.print(Panel.fit("[bold cyan]🤖 RAG Bot - Gemini 2.5 Flash Edition[/bold cyan]", border_style="blue"))
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        api_key = console.input("[bold yellow]Please enter your Google API key:[/bold yellow] ").strip()
    
    try:
        with open('api-docs-merged.md', 'r', encoding='utf-8') as f:
            doc_text = f.read()
    except FileNotFoundError:
        console.print("[red]❌ Could not find api-docs-merged.md[/red]")
        return
    
    with console.status("[bold green]Indexing documentation..."):
        documents = parse_documents(doc_text)
        rag = SimpleRAG(documents)
    
    console.print(f"[grey62]✅ Indexed {len(documents)} sections.[/grey62]\n")

    while True:
        try:
            user_input = console.input("[bold magenta]🧑 You:[/bold magenta] ").strip()
            if not user_input or user_input.lower() in ['quit', 'exit', 'q']: break
            
            with console.status("[bold blue]Searching & Thinking..."):
                relevant_docs = rag.search(user_input, top_k=3)
                if not relevant_docs:
                    console.print("[yellow]No relevant documentation found.[/yellow]")
                    continue
                
                context = "\n\n---\n\n".join([f"[Doc: {d['title']}]\n{d['content']}" for d in relevant_docs])
                prompt = f"Context:\n{context}\n\nQuestion: {user_input}\n\nAnswer using markdown. If you provide code, use code blocks."
                answer = query_gemini(prompt, api_key)
            
            # Render the Markdown output
            console.print("\n[bold cyan]🤖 Assistant:[/bold cyan]")
            console.print(Markdown(answer))
            
            # Sources footer
            sources = ", ".join([f"[cyan]{d['title']}[/cyan]" for d in relevant_docs])
            console.print(f"\n[dim italic]Sources: {sources}[/dim italic]")
            console.print("[hr]")
            
        except KeyboardInterrupt: break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
