from fastapi import FastAPI, Form
from pydantic import BaseModel
from attendance_checker import UGMAttendanceChecker  # Your main logic separated

app = FastAPI()

class Credential(BaseModel):
    username: str
    password: str


@app.post("/check")
async def check_attendance(username: str = Form(...), password: str = Form(...)):
    checker = UGMAttendanceChecker()
    try:
        if checker.login(username, password):
            results = checker.check_all_students()
            return {"results": results}
        else:
            return {"error": "Login failed"}
    except Exception as e:
        return {"error": str(e)}
