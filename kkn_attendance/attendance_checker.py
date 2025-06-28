#!/usr/bin/env python3
"""
UGM KKN Attendance Checker
Automates the process of checking daily attendance for all students in KKN program
"""

import requests
import time
import csv
from datetime import date
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from PIL import Image
import pytesseract
import io

class UGMAttendanceChecker:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0'
        })
        self.base_url = "https://simaster.ugm.ac.id"
        self.sso_url = "https://sso.ugm.ac.id"
        
    def login(self, username, password):
        login_page = self.session.get(f"{self.base_url}/ugmfw/signin_simaster/signin_proses")
        if login_page.status_code != 200:
            raise Exception("Failed to access login page")

        soup = BeautifulSoup(login_page.text, 'html.parser')
        sso_login_url = f"{self.sso_url}/cas/login?service=http%3A%2F%2Fsimaster.ugm.ac.id%2Fugmfw%2Fsignin_simaster%2Fsignin_proses"
        sso_page = self.session.get(sso_login_url)
        if sso_page.status_code != 200:
            raise Exception("Failed to access SSO page")

        sso_soup = BeautifulSoup(sso_page.text, 'html.parser')
        login_form = sso_soup.find('form', {'id': 'fm1'})
        if not login_form:
            raise Exception("Login form not found")

        form_action = login_form.get('action')
        if form_action.startswith('/'):
            form_action = urljoin(self.sso_url, form_action)

        form_data = {input_field.get('name'): input_field.get('value', '') for input_field in login_form.find_all('input') if input_field.get('name')}
        form_data['username'] = username
        form_data['password'] = password

        login_response = self.session.post(form_action, data=form_data)
        if login_response.status_code != 200:
            raise Exception("Login failed")

        if 'captchasound_verification' in login_response.url:
            return self.handle_captcha(login_response)
        return True
    
    def handle_captcha(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        captcha_form = soup.find('form')
        if not captcha_form:
            raise Exception("Captcha form not found")

        form_action = captcha_form.get('action')
        if form_action.startswith('/'):
            form_action = urljoin(self.base_url, form_action)

        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            # Refetch the CAPTCHA page every attempt
            refresh_response = self.session.get(form_action)
            soup = BeautifulSoup(refresh_response.text, 'html.parser')

            captcha_form = soup.find('form')
            captcha_src_tag = soup.find('img', {'id': 'captchaView'})
            if not captcha_form or not captcha_src_tag:
                raise Exception("Failed to refresh CAPTCHA form or image")

            captcha_src = captcha_src_tag.get('src')
            captcha_url = urljoin(self.base_url, captcha_src)
            img_response = self.session.get(captcha_url)
            if img_response.status_code != 200:
                raise Exception("Failed to fetch CAPTCHA image")

            # Process image in memory
            image = Image.open(io.BytesIO(img_response.content)).convert("L")
            image = image.point(lambda x: 0 if x < 140 else 255, '1')

            captcha_text = pytesseract.image_to_string(
                image,
                config='--psm 8 -c tessedit_char_whitelist=0123456789'
            ).strip()

            print(f"Attempt {attempt + 1}: Detected CAPTCHA = {captcha_text}")

            if not re.fullmatch(r'\d{6}', captcha_text):
                print("OCR result not valid (not 6 digits), retrying...")
                time.sleep(1)
                continue

            form_data = {
                input_field.get('name'): input_field.get('value', '')
                for input_field in captcha_form.find_all('input') if input_field.get('name')
            }
            form_data['captcha'] = captcha_text

            captcha_response = self.session.post(form_action, data=form_data)

            attempt += 1

            if captcha_response.status_code == 200 and 'beranda' in captcha_response.url:
                return True

            print(f"Attempt {attempt} failed, retrying...")
            time.sleep(2)

        raise Exception("Captcha verification failed after multiple attempts")

    def get_attendance_page(self):
        response = self.session.get(f"{self.base_url}/kkn/presensi/unit")
        if response.status_code != 200:
            raise Exception("Failed to access attendance page")
        return response.text

    def parse_student_list(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        select_element = soup.find('select', {'name': 'mhsPeriodeId'})
        if not select_element:
            raise Exception("Student dropdown not found")

        students = []
        for option in select_element.find_all('option'):
            value = option.get('value')
            text = option.get_text().strip()
            if value and text:
                match = re.match(r'^(.+?)\s*\((\d+)\)$', text)
                if match:
                    name = match.group(1).strip()
                    student_id = match.group(2)
                    students.append({
                        'value': value,
                        'name': name,
                        'student_id': student_id
                    })
        return students

    def get_student_attendance(self, student_name_to_find, driver):
        try:
            driver.get(f"{self.base_url}/kkn/presensi/unit")
            for cookie in self.session.cookies:
                if "simaster.ugm.ac.id" in cookie.domain:
                    try:
                        driver.add_cookie({
                            'name': cookie.name,
                            'value': cookie.value,
                            'path': cookie.path
                        })
                    except:
                        pass
            driver.get(f"{self.base_url}/kkn/presensi/unit")

            wait = WebDriverWait(driver, 10)
            select_element = wait.until(EC.presence_of_element_located((By.NAME, "mhsPeriodeId")))
            select = Select(select_element)

            matched_value = None
            for option in select.options:
                if student_name_to_find.lower() in option.text.lower():
                    matched_value = option.get_attribute("value")
                    break

            if not matched_value:
                return None

            select.select_by_value(matched_value)

            wait.until(lambda d: "form-loading" not in d.find_element(By.ID, "form-presensi-unit").get_attribute("class"))
            
            html_after = driver.page_source

            return self.parse_attendance_calendar(html_after)

        except:
            return None

    def parse_attendance_calendar(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        today = date.today().strftime('%Y-%m-%d')
        today_cell = soup.find('td', class_='fc-day-top', attrs={'data-date': today}) \
                     or soup.find('td', class_='fc-day', attrs={'data-date': today})
        if not today_cell:
            return None

        week_row = today_cell.find_parent('tr')
        today_column_index = list(week_row.find_all('td')).index(today_cell)
        fc_row = today_cell.find_parent('div', class_='fc-row')
        if not fc_row:
            return None

        bgevent_skeletons = fc_row.find_all('div', class_='fc-bgevent-skeleton')
        for skeleton in bgevent_skeletons:
            row = skeleton.find('tr')
            if row:
                cells = row.find_all('td')
                if len(cells) > today_column_index:
                    event_cell = cells[today_column_index]
                    style = event_cell.get('style', '')
                    text = event_cell.get_text().strip()

                    if 'rgb(120, 189, 93)' in style:
                        return {'status': 'present', 'time': text}
                    elif 'rgb(228, 96, 80)' in style:
                        return {'status': 'absent', 'time': None}
                    elif 'rgb(244, 171, 67)' in style:
                        return {'status': 'pending', 'time': text}
        return {'status': 'absent', 'time': None}

    def check_all_students(self):
        initial_page = self.get_attendance_page()
        students = self.parse_student_list(initial_page)

        results = []
        today_str = date.today().strftime('%Y-%m-%d')
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)

        for i, student in enumerate(students, 1):
            print(f"[{i}/{len(students)}] Checking: {student['name']} ({student['student_id']})")
            try:
                attendance = self.get_student_attendance(student['name'], driver)
                result = {
                    'name': student['name'],
                    'student_id': student['student_id'],
                    'date': today_str,
                    'status': attendance['status'] if attendance else 'unknown',
                    'time': attendance['time'] if attendance else None
                }
                results.append(result)
                status = result['status']
                time_str = f" at {result['time']} GMT+07:00" if result['time'] else ''
                print(f"Result: {status}{time_str}")
            except:
                results.append({
                    'name': student['name'],
                    'student_id': student['student_id'],
                    'date': today_str,
                    'status': 'error',
                    'time': None
                })

        driver.quit()
        return results

    def export_results(self, results, filename=None):
        if not filename:
            filename = f"kkn_attendance_{date.today().strftime('%Y%m%d')}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['name', 'student_id', 'date', 'status', 'time'])
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        return filename

    def print_summary(self, results):
        present = sum(1 for r in results if r['status'] == 'present')
        absent = sum(1 for r in results if r['status'] == 'absent')
        pending = sum(1 for r in results if r['status'] == 'pending')
        errors = sum(1 for r in results if r['status'] == 'error')
        total = len(results)

        print(f"\nSUMMARY - {date.today().strftime('%Y-%m-%d')}")
        print(f"Total: {total}, Present: {present}, Absent: {absent}, Pending: {pending}, Errors: {errors}")

def main():
    checker = UGMAttendanceChecker()
    try:
        username = input("UGM ID (no @ugm.ac.id): ")
        password = input("Password: ")
        if checker.login(username, password):
            results = checker.check_all_students()
            filename = checker.export_results(results)
            checker.print_summary(results)
            print(f"\nSaved to {filename}")
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
