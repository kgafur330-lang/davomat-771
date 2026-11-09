
import os, json, hmac, hashlib, sqlite3, csv, io, time
from urllib.parse import parse_qsl
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR=os.path.dirname(__file__)
DB=os.getenv("DATABASE_PATH", os.path.join(APP_DIR,"davomat.db"))
BOT_TOKEN=os.getenv("BOT_TOKEN","")
SUPER_ADMIN_ID=int(os.getenv("SUPER_ADMIN_ID","474474"))
ADMIN_IDS={int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()}
DEV_MODE=os.getenv("DEV_MODE","false").lower()=="true"

app=FastAPI(title="DAVOMAT.UZ474")
@contextmanager
def db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    try: yield con; con.commit()
    finally: con.close()

def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, role TEXT DEFAULT 'student');
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, group_name TEXT DEFAULT '', photo TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS lessons(id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT NOT NULL, group_name TEXT NOT NULL, room TEXT DEFAULT '', starts TEXT DEFAULT CURRENT_TIMESTAMP, ends TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER, student_id TEXT, status TEXT DEFAULT 'present', created TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(lesson_id,student_id));
        """)
init()

def verify(init_data):
    if DEV_MODE and not BOT_TOKEN: return {"id":SUPER_ADMIN_ID,"first_name":"Demo Admin"}
    if not BOT_TOKEN or not init_data: raise HTTPException(401,"Telegram autentifikatsiyasi kerak")
    vals=dict(parse_qsl(init_data,keep_blank_values=True)); received=vals.pop("hash",None)
    if not received: raise HTTPException(401,"Telegram hash topilmadi")
    check="\n".join(f"{k}={v}" for k,v in sorted(vals.items()))
    secret=hmac.new(b"WebAppData",BOT_TOKEN.encode(),hashlib.sha256).digest()
    digest=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest,received): raise HTTPException(401,"Telegram ma'lumotlari tasdiqlanmadi")
    if int(time.time())-int(vals.get("auth_date","0"))>86400: raise HTTPException(401,"Sessiya eskirgan")
    try: return json.loads(vals["user"])
    except Exception: raise HTTPException(401,"Telegram foydalanuvchisi aniqlanmadi")

def current(x_telegram_init_data: str=Header(default="")):
    u=verify(x_telegram_init_data); uid=int(u["id"])
    role="super_admin" if uid==SUPER_ADMIN_ID else ("admin" if uid in ADMIN_IDS else "student")
    with db() as c:
        c.execute("INSERT INTO users(id,name,role) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, role=excluded.role",(uid,u.get("first_name","User"),role))
    return {"id":uid,"name":u.get("first_name","User"),"role":role}

def auth(x_telegram_init_data: str=Header(default="")): return current(x_telegram_init_data)
def staff(u): 
    if u["role"] not in ("super_admin","admin"): raise HTTPException(403,"Bu bo‘lim faqat administrator va o‘qituvchi uchun")

@app.get("/health")
def health(): return {"ok":True,"project":"DAVOMAT.UZ474"}
@app.get("/api/me")
def me(u=__import__('fastapi').Depends(auth)): return u
@app.get("/api/students")
def students(q:str="",u=__import__('fastapi').Depends(auth)):
    with db() as c:
        rows=c.execute("SELECT * FROM students WHERE student_id LIKE ? OR name LIKE ? OR group_name LIKE ? ORDER BY name LIMIT 1000",(f"%{q}%",)*3).fetchall()
    return [dict(r) for r in rows]
class Student(BaseModel):
    student_id:str
    name:str
    group_name:str=""
    photo:str=""
@app.post("/api/students")
def add_student(s:Student,u=__import__('fastapi').Depends(auth)):
    staff(u)
    try:
        with db() as c: c.execute("INSERT INTO students(student_id,name,group_name,photo) VALUES(?,?,?,?)",(s.student_id.strip(),s.name.strip(),s.group_name.strip(),s.photo))
    except sqlite3.IntegrityError: raise HTTPException(409,"Bu Student ID avval kiritilgan")
    return {"ok":True}
@app.post("/api/students/import")
async def import_students(file:UploadFile=File(...),u=__import__('fastapi').Depends(auth)):
    if u["role"]!="super_admin": raise HTTPException(403,"Import faqat Super Admin uchun")
    raw=(await file.read()).decode("utf-8-sig")
    reader=csv.DictReader(io.StringIO(raw)); count=0
    with db() as c:
        for r in reader:
            sid=(r.get("student_id") or r.get("Student ID") or r.get("ID") or "").strip()
            name=(r.get("name") or r.get("Name") or r.get("F.I.Sh") or "").strip()
            group=(r.get("group_name") or r.get("Group") or r.get("Guruh") or "").strip()
            if sid and name:
                c.execute("INSERT INTO students(student_id,name,group_name) VALUES(?,?,?) ON CONFLICT(student_id) DO UPDATE SET name=excluded.name,group_name=excluded.group_name",(sid,name,group)); count+=1
    return {"ok":True,"imported":count}
class Lesson(BaseModel):
    subject:str
    group_name:str
    room:str=""
    starts:str=""
    ends:str=""
@app.get("/api/lessons")
def lessons(u=__import__('fastapi').Depends(auth)):
    with db() as c: rows=c.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]
@app.post("/api/lessons")
def add_lesson(l:Lesson,u=__import__('fastapi').Depends(auth)):
    staff(u)
    with db() as c:
        cur=c.execute("INSERT INTO lessons(subject,group_name,room,starts,ends) VALUES(?,?,?,?,?)",(l.subject,l.group_name,l.room,l.starts,l.ends))
        return {"ok":True,"lesson_id":cur.lastrowid}
class Mark(BaseModel):
    lesson_id:int
    student_id:str
    status:str="present"
@app.post("/api/attendance")
def mark(a:Mark,u=__import__('fastapi').Depends(auth)):
    staff(u)
    if a.status not in ("present","absent","late"): raise HTTPException(400,"Noto‘g‘ri status")
    with db() as c:
        exists=c.execute("SELECT id FROM students WHERE student_id=?",(a.student_id,)).fetchone()
        if not exists: raise HTTPException(404,"Talaba topilmadi")
        c.execute("INSERT INTO attendance(lesson_id,student_id,status) VALUES(?,?,?) ON CONFLICT(lesson_id,student_id) DO UPDATE SET status=excluded.status,created=CURRENT_TIMESTAMP",(a.lesson_id,a.student_id,a.status))
    return {"ok":True}
@app.get("/api/attendance/{lesson_id}")
def attendance(lesson_id:int,u=__import__('fastapi').Depends(auth)):
    with db() as c:
        rows=c.execute("SELECT s.student_id,s.name,s.group_name,COALESCE(a.status,'absent') status FROM students s LEFT JOIN attendance a ON a.student_id=s.student_id AND a.lesson_id=? ORDER BY s.name",(lesson_id,)).fetchall()
    return [dict(r) for r in rows]
@app.get("/api/stats")
def stats(u=__import__('fastapi').Depends(auth)):
    with db() as c:
        students=c.execute("SELECT COUNT(*) n FROM students").fetchone()["n"]
        lessons=c.execute("SELECT COUNT(*) n FROM lessons").fetchone()["n"]
        marks=c.execute("SELECT COUNT(*) n FROM attendance WHERE status='present'").fetchone()["n"]
    return {"students":students,"lessons":lessons,"present_marks":marks}
app.mount("/",StaticFiles(directory=os.path.join(APP_DIR,"..","miniapp"),html=True),name="miniapp")
