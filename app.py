import os

from sqlalchemy import create_engine, select
from sqlalchemy import Table, Column, MetaData
from sqlalchemy.sql import text
from flask import Flask, render_template, session, request, url_for, jsonify, redirect
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import requests
import json
from functools import wraps
import asyncio
import websocket
from datetime import datetime

app = Flask(__name__)

engine = create_engine("sqlite:///users.db")

# Create a metadata object
meta = MetaData()

# Reflect the "users" table structure into SQLAlchemy
users = Table('users', meta, autoload=True, autoload_with=engine)


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


#The login required function
def login_required(f):

    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/", methods = ["POST", "GET"])
def index():
    #Requesting Data from cryptocompare
    response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=4&page=1&sparkline=false&locale=en")
    data = response.json()

    return render_template("welcome.html", data=data)

@app.route("/register", methods=["GET", "POST"])
def register():
    with engine.connect() as db:
        """Register user"""
        if request.method == "POST":
            # Extracting the details entered on the form by the user
            first_name = request.form.get("firstname").title()
            last_name = request.form.get("lastname").title()
            username = request.form.get("username")
            password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            first_name_error = "* enter your first name"
            last_name_error = "* enter your last name"
            error1 = "* please provide your username!"
            error2 = "* password required"
            error3 = "* passwords do not match"
            starting_balance = 10000

            # Hashing the password so that it is safe in the database
            hashed_password = generate_password_hash(password)

            if not first_name:
                return render_template("register.html", first_name_error=first_name_error)
            
            elif not last_name:
                return render_template("register.html", last_name_error=last_name_error)

            # Displaying an error to the user if they don't provide a username
            elif not username:
                return render_template("register.html", error1=error1)

            # Displaying an error to the user if they don't provide a password
            elif not password:
                return render_template("register.html", error2=error2)
            
            

            # Displaying an error to the user if they provide a password with less than 8 characters
            if len(password) < 8:
                error = "* password must be more than 8 characters"
                return render_template("register.html", error2=error)

            # Displaying an error to the user if they retype a password that doesn't match the password they initially provided
            if confirmation != password:
                return render_template("register.html", error3=error3)

            # Extracting usernames from the database
            usernames = [user[0] for user in db.execute(select([text("username")]).select_from(text("users")))]

            # Displaying an error if the user provides a username that already exists in the database
            if username in usernames:
                error = "* username already taken"
                return render_template("register.html", error1=error)

            # Updating the database with the new user's information if everything is ok
            insert_user_details = text("INSERT INTO users (username, password) VALUES (:username, :hashed_password)")
            db.execute(insert_user_details, username=username, hashed_password=hashed_password)

            # Get the user's ID
            get_id = text("SELECT id FROM users WHERE username = :username")
            result = db.execute(get_id, username=username)
            id = result.fetchone()[0]

            # Initialize balance for the user
            initialize_balance = text("INSERT INTO accounts (first_name, last_name, balance, user_id) VALUES (:first_name, :last_name, :starting_balance, :id)")
            db.execute(initialize_balance, first_name=first_name, last_name=last_name, starting_balance=starting_balance, id=id)

            # Close the connection
            db.close()

            # Redirect the user to the home page after submission
            return redirect("/dashboard")

        else:

            #if the request method was GET, then the user is provided with the form
            return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    with engine.connect() as db:
        """Log user in"""

        # Forget any user_id
        session.clear()

        # User reached route via POST (as by submitting a form via POST)
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            error1 = "* You must enter your username"
            error2 = "* Must provide password"
            # Ensure username was submitted
            if not username:
                return render_template("login.html", error1=error1)

            # Ensure password was submitted, displaying an error if the user doesnt provide a password
            elif not password:
                return render_template("login.html", error2=error2)

            elif not username and not password:
                return render_template("login.html", error2=error2, error1=error1)

            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=username).fetchall()
            

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
                error = "*Invalid username and/or password"
                return render_template("login.html", error3=error)

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/dashboard")

        # User reached route via GET (as by clicking a link or via redirect)
        else:
            return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
        #setting the session to none
        session["user_id"] = None
        #taking the user back to the login page
        return redirect("/login")

#This is the route for the candlestick chart for all the cryptocurrencies available
@app.route("/chart")
@login_required
def chart():
    #requesting crypto data from coingecko api
    response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")

    #parsing the data to json format
    data = response.json()
    return render_template("chart.html", coins=data)

#This route has a list of all the crytocurrencies available
@app.route("/instruments", methods=["POST", "GET"])
@login_required
def instruments():
    if request.method == "POST":
        return redirect("/chart")
    else:
        response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")
        data = response.json()
        return render_template("instruments.html", coins=data)

@app.route("/dashboard", methods = ["POST", "GET"])
@login_required
def dashboard():
    with engine.connect() as db:
        #setting dash = true to filter some template inheritance when in the dashboard route
        dash = True
        user_id = session.get("user_id")
        history = db.execute("SELECT * FROM history WHERE user_id = :user_id", user_id=user_id).fetchall()
        transactions = db.execute("SELECT * FROM transactions WHERE user_id = :user_id", user_id=user_id).fetchall()
        username = db.execute("SELECT username from users WHERE id = :user_id", user_id=user_id).fetchone()
        account = db.execute("SELECT * from accounts WHERE user_id = :user_id", user_id=user_id).fetchall()
        first_name = account[0]["first_name"]
        last_name = account[0]["last_name"]
        balance = float(account[0]["balance"])
        formated_balance = "{:.2f}".format(balance)
        name = username[0]
        response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")
        data = response.json()
        return render_template("dashboard.html", dashboard=dash, history=history, name=name, first_name=first_name, last_name=last_name, balance=formated_balance, transactions=transactions, coins=data)


#This route has all the logic that handles buying a crypto pair
@app.route("/buy", methods = ["GET", "POST"])
@login_required
def buy():
    with engine.connect() as db:

        if request.method == "POST":

            #getting cryto data from coingecko api
            response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")
            data = response.json()
            order_type = "Buy"
        
            #getting form data for the pair the user wishes to buy
            user_id = session.get("user_id")
            try: 
                coins = float(request.form.get("coins"))
            except ValueError:
                error = "Enter the amount you want"
                return render_template("trade.html", error=error)

            price = float(request.form.get("price"))
            name = request.form.get("name")

            #Calcuating The balance and gain associated with the buying of the symbol
            symbol = request.form.get("symbol")
            symbols = [row['symbol'] for row in db.execute("SELECT symbol FROM transactions WHERE user_id = :user_id", user_id=user_id).fetchall()]
            cost = coins * price
            balance = [row['balance'] for row in db.execute("SELECT balance FROM accounts WHERE user_id = :user_id", user_id=user_id).fetchall()]

            #Getting the current date and time
            date = datetime.now().date().strftime("%Y-%m-%D")
            time = datetime.now().time().strftime("%H:%M:%S")

            
            
            db.execute("INSERT INTO transactions (name, symbol, price, coins, cost, user_id, order_type, date, time) values(:name, :symbol, :price, :coins, :cost, :user_id, :order_type, :date, :time)", name=name, symbol=symbol, price=price, coins=coins, cost=cost, user_id=user_id, order_type=order_type, date=date, time=time)


            return redirect(url_for("dashboard"))

        else:
            return redirect(url_for("trade"))
        


#This route has all the logic that handles selling a crypto pair
@app.route("/sell", methods = ["GET", "POST"])
@login_required
def sell():
    with engine.connect() as db:

        if request.method == "POST":

            #getting cryto data from coingecko api
            response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")
            data = response.json()
            order_type = "sell"
            names = {}
            for name in data:
                names[name["symbol"]] = name["name"]


            #live data from Binance



            #getting form data for the pair the user wishes to buy
            user_id = session.get("user_id")
            coins = float(request.form.get("coins"))
            price = float(request.form.get("price"))
            name = request.form.get("name")

            #Calcuating The balance and gain associated with the buying of the symbol
            symbol = request.form.get("symbol")
            symbols = [row['symbol'] for row in db.execute("SELECT symbol FROM transactions WHERE user_id = :user_id", user_id=user_id).fetchall()]
            cost = coins * price
            balance = [row['balance'] for row in db.execute("SELECT balance FROM accounts WHERE user_id = :user_id", user_id=user_id).fetchall()]

            #Getting the current date and time
            date = datetime.now().date().strftime("%Y-%m-%D")
            time = datetime.now().time().strftime("%H:%M:%S")


            #updating the transaction information into the database, thats if the symbol already exists in the database
            if symbol in symbols:
                db.execute("UPDATE transactions SET coins = coins - :coins", coins=coins)
                db.execute("UPDATE ACCOUNTS SET balance = balance + :cost", cost=cost)
                coins = [row['coins'] for row in db.execute("SELECT coins FROM transactions WHERE symbol = :symbol AND user_id = :user_id", symbol=symbol, user_id=user_id)]
                if coins <= 0:
                    db.execute("DELETE FROM transactions WHERE symbol = :symbol AND user_id = :user_id", symbol=symbol, user_id=user_id)
            

            #Inserting the transaction if the symbol is not already in the database
            else:
                db.execute("INSERT INTO transactions (name, symbol, price, coins, cost, user_id, order_type) values(:name, :symbol, :price, :coins, :cost, :user_id, order_type)", name=name, symbol=symbol, price=price, coins=coins, cost=cost, user_id=user_id, order_type=order_type)
                balance = balance[0] - cost
                db.execute("INSERT INTO history (name, symbol, price, coins, cost, balance, user_id, date, time, order_type) values(:name, :symbol, :price, :coins, :cost, :balance, :user_id, :date, :time, :order_type)", name=name, symbol=symbol, price=price, coins=coins, cost=cost, balance=balance, user_id=user_id, date=date, time=time, order_type=order_type)



            
            return redirect(url_for("dashboard"))

        else:
            symbol = request.form.get("symbol")
            name = request.form.get("name")
            return redirect(f"/trade?symbol={symbol}&name={name}")

@app.route("/exit_position", methods = ["POST"])
def exit_position():
    with engine.connect() as db:
        if request.method == "POST":
            
            name = request.form.get("name")
            price = request.form.get("price")
            coins = request.form.get("coins")
            order_type = request.form.get("order_type")
            order_date = request.form.get("date")
            order_time = request.form.get("time")
            date = datetime.now().date().strftime("%Y-%m-%D")
            time = datetime.now().time().strftime("%H:%M:%S")

            equity = request.form.get("equity")
            print(f"recieved message{equity}")
            
            symbol = request.form.get("symbol")
            user_id = session.get("user_id")

            db.execute("DELETE FROM transactions WHERE name = :symbol AND user_id = :user_id AND date = :date AND time = :time", symbol=symbol, user_id=user_id, date=order_date, time=order_time)
            db.execute("UPDATE accounts SET balance = :equity", equity=equity)
            db.execute("INSERT INTO history (name, symbol, price, coins, balance, user_id, date, time, order_type) values(:name, :symbol, :price, :coins, :balance, :user_id, :date, :time, :order_type)", name=name, symbol=symbol, price=price, coins=coins, balance=equity, user_id=user_id, date=date, time=time, order_type=order_type)


            return redirect(url_for("dashboard"))


@app.route("/trade")
def trade():
    coins = request.form.get("coins")

    if not coins:
        error = "Enter the amount you want"
    return render_template("trade.html", error=error)


@app.route("/deposit", methods = ["GET", "POST"])
def deposit():
    with engine.connect() as db:
        if request.method == "POST":
            user_id = session.get("user_id")
            amount = request.form.get("amount")
            balance = db.execute("SELECT balance FROM accounts WHERE user_id = :user_id", user_id=user_id).fetchone()
            db.execute("UPDATE accounts SET balance = balance + :deposit", deposit=amount)

            return redirect(url_for("dashboard"))
        else:
            user_id = session.get("user_id")
            balance = db.execute("SELECT balance FROM accounts WHERE user_id = :user_id", user_id=user_id).fetchone()
            return render_template("deposit.html",balance=balance[0])
        
@app.route("/withdraw", methods = ["GET", "POST"])
def withdraw():
    with engine.connect() as db:
        if request.method == "POST":
            user_id = session.get("user_id")
            amount = request.form.get("withdraw")
            db.execute("UPDATE accounts SET balance = balance - :withdrawal WHERE user_id = :user_id", withdrawal=amount, user_id=user_id)

            return redirect(url_for("dashboard"))
        else:
            user_id = session.get("user_id")
            balance = db.execute("SELECT balance FROM accounts WHERE user_id = :user_id", user_id=user_id).fetchone()
            return render_template("withdraw.html", balance=balance[0])

@app.route("/clear_history", methods = ["POST"])
def clear_history():
    if request.method == "POST":
        with engine.connect() as db:
            user_id = session.get("user_id")
            db.execute("DELETE FROM history WHERE user_id = :user_id", user_id=user_id)

            return redirect(url_for("dashboard"))

    





if __name__=="__main__":
    app.run(debug=True)
