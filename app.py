from flask import Flask
from threading import Thread
from main import run_bot # מייבאים את הפונקציה שהכנו מקובץ main

# יוצרים את אפליקציית הווב
app = Flask(__name__)

@app.route('/')
def health_check():
    """
    נקודת קצה (endpoint) שרנדר ו-UptimeRobot יכולים לבדוק.
    היא מחזירה הודעה פשוטה כדי להראות שהשירות חי.
    """
    return "I'm alive and the bot is running!", 200

def run_flask_app():
    """
    מריץ את שרת הווב של Flask.
    הוא חייב להאזין ב-host '0.0.0.0' כדי להיות נגיש מחוץ לקונטיינר של רנדר.
    """
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # 1. מריצים את הבוט עצמו בתהליכון (thread) נפרד
    #    זה מבטיח שלוגיקת הבוט לא תחסום את שרת הווב מלהגיב.
    print("Starting bot thread...")
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. מריצים את שרת הווב בתהליכון הראשי
    print("Starting Flask web server...")
    run_flask_app()
