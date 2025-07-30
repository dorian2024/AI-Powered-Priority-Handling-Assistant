# AI Priority Handling Assistant

An AI-powered assistant that simplifies task management by **understanding your tasks**, **assigning priorities**, and **scheduling them in Google Calendar** automatically.  

This project leverages **Natural Language Processing (NLP)** and **Machine Learning** to streamline task organization for busy students and professionals.  

---

## Features
- **Natural Language Input:** Add tasks like _"Submit assignment tomorrow 5pm"_.
- **Intent Classification:** Uses **IDF Vectorizer + Logistic Regression** to identify the type of task.
- **Entity Extraction:** Uses **spaCy** to extract deadlines, times, and other relevant entities.
- **Priority Assignment:** A **custom ML reasoning engine** determines task urgency.
- **Google Calendar Integration:** Automatically adds tasks to your calendar.
- **Interactive Frontend:** A simple **Streamlit + CSS** UI to manage your tasks.

---

## 🛠 Tech Stack
- **Python 3.9+**
- **spaCy** (Entity Recognition)
- **Scikit-learn** (IDF Vectorizer + Logistic Regression)
- **Streamlit** (Frontend)
- **Google Calendar API** (Task Scheduling)
- **CSS** (UI Styling)

---

## Note
This version is currently does not provide multiuser support. To use this project you need to get API keys from Google Cloud Console for managing your Google calendar requests. 
