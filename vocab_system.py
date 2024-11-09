# Import the necessary libraries
import sqlite3
import csv
import schedule
import time
import os
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Database setup
def setup_database():
    """Create the SQLite database and a table for storing vocabulary words if they don't already exist."""
    conn = sqlite3.connect('vocab.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            definition TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("\nDatabase setup complete.")


# Function to remove duplicates from the database
def remove_duplicates():
    """Remove any duplicate vocabulary words in the database and output them to a CSV file."""
    conn = sqlite3.connect('vocab.db')
    cursor = conn.cursor()

    # Find duplicates
    cursor.execute('''
        SELECT word, definition, COUNT(*)
        FROM words
        GROUP BY word, definition
        HAVING COUNT(*) > 1
    ''')
    duplicates = cursor.fetchall()

    # Write duplicates to CSV
    with open('duplicates_removed.csv', 'w', newline='') as csvfile:
        fieldnames = ['Word', 'Definition', 'Count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for word, definition, count in duplicates:
            writer.writerow({'Word': word, 'Definition': definition, 'Count': count})

    # Remove duplicates by keeping only the first occurrence of each vocabulary word
    cursor.execute('''
        DELETE FROM words
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM words
            GROUP BY word, definition
        )
    ''')

    conn.commit()
    conn.close()
    
    # If duplicates were removed, print a message
    if len(duplicates) > 0:
        print(f"Removed {len(duplicates)} duplicate vocabulary words from the database and saved to duplicates_removed.csv.")
        

# Function to add new vocabulary words to the database
def update_database():
    """Read vocabulary words from a CSV file and add new words/definitions to the database, ignoring duplicates."""
    conn = sqlite3.connect('vocab.db')
    cursor = conn.cursor()
    
    with open('vocab_words.csv', 'r') as file:
        reader = csv.DictReader(file)
        new_vocab = 0
        errors = 0
        
        for row_number, row in enumerate(reader, start=1):
            try:
                word = row['Word'].strip()
                definition = row['Definition'].strip()
                # Check if the word is already in the database
                cursor.execute("SELECT COUNT(*) FROM words WHERE word = ? AND definition = ?", (word, definition))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO words (word, definition) VALUES (?, ?)", (word, definition))
                    new_vocab += 1
            except Exception as e:
                errors += 1
                print(f"Error in row {row_number}: {row}. Error: {str(e)}")
    
    conn.commit()
    
    # Get total word count
    cursor.execute("SELECT COUNT(*) FROM words")
    total_words = cursor.fetchone()[0]
    
    conn.close()
    
    # Print summary of update
    print(f"Database update completed.")
    print(f"New words added: {new_vocab}")
    print(f"Errors: {errors}")
    print(f"Total words: {total_words}\n")
    
    # Update summary file
    with open('summary.txt', 'a') as summary:
        summary.write(f"Update Date: {datetime.now()}\n")
        summary.write(f"Total Words: {total_words}\n")
        summary.write(f"New Words Added: {new_vocab}\n")
        summary.write(f"Errors: {errors}\n\n")


# Function to retrieve a random unused vocabulary word from the database
def get_random_vocab_word():
    """Select a random vocabulary word from the database."""
    conn = sqlite3.connect('vocab.db')
    cursor = conn.cursor()
    cursor.execute("SELECT word, definition FROM words ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return None, None


# Function to send an SMS via email
def send_sms_via_email(vocab_word, definition):
    """Send a vocabulary word and definition via email to SMS gateway."""
    sender_email = "example@gmail.com"
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender_email or not sender_password:
        raise ValueError("GMAIL_USER or GMAIL_APP_PASSWORD not set in .env file")
    
    recipients = [
        "phone_number@txt.att.net",   # AT&T
        "phone_number@tmomail.net"    # T-Mobile
    ]
    
    body = f'Word of the Day:\n{vocab_word}: {definition}'
    
    msg = MIMEText(body)
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(sender_email, sender_password)
            smtp_server.sendmail(sender_email, recipients, msg.as_string())
        print("SMS sent successfully")
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")


# Function to send daily vocabulary word
def send_daily_vocab_word():
    """Gets a random vocabulary word and sends it to the recipients via email-to-SMS gateways."""
    vocab_word, definition = get_random_vocab_word()
    if vocab_word and definition:
        send_sms_via_email(vocab_word, definition)
    else:
        print("No vocabulary words available to send.")
        
# Quick test schedule
# schedule.every(1).minutes.do(send_daily_vocab_word)  # Test the send_daily_vocab_word function


# Main loop
if __name__ == "__main__":
    setup_database()
    remove_duplicates()  # Ensure duplicates are removed initially
    update_database()  # Ensure the database is updated with vocabulary words initially
    
    # Schedule tasks
    schedule.every().monday.at("00:00").do(update_database)   # Updates the database every Monday at midnight
    schedule.every().day.at("09:00").do(send_daily_vocab_word)   # Sends the daily vocabulary word every day at 9:00 AM
    schedule.every().day.at("19:00").do(send_daily_vocab_word)   # Sends the daily vocabulary word every day at 7:00 PM

    while True:
        schedule.run_pending()
        time.sleep(60)