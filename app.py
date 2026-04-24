import os
import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, Request, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

app = FastAPI()

os.makedirs("templates", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

DB_FILE = "chatbot.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id INTEGER, role TEXT, content TEXT, type TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, user_id INTEGER, preference_key TEXT, preference_value TEXT, created_at TEXT)''')
    
    c.execute("SELECT id FROM users WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO users (id, username, created_at) VALUES (1, 'default_user', ?)", (datetime.now().isoformat(),))
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_current_time():
    """Returns the current date and time in ISO format."""
    return datetime.now().isoformat()

def search_web(query: str):
    """Mocks a web search. Returns dummy results."""
    return f"Search results for '{query}': 1. Example domain (example.com) 2. Mock result."

from typing import Optional

class ChatRequest(BaseModel):
    session_id: int
    content: str
    file_uri: Optional[str] = None
    regenerate: bool = False

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/sessions")
async def get_sessions():
    conn = get_db()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    return [dict(s) for s in sessions]

@app.post("/api/sessions")
async def create_session():
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT INTO sessions (user_id, title, created_at, updated_at) VALUES (1, 'New Chat', ?, ?)", (now, now))
    session_id = c.lastrowid
    conn.commit()
    return {"id": session_id, "title": "New Chat"}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    return {"status": "success"}

@app.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: int):
    conn = get_db()
    messages = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,)).fetchall()
    result = []
    for m in messages:
        d = dict(m)
        if d['type'] != 'text':
            try:
                parsed = json.loads(d['content'])
                d['content'] = parsed.get('text', '')
                d['file_uri'] = parsed.get('file', '')
            except:
                pass
        result.append(d)
    return result

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"file_uri": file_path, "filename": file.filename}

def extract_memory(user_input: str, assistant_reply: str):
    conn = get_db()
    memories = conn.execute("SELECT preference_key, preference_value FROM memories WHERE user_id=1").fetchall()
    current_memories = {m['preference_key']: m['preference_value'] for m in memories}
    
    prompt = f"""
    You are a memory extractor. Analyze the following conversation and update the user's profile.
    Current memories: {json.dumps(current_memories)}
    User input: {user_input}
    Assistant reply: {assistant_reply}
    
    Return a JSON object containing any new or updated memories in key-value pairs (e.g. {{"user_name": "Alice", "likes": "Pizza"}}). Only output valid JSON without markdown blocks. If nothing to update, return {{}}.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        new_memories = json.loads(response.text)
        if new_memories:
            c = conn.cursor()
            now = datetime.now().isoformat()
            for k, v in new_memories.items():
                c.execute("SELECT id FROM memories WHERE user_id=1 AND preference_key=?", (k,))
                row = c.fetchone()
                if row:
                    c.execute("UPDATE memories SET preference_value=?, created_at=? WHERE id=?", (str(v), now, row['id']))
                else:
                    c.execute("INSERT INTO memories (user_id, preference_key, preference_value, created_at) VALUES (1, ?, ?, ?)", (k, str(v), now))
            conn.commit()
    except Exception as e:
        print("Memory extraction error:", e)

@app.post("/api/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    user_input = req.content
    file_uri = req.file_uri

    if req.regenerate:
        c.execute("SELECT id, role FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1", (req.session_id,))
        last_msg = c.fetchone()
        if last_msg and last_msg['role'] == 'model':
            c.execute("DELETE FROM messages WHERE id = ?", (last_msg['id'],))
        
        c.execute("SELECT content, type FROM messages WHERE session_id = ? AND role = 'user' ORDER BY timestamp DESC LIMIT 1", (req.session_id,))
        user_msg_row = c.fetchone()
        if not user_msg_row:
            return {"error": "No user message to regenerate from."}
        
        if user_msg_row['type'] != 'text':
            data = json.loads(user_msg_row['content'])
            user_input = data.get('text', '')
            file_uri = data.get('file', '')
        else:
            user_input = user_msg_row['content']
    else:
        msg_type = "text"
        content_to_save = user_input
        if file_uri:
            content_to_save = json.dumps({"text": user_input, "file": file_uri})
            msg_type = "image" if file_uri.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')) else "doc"

        c.execute("INSERT INTO messages (session_id, role, content, type, timestamp) VALUES (?, 'user', ?, ?, ?)",
                  (req.session_id, content_to_save, msg_type, now))
        
        c.execute("SELECT title FROM sessions WHERE id=?", (req.session_id,))
        title_row = c.fetchone()
        if title_row and title_row['title'] == 'New Chat' and user_input:
            new_title = user_input[:20] + "..." if len(user_input) > 20 else user_input
            c.execute("UPDATE sessions SET title=?, updated_at=? WHERE id=?", (new_title, now, req.session_id))
        else:
            c.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, req.session_id))
            
    conn.commit()

    # Load history (simplified)
    history_rows = conn.execute("SELECT role, content, type FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (req.session_id,)).fetchall()
    
    gemini_history = []
    for row in history_rows:
        if row['role'] in ['user', 'model']:
            text = row['content']
            if row['type'] != 'text' and row['role'] == 'user':
                try:
                    data = json.loads(text)
                    text = data.get('text', '')
                except:
                    pass
            gemini_history.append({"role": row['role'], "parts": [text]})
            
    # Remove the last user message from history because we pass it directly to send_message
    if gemini_history and gemini_history[-1]['role'] == 'user':
        gemini_history.pop()

    memories = conn.execute("SELECT preference_key, preference_value FROM memories WHERE user_id=1").fetchall()
    memory_str = ", ".join([f"{m['preference_key']}: {m['preference_value']}" for m in memories])
    system_instruction = f"You are a helpful AI assistant. You remember the following about the user: {memory_str}"

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_instruction,
        tools=[get_current_time, search_web]
    )

    chat_session = model.start_chat(history=gemini_history, enable_automatic_function_calling=True)
    
    message_parts = []
    if file_uri:
        try:
            uploaded_file = genai.upload_file(file_uri)
            message_parts.append(uploaded_file)
        except Exception as e:
            print("Failed to upload to Gemini:", e)
    
    if user_input:
        message_parts.append(user_input)
    
    try:
        if not message_parts:
            message_parts.append("Hello")
        response = chat_session.send_message(message_parts)
        model_reply = response.text
    except Exception as e:
        model_reply = f"Error generating response: {str(e)}"

    now = datetime.now().isoformat()
    c.execute("INSERT INTO messages (session_id, role, content, type, timestamp) VALUES (?, 'model', ?, 'text', ?)",
              (req.session_id, model_reply, now))
    conn.commit()
    
    background_tasks.add_task(extract_memory, user_input, model_reply)

    return {"reply": model_reply}

@app.get("/api/memory")
async def get_memories():
    conn = get_db()
    memories = conn.execute("SELECT * FROM memories WHERE user_id=1").fetchall()
    return [dict(m) for m in memories]
