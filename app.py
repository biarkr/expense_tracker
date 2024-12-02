from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'admin',
    'password': '!admin',
    'database': 'expense_tracker'
}

# Create database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Home route (Login Page)
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            conn.close()
            return redirect(url_for('register'))

        # Insert new user
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Dashboard (Expense Tracker)
@app.route('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM expenses WHERE user_id = %s", (user_id,))
    expenses = cursor.fetchall()
    conn.close()
    return render_template('index.html', expenses=expenses)

# Add expense
@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        amount = request.form['amount']
        user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO expenses (user_id, name, amount) VALUES (%s, %s, %s)", (user_id, name, amount))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_expense.html')

# Update expense
@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the expense to ensure it belongs to the current user
    cursor.execute("SELECT * FROM expenses WHERE id = %s AND user_id = %s", (id, session['user_id']))
    expense = cursor.fetchone()

    if not expense:
        conn.close()
        flash('You are not authorized to edit this expense.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        amount = request.form['amount']
        cursor.execute("UPDATE expenses SET name = %s, amount = %s WHERE id = %s", (name, amount, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('update_expense.html', expense=expense)

# Delete expense
@app.route('/delete/<int:id>')
def delete_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure the expense belongs to the current user
    cursor.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Ensure the required tables exist
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create `users` table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(150) UNIQUE NOT NULL,
        password VARCHAR(200) NOT NULL
    )
    """)

    # Create `expenses` table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(100) NOT NULL,
        amount FLOAT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    conn.close()

    app.run(debug=True)

