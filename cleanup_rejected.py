from app import create_app
from models import db, Elector

app = create_app()

with app.app_context():
    print("Scanning for rejected electors...")
    rejected = Elector.query.filter_by(status='rejected').all()
    
    if not rejected:
        print("No rejected electors found.")
    else:
        print(f"Found {len(rejected)} rejected electors.")
        for elector in rejected:
            if elector.has_voted:
                print(f"SKIPPING: {elector.name} (has_voted=True) - Status is rejected but has voted? Manual check required.")
            else:
                print(f"Deleting: {elector.name}")
                db.session.delete(elector)
        
        db.session.commit()
        print("Cleanup complete.")
