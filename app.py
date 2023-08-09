import os

from cs50 import SQL
from flask import Flask, render_template, session, request, jsonify, redirect
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import requests
import json
from functools import wraps
import asyncio
import websocket
from datetime import datetime

app = Flask(__name__)

db = SQL("sqlite:///users.db")

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
    response = requests.get("https://min-api.cryptocompare.com/data/news/feedsandcategories&api_key=(be2268685046f9c369db2f4a22e442d04ce4ea81415d4f97de65483edb5df25b)")
    data = response.json()

    return render_template("welcome.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        #extracting the details entered on the form by the user
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        error1 = "* please provide your username!"
        error2 = "* password required"
        error3 = "* passwords do not match"
        starting_balance = 10000

        #hashing the password so that it is safe in the database
        hash = generate_password_hash(password)


        #Displaying an error to the user If they dont provide a username
        if not username:
            return render_template("register.html", error1=error1)

        #Dislaying an error to the user if they dont provide a password
        elif not password:
            return render_template("register.html", error2=error2)

        #Displaying an error to the user if they provide a password with less than 8 characters
        if len(password) < 8:
            error = "* password must be more than 8 characters"
            return render_template("register.html", error2=error)

        #Diaplaying an error to the user if they retype a password that doesnt match the password they initially provided
        if confirmation != password:
            return render_template("register.html", error3=error3)

        #Extracting usernames from the database
        usernames = [user['username'] for user in db.execute("SELECT username FROM users;")]
        #Displaying an error if the user provides a username that already exists in the database
        if username in usernames:
            error = "* username already taken"
            return render_template("register.html", error1=error)

        #Updating the database with the new users' infomation if everything is ok
        db.execute("INSERT INTO users (username, password) values(?, ?)", username, hash)
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        id = rows[0]["id"]
        session["user_id"] = id
        db.execute("INSERT INTO accounts (balance, user_id) values(?, ?)", starting_balance, id)

        #redirecting the user to the home page after submission
        return redirect("/")

    else:

        #if the request method was GET, then the user is provided with the form
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            error = "*Invalid username and/or password"
            return render_template("login.html", error3=error)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

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
    #setting dash = true to filter some template inheritance when in the dashboard route
    dash = True
    user_id = session.get("user_id")
    history = db.execute("SELECT * FROM history WHERE user_id = ?", user_id)
    return render_template("dashboard.html", dashboard=dash, history=history)


#This route has all the logic that handles buying a crypto pair
@app.route("/buy", methods = ["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        #getting cryto data from coingecko api
        response = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&locale=en")
        data = response.json()
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
        symbols = [row['symbol'] for row in db.execute("SELECT symbol FROM transactions WHERE user_id = ?", user_id)]
        cost = coins * price
        balance = [row['balance'] for row in db.execute("SELECT balance FROM accounts WHERE user_id = ?", user_id)]

        #Getting the current date and time
        date = "2023-08-08"
        time = datetime.now().time()


        #updating the transaction information into the database, thats if the symbol already exists in the database
        if symbol in symbols:
            db.execute("UPDATE transactions SET coins = coins + ?", coins)
            db.execute("UPDATE ACCOUNTS SET balance = balance - ?", cost)

        #Inserting the transaction if the symbol is not already in the database
        else:
            db.execute("INSERT INTO transactions (name, symbol, price, coins, cost, user_id) values(?,?,?,?,?,?)", name, symbol, price, coins, cost, user_id)


        balance = balance[0] - cost
        db.execute("INSERT INTO history (name, symbol, price, coins, cost, balance, user_id, date, time) values(?,?,?,?,?,?,?,?,?)", name, symbol, price, coins, cost, balance, user_id, date, time)

        return redirect(f"/chart?name={name}&symbol={symbol}")

    else:
        return render_template("buy.html")

@app.route("/trade")
def trade():
    coins = request.form.get("coins")

    if not coins:
        error = "Enter the amount you want"
    return render_template("trade.html", error=error)




if __name__=="__main__":
    threading.Thread(target=start_websocket).start()
    app.live_price = None
    app.run()