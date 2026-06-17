AI-Powered Patient Bed Booking & Hospital Resource Management Ecosystem
🚀 Overview
This is a full-stack web application designed to revolutionize hospital resource management. It enables seamless booking and management of beds, doctor appointments, ambulances, nurses, and canteen services through an intuitive interface. Key highlights include role-based access, secure payments via Razorpay, automated PDF bills, and an AI-powered chatbot for natural language assistance.

Problem Solved: Automates manual hospital workflows, reduces overbooking errors, and provides real-time tracking to improve patient experience.

✨ Features
Multi-Role Authentication: Secure portals for patients, admins, doctors, ambulance services, nurses, and canteens.

Resource Management: Real-time bed availability, doctor scheduling, and emergency ambulance booking.

AI Chatbot: Natural language assistance for guided bookings.

Payments & Billing: Razorpay integration with auto-generated PDF receipts sent via email.

Dashboards: Admin insights and post-service review systems.

🛠 Tech Stack
Backend: Python 3.10+, Flask, SQLAlchemy (ORM)

Database: SQLite (dev)

Frontend: HTML/CSS/JS, Jinja2, Bootstrap

Integrations: Razorpay SDK, OpenRouter API (LLM), ReportLab (PDFs)

📦 Setup & Installation
Clone the Repository:

Bash
git clone <YOUR_REPO_URL>
cd <YOUR_PROJECT_FOLDER>
Install Dependencies:

Bash
pip install -r requirements.txt
Configure Environment Variables:
Create a .env file and add your RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, SENDER_EMAIL, SENDER_PASSWORD, and OPENROUTER_API_KEY.

Initialize Database & Run:

Bash
python -c "from app import db, app; with app.app_context(): db.create_all()"
python app.py
🏗 Architecture
📞 Contact
Author: Sudhir Bhosale

Role: Computer Engineering Student

Project: AI-Powered Patient Bed Booking & Hospital Resource Management

Built with passion for healthcare innovation.