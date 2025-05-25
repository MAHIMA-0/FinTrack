from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__)
app.secret_key = '123'

# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="fintrack"
    )

@app.route('/')
def home():
    return render_template('home.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                           (username, email, password))
            conn.commit()
            flash("Registered successfully!", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash("Error: Email already exists.", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password_input):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")

    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Income, Expenses
    cursor.execute("SELECT SUM(amount) AS total_income FROM transactions WHERE user_id = %s AND type = 'income'", (user_id,))
    income = cursor.fetchone()['total_income'] or 0

    cursor.execute("SELECT SUM(amount) AS total_expenses FROM transactions WHERE user_id = %s AND type = 'expense'", (user_id,))
    expenses = cursor.fetchone()['total_expenses'] or 0

    balance = income - expenses

    # Transaction History
    cursor.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC LIMIT 10", (user_id,))
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('dashboard.html', username=session['username'],
                           income=income, expenses=expenses,
                           balance=balance, transactions=transactions)


@app.route('/delete/<int:transaction_id>')
def delete_transaction(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure the transaction belongs to the current user
    cursor.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Transaction deleted successfully!", "success")
    return redirect(url_for('dashboard'))




@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        t_type = request.form['type']
        amount = request.form['amount']
        description = request.form['description']
        user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, type, amount, description) VALUES (%s, %s, %s, %s)",

                       (user_id, t_type, amount, description))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Transaction added!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_transaction.html')

@app.route('/monthly_report', methods=['GET'])
def monthly_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Convert month and year to int for MySQL query
    try:
        month = int(request.args.get('month'))
        year = int(request.args.get('year'))
    except (TypeError, ValueError):
        flash("Invalid month or year", "danger")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT type, SUM(amount) AS total
        FROM transactions
        WHERE user_id = %s AND MONTH(date) = %s AND YEAR(date) = %s
        GROUP BY type
    """
    cursor.execute(query, (user_id, month, year))
    results = cursor.fetchall()

    income = 0
    expense = 0
    for row in results:
        if row['type'].lower() == 'income':
            income = row['total']
        elif row['type'].lower() == 'expense':
            expense = row['total']

    cursor.close()
    conn.close()

    return render_template('monthly_report.html', income=income, expense=expense, month=month, year=year)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
