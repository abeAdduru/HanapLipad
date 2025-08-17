import sys
from src.app import app, db
from src.app import scan_and_save_flights # We'll need to create this function

# A simple command-line interface
if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'create_db':
            with app.app_context():
                db.create_all()
            print("Database tables created successfully.")
            
        elif command == 'scan_flights':
            # This will run the scanning logic within the correct app context
            scan_and_save_flights()
            
        else:
            print(f"Unknown command '{command}'")
    else:
        print("Usage: python manage.py [create_db|scan_flights]")