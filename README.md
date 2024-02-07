# Fitness-Website

# Fitness Gym Management System

The Fitness Gym Management System is a web-based application developed for the promotion and customer management of fitness centers. This application is built using Python Flask and utilizes MSSQL as the database.

## Features

- **Authorization System**: Allows gym administrators and customers to log in to the system.
- **Activity Management**: Management and classification of activities held in the gym (Pilates, Zumba, Yoga, Fitness).
- **Instructor Management**: Management of instructor information (addition, deletion, update).
- **Customer Management**: Management of customer information (addition, deletion, update).
- **Category Management**: Classification and management of activities into categories (addition, deletion, update).
- **Private Lesson Management**: Provision and tracking of private lessons for customers.
- **Payment Plans**: Tracking and management of customer payment plans, viewing payment history.
- **Membership Operations**: Management of customer memberships (deletion, extension), implementation of campaigns.

## Technologies Used

- **Python Flask**: A lightweight and flexible framework used for web application development.
- **MSSQL**: A relational database management system used as the database.
- **Other Libraries**: 
  - `pyodbc`: Used for communication with the MSSQL database.
  - `werkzeug`: Used for secure file uploads.
  - `hashlib`: Used for password hashing.
  - Other Flask and Python libraries.

## Installation

1. Clone the project:

```
git clone https://github.com/username/project.git
```

2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Set up the MSSQL database and configure the connection settings.

4. Run the application:

```
python app.py
```
