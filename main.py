import os
import json
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 数据库配置 (映射到 Docker 卷以持久化)
DB_DIR = "/app/data"
os.makedirs(DB_DIR, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_DIR}/exam.db")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class ExamProject(Base):
    __tablename__ = "exams"
    id = Column(String, primary_key=True)
    title = Column(String)
    content = Column(Text) # 存储完整的题目、选项、答案、解析 JSON
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)
app = FastAPI()

# 路由：分发前端页面
@app.get("/")
def read_index(): return FileResponse("index.html")

@app.get("/admin_page")
def read_admin(): return FileResponse("admin.html")

# API: 发布并自动保存
@app.post("/api/publish")
def publish_exam(data: dict):
    db = SessionLocal()
    exam_id = str(uuid.uuid4())[:8]
    new_exam = ExamProject(id=exam_id, title=data['title'], content=json.dumps(data['questions'], ensure_ascii=False))
    db.add(new_exam)
    db.commit()
    db.close()
    return {"id": exam_id, "message": "已自动保存到历史项目"}

# API: 获取历史项目列表 (管理端)
@app.get("/api/history")
def get_history():
    db = SessionLocal()
    exams = db.query(ExamProject).order_by(ExamProject.created_at.desc()).all()
    db.close()
    return [{"id": e.id, "title": e.title, "date": e.created_at.strftime("%m-%d %H:%M")} for e in exams]

# API: 获取试卷详情
# 管理端调用（带解析），学生端调用（不带解析）
@app.get("/api/exam/{exam_id}")
def get_exam(exam_id: str, is_admin: bool = False):
    db = SessionLocal()
    exam = db.query(ExamProject).filter(ExamProject.id == exam_id).first()
    db.close()
    if not exam: raise HTTPException(status_code=404)
    
    questions = json.loads(exam.content)
    if not is_admin:
        # 学生端脱敏：删除答案和解析字段
        for q in questions:
            q.pop('answer', None)
            q.pop('analysis', None)
            
    return {"title": exam.title, "questions": questions}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
