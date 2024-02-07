import pyodbc
import subprocess
from datetime import datetime

# Database connection
connection_string = (
    r'DRIVER={SQL Server};'
    r'SERVER=(local)\SQLEXPRESS;'  # YOUR SERVER NAME
    r'DATABASE=fitnessDatabase;'  # YOUR DATABASE NAME
    r'Trusted_Connection=yes;'
)

database_name = 'fitnessDatabase'
current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f'{database_name}_backup_{current_date}.bak'

try:
    # Connect to the database
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # Build the backup command
    backup_command = f'sqlcmd -S (local)\\SQLEXPRESS -d {database_name} -E -Q "BACKUP DATABASE {database_name} TO DISK=''{backup_file}''"'

    # Run the backup command using subprocess
    subprocess.run(backup_command, shell=True, check=True)

    print(f"Backup completed successfully. Backup file: {backup_file}")

except Exception as e:
    print(f"Error during backup: {str(e)}")

finally:
    # Close the database connection
    if connection:
        connection.close()
