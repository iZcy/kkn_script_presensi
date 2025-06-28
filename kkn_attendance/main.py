from fastapi import FastAPI, Form
from pydantic import BaseModel
from attendance_checker import UGMAttendanceChecker
import threading

app = FastAPI()
check_lock = threading.Lock()  # Global lock

class Credential(BaseModel):
    username: str
    password: str

@app.post("/check")
async def check_attendance(username: str = Form(...), password: str = Form(...)):
    if check_lock.locked():
        return {"error": "A check is already in progress. Please wait."}

    with check_lock:
        checker = UGMAttendanceChecker()
        try:
            if checker.login(username, password):
                results = checker.check_all_students()
                return {"results": results}
            else:
                return {"error": "Login failed"}
        except Exception as e:
            return {"error": str(e)}
