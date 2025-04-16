#!/bin/bash
echo "Updating database with new certificate fields..."
python migrate_db.py

echo "All done! The database should now have the certificate columns."