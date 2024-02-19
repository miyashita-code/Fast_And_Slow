# Fast_And_Slow
Combining a fast, light agent with a deep-thinking Auto-GPT to create an interactive system that's both quick and thoughtful.


## Description
Combining a fast, light agent with a deep-thinking Auto-GPT to create an interactive system that's both quick and thoughtful. To achive this, use Flask-based socket server with authentication features. It uses JWT (JSON Web Token) for API key issuance and handshake authentication. The server utilizes PostgreSQL as the database for storing authenticated user information.

## Prerequisites
- Python
- Flask
- PostgreSQL
- Firebase Authentication

## Installation & Setup

### Step 1: Install PostgreSQL
Download and install PostgreSQL from the official website.

### Step 2: Create Database in PostgreSQL
Use psql or a PostgreSQL GUI to create a new database for the application:

```
CREATE DATABASE rementia;
```

### Step 3: Database Migration
Navigate to your project directory and run the following commands to initialize, migrate, and upgrade your database:
```
flask db init
flask db migrate -m "initial migration"
flask db upgrade
```

### Step 4: Install Requirements
Install the required Python packages using pip:
```
pip install -r requirements.txt
```

### Step 5: Set Up Firebase Authentication
Create a project in Firebase Authentication and obtain your API key. Register the auth user's email and password in Firebase.

### Step 6: Configure .env File
Fill in the necessary environment variables in the .env file, including database credentials and API key.

### Step 7: Run the Flask Application
Start the Flask server by running:
```
python app.py
```


### Step 8: User Authentication
- Use /login endpoint to log in.
- Use /create_user endpoint to create a new user and obtain an API key. Remember to store this key securely.

### Step 9: Configure Client  
In the client's config, set the API key and the server's URL with its port.

### Step 10: Run Client
Run the client application in a new terminal:


## Endpoints
- /login - For user login.
- /create_user - To create a new user and receive an API key.
```
python -m http.server 8000
```

Enjoy your a slite secure Flask socket server with authentication!
