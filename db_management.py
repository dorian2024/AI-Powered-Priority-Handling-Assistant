import joblib
import spacy
import sqlite3
# This code contains functions that process user commands, turn them into structures objects and save them to the db
# Load models
intent_clf = joblib.load("models/intent_classifier.pkl")
nlp = spacy.load("models/entity_clf")

def process_user_command(command: str):
    """
    Classifies the user's intent and extracts entities.
    Returns a structured dictionary.
    """
    
    # Predict intent
    intent = intent_clf.predict([command])[0]
    
    # Extract entities using spaCy
    doc = nlp(command)
    entities = {ent.label_: ent.text for ent in doc.ents}
    
    # Combine into a structured object
    result = {
        "command": command,
        "intent": intent,
        "entities": entities
    }
    return result





def save_to_db(result):
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    
    entities = result["entities"]

    # Ensure missing keys are saved as None
    task = entities.get("TASK")
    deadline = entities.get("DEADLINE")
    priority = entities.get("PRIORITY")
    location = entities.get("LOCATION")
    recurrence = entities.get("RECURRENCE")
    duration = entities.get("DURATION")
    intent = result["intent"]

    try:
        c.execute("""
            INSERT INTO tasks (task, deadline, priority, location, recurrence, duration, intent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task, deadline, priority, location, recurrence, duration, intent))
        
        conn.commit()
        print("✅ Task saved to database!")
    except Exception as e:
        print("❌ Database error:", e)
    finally:
        conn.close()