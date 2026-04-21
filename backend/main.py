from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid, shutil, os, re, json, datetime
import tarfile, base64, urllib.request, urllib.parse
import sqlite3

DB_DIR = "/app/data"
os.makedirs(DB_DIR, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_DIR}/exam.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Folder(Base):
    __tablename__ = "folders"
    id = Column(String, primary_key=True)
    name = Column(String)
    sort_order = Column(Integer, default=0)

class Exam(Base):
    __tablename__ = "exams"
    id = Column(String, primary_key=True)
    title = Column(String)
    content_md = Column(Text)
    parsed_json = Column(Text)
    config_json = Column(Text)
    roster_json = Column(Text)
    folder_id = Column(String, default="default")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.now)

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String)
    student_name = Column(String)
    score = Column(Integer)
    detail_json = Column(Text)

Base.metadata.create_all(bind=engine)

# [终极保障] 原生 SQLite 强制补全所有缺失字段，绝不报错
try:
    conn_sq = sqlite3.connect(f"{DB_DIR}/exam.db")
    cur = conn_sq.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS folders (id TEXT PRIMARY KEY, name TEXT, sort_order INTEGER)")
    
    cur.execute("PRAGMA table_info(exams)")
    cols = [row[1] for row in cur.fetchall()]
    if 'folder_id' not in cols:
        cur.execute("ALTER TABLE exams ADD COLUMN folder_id TEXT DEFAULT 'default'")
    if 'sort_order' not in cols:
        cur.execute("ALTER TABLE exams ADD COLUMN sort_order INTEGER DEFAULT 0")
        
    cur.execute("SELECT count(*) FROM folders WHERE id='default'")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO folders (id, name, sort_order) VALUES ('default', '默认文件夹', 0)")
    conn_sq.commit()
    conn_sq.close()
except Exception as e:
    print(f"数据库底座构建异常: {e}")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def process_markdown_text(text_str):
    html = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<div style="text-align:center; margin:15px 0;"><img src="\2" alt="\1" style="max-width:100%; max-height:400px; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.1);"></div>', text_str)
    return html.replace('\n', '<br>')

def parse_exam(md_text, manual_title=None):
    title = manual_title or "在线测试"
    t_m = re.search(r'^#\s+(.+)$', md_text, re.M)
    if t_m: title = t_m.group(1).strip()
    questions = []
    blocks = re.split(r'\n(?=\*?\*?\d+[\.、])', md_text)
    for b in blocks:
        b = b.strip()
        if not b: continue
        num_match = re.match(r'^(\*?\*?(\d+[\.、])\*?\*?)', b)
        if not num_match: continue
        raw_num = num_match.group(2)
        end_idx = len(b)
        patterns = [r'\n\s*[A-F][\.、]', r'\n\s*(正确|错误)\s*(?=\n|<|$)', r'<details>', r'\n\s*答案[：:]', r'答案[：:]\s*(?:</b>)?\s*[A-F√×对错正确错误]+']
        for pat in patterns:
            m = re.search(pat, b)
            if m and m.start() < end_idx: end_idx = m.start()
        raw_content = b[num_match.end():end_idx].strip().replace('**', '')
        html_content = process_markdown_text(raw_content)
        q_type = "single"
        if "[多选]" in b: q_type = "multiple"
        elif "[判断]" in b: q_type = "judge"
        opts = {m[0]: m[1].replace('**','').strip() for m in re.findall(r'^([A-F])[\.、]\s*(.*)$', b, re.M)}
        if q_type == "judge": opts = {"T": "正确", "F": "错误"}
        std_ans = ""
        ans_m = re.search(r'答案[：:]\s*(?:</b>)?\s*([A-F√×对错正确错误]+)', b)
        if ans_m: std_ans = ans_m.group(1).strip()
        if q_type == "judge": std_ans = "T" if std_ans in ["正确", "对", "√", "T"] else "F"
        ana_html = "无"
        ana_m = re.search(r'解析[：:]\s*(?:</b>)?\s*(.*?)(?=</blockquote>|$)', b, re.S)
        if ana_m: ana_html = process_markdown_text(ana_m.group(1).strip())
        questions.append({"id": f"q_{len(questions)+1}", "type": q_type, "raw_num": raw_num, "content": html_content, "config": {"options": opts, "answer": std_ans, "analysis": ana_html}})
    return {"title": title, "questions": questions}

os.makedirs("uploads", exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join("uploads", filename), "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    return {"url": f"/api/uploads/{filename}"}

@app.get("/api/tree")
async def get_tree():
    db = SessionLocal()
    folders = db.query(Folder).order_by(Folder.sort_order).all()
    exams = db.query(Exam).order_by(Exam.sort_order).all()
    if not any(f.id == 'default' for f in folders): folders.insert(0, Folder(id='default', name='默认文件夹'))
    tree = []
    known_fids = set()
    for f in folders:
        known_fids.add(f.id)
        f_exams = [{"id": e.id, "title": e.title} for e in exams if e.folder_id == f.id]
        tree.append({"id": f.id, "name": f.name, "exams": f_exams})
    orphans = [{"id": e.id, "title": e.title} for e in exams if e.folder_id not in known_fids]
    if orphans:
        for t in tree:
            if t["id"] == "default": t["exams"].extend(orphans); break
    db.close()
    return tree

@app.post("/api/folders")
async def create_folder(req: dict):
    db = SessionLocal()
    fid = "f_" + uuid.uuid4().hex[:8]
    max_order = db.query(Folder).count()
    db.add(Folder(id=fid, name=req["name"], sort_order=max_order))
    db.commit(); db.close()
    return {"status": "ok"}

@app.delete("/api/folders/{fid}")
async def delete_folder(fid: str):
    db = SessionLocal()
    db.query(Exam).filter(Exam.folder_id == fid).update({"folder_id": "default"})
    db.query(Folder).filter(Folder.id == fid).delete()
    db.commit(); db.close()
    return {"status": "ok"}

@app.post("/api/tree/save")
async def save_tree(req: dict):
    db = SessionLocal()
    try:
        for f_idx, folder in enumerate(req.get("tree", [])):
            fid = folder["id"]
            db.query(Folder).filter(Folder.id == fid).update({"sort_order": f_idx})
            for e_idx, eid in enumerate(folder.get("exams", [])):
                db.query(Exam).filter(Exam.id == eid).update({"folder_id": fid, "sort_order": e_idx})
        db.commit()
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))
    finally:
        db.close()
    return {"status": "ok"}

@app.post("/api/exams")
async def create(req: dict):
    p = parse_exam(req["markdown_text"], req.get("title"))
    eid = uuid.uuid4().hex[:8]
    db = SessionLocal()
    fid = req.get("folder_id", "default")
    max_order = db.query(Exam).filter(Exam.folder_id == fid).count()
    db.add(Exam(id=eid, title=p["title"], content_md=req["markdown_text"], parsed_json=json.dumps(p, ensure_ascii=False), config_json=json.dumps(req.get("points", {"single":5,"multiple":10,"judge":2})), roster_json=json.dumps([n.strip() for n in req.get("roster", "").split('\n') if n.strip()], ensure_ascii=False), folder_id=fid, sort_order=max_order))
    db.commit(); db.close()
    return {"exam_id": eid}

@app.put("/api/exams/{eid}")
async def update_exam(eid: str, req: dict):
    db = SessionLocal()
    exam = db.query(Exam).filter(Exam.id == eid).first()
    if not exam: raise HTTPException(404)
    p = parse_exam(req["markdown_text"], req.get("title"))
    exam.title = p["title"]
    exam.content_md = req["markdown_text"]
    exam.parsed_json = json.dumps(p, ensure_ascii=False)
    exam.config_json = json.dumps(req.get("points", {"single":5,"multiple":10,"judge":2}))
    exam.roster_json = json.dumps([n.strip() for n in req.get("roster", "").split('\n') if n.strip()], ensure_ascii=False)
    db.commit(); db.close()
    return {"status": "updated"}

@app.delete("/api/exams/{eid}")
async def delete_e(eid: str):
    db = SessionLocal(); db.query(Exam).filter(Exam.id==eid).delete(); db.commit(); db.close()
    return {"status": "ok"}

@app.get("/api/exams/raw/{eid}")
async def get_raw(eid: str):
    db = SessionLocal(); e = db.query(Exam).filter(Exam.id == eid).first(); db.close()
    if not e: raise HTTPException(404)
    return {"title": e.title, "md": e.content_md, "roster": "\n".join(json.loads(e.roster_json or "[]")), "points": json.loads(e.config_json or "{}")}

@app.get("/api/exams/{eid}")
async def get_e(eid: str):
    db = SessionLocal(); e = db.query(Exam).filter(Exam.id==eid).first(); db.close()
    if not e: raise HTTPException(404)
    data = json.loads(e.parsed_json); data["roster"] = json.loads(e.roster_json or "[]")
    for q in data["questions"]: q["config"].pop("answer", None); q["config"].pop("analysis", None)
    return data

@app.post("/api/submit")
async def submit(req: dict):
    db = SessionLocal()
    exam = db.query(Exam).filter(Exam.id==req["exam_id"]).first()
    data = json.loads(exam.parsed_json); pts = json.loads(exam.config_json); stu_ans = req.get("answers", {}); score = 0; results = {}
    for q in data["questions"]:
        qid = q["id"]; correct = q["config"]["answer"]; mine = stu_ans.get(qid); q_pt = int(pts.get(q["type"], 0))
        is_ok = (str("".join(sorted(mine)) if isinstance(mine, list) else mine) == str(correct))
        if is_ok: score += q_pt
        results[qid] = "对" if is_ok else f"错(答:{mine})"
    new_sub = Submission(exam_id=req["exam_id"], student_name=req.get("name","未知"), score=score, detail_json=json.dumps(results, ensure_ascii=False))
    db.add(new_sub); db.commit()
    higher = db.query(Submission).filter(Submission.exam_id==req["exam_id"], Submission.score > score).count()
    db.close()
    return {"score": score, "rank": higher + 1}

@app.get("/api/submissions/{eid}")
async def get_subs(eid: str):
    db = SessionLocal(); ss = db.query(Submission).filter(Submission.exam_id == eid).all(); db.close()
    return [{"id": s.id, "name": s.student_name, "score": s.score, "details": json.loads(s.detail_json)} for s in ss]

@app.delete("/api/submissions/{sid}")
async def delete_sub(sid: int):
    db = SessionLocal(); db.query(Submission).filter(Submission.id == sid).delete(); db.commit(); db.close()
    return {"status": "ok"}

@app.get("/api/analysis/{eid}")
async def get_a(eid: str):
    db = SessionLocal(); e = db.query(Exam).filter(Exam.id==eid).first(); db.close()
    return json.loads(e.parsed_json)

@app.post("/api/backup")
async def backup():
    user = os.environ.get("NUTSTORE_USER"); pw = os.environ.get("NUTSTORE_PASS"); url = os.environ.get("WEBDAV_URL")
    if not all([user, pw, url]): raise HTTPException(status_code=500, detail="未配置坚果云环境变量")
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"exam_backup_{ts}.tar.gz"; path = f"/tmp/{name}"
        with tarfile.open(path, "w:gz") as tar: tar.add(DB_DIR+"/exam.db", arcname="exam.db")
        with open(path, "rb") as f: content = f.read()
        target = f"{url.rstrip('/')}/{name}"
        req = urllib.request.Request(urllib.parse.quote(target, safe=':/'), data=content, method="PUT")
        auth = base64.b64encode(f'{user}:{pw}'.encode()).decode()
        req.add_header("Authorization", f"Basic {auth}")
        urllib.request.urlopen(req)
        os.remove(path)
        return {"message": "已成功备份至坚果云！"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin")
def s_admin(): return FileResponse("/app/templates/admin.html")
@app.get("/exam/{eid}")
def s_exam(eid: str): return FileResponse("/app/templates/index.html")
@app.get("/dashboard/{eid}")
def s_dash(eid: str): return FileResponse("/app/templates/dashboard.html")
@app.get("/analysis/{eid}")
def s_ana(eid: str): return FileResponse("/app/templates/analysis.html")
@app.get("/report/{eid}")
def s_report(eid: str): return FileResponse("/app/templates/report.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
