#!/bin/bash
source "/home/izcy/Desktop/UGM/KKN/script_presensi/kkn_attendance/.venv/bin/activate"
exec uvicorn "main:app" --host 0.0.0.0 --port 33002
