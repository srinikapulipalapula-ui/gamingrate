from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "gkb_project_secret_key"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="PASSWORD",
        database="registration_db"
    )


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/")
@app.route("/login")
def login():
    # If already logged in, go to dashboard
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# =========================================================
# LOGIN USER
# =========================================================

@app.route("/login", methods=["POST"])
def login_user():

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Please enter email and password.")
        return redirect(url_for("login"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        query = """
            SELECT id, username, email
            FROM users
            WHERE email = %s AND password = %s
        """

        cursor.execute(query, (email, password))
        user = cursor.fetchone()

        if user:
            # Store login information in session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]

            return redirect(url_for("dashboard"))

        else:
            flash("Invalid email or password.")
            return redirect(url_for("login"))

    except mysql.connector.Error as error:
        print("MySQL Error:", error)
        flash("Database connection error.")
        return redirect(url_for("login"))

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# =========================================================
# REGISTER PAGE
# =========================================================

@app.route("/register")
def register():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("register.html")


# =========================================================
# REGISTER USER
# =========================================================

@app.route("/register", methods=["POST"])
def register_user():

    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if not username or not email or not password:
        flash("Please fill all the fields.")
        return redirect(url_for("register"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Check whether email already exists
        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email already registered. Please login.")
            return redirect(url_for("login"))

        # Insert new user
        query = """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (username, email, password)
        )

        db.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    except mysql.connector.Error as error:
        print("MySQL Error:", error)
        flash("Database connection error.")
        return redirect(url_for("register"))

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # User must be logged in
    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        if search:

            query = """
                SELECT
                    g.id,
                    g.name,
                    g.genre,
                    g.description,
                    COALESCE(AVG(r.rating), 0) AS rating,
                    COUNT(r.id) AS review_count
                FROM games g
                LEFT JOIN reviews r
                    ON g.id = r.game_id
                WHERE g.name LIKE %s
                   OR g.genre LIKE %s
                GROUP BY
                    g.id,
                    g.name,
                    g.genre,
                    g.description
                ORDER BY rating DESC
            """

            search_value = "%" + search + "%"

            cursor.execute(
                query,
                (search_value, search_value)
            )

        else:

            query = """
                SELECT
                    g.id,
                    g.name,
                    g.genre,
                    g.description,
                    COALESCE(AVG(r.rating), 0) AS rating,
                    COUNT(r.id) AS review_count
                FROM games g
                LEFT JOIN reviews r
                    ON g.id = r.game_id
                GROUP BY
                    g.id,
                    g.name,
                    g.genre,
                    g.description
                ORDER BY rating DESC
            """

            cursor.execute(query)

        games = cursor.fetchall()

        return render_template(
            "dashboard.html",
            games=games,
            username=session["username"],
            search=search
        )

    except mysql.connector.Error as error:
        print("MySQL Error:", error)
        flash("Unable to load games.")
        return redirect(url_for("login"))

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# =========================================================
# GAME DETAILS
# =========================================================

@app.route("/game/<int:game_id>")
def game_details(game_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # Get game information
        game_query = """
            SELECT
                g.id,
                g.name,
                g.genre,
                g.description,
                COALESCE(AVG(r.rating), 0) AS rating,
                COUNT(r.id) AS review_count
            FROM games g
            LEFT JOIN reviews r
                ON g.id = r.game_id
            WHERE g.id = %s
            GROUP BY
                g.id,
                g.name,
                g.genre,
                g.description
        """

        cursor.execute(game_query, (game_id,))
        game = cursor.fetchone()

        if not game:
            flash("Game not found.")
            return redirect(url_for("dashboard"))

        # Get reviews
        review_query = """
            SELECT
                r.rating,
                r.review,
                r.created_at,
                u.username
            FROM reviews r
            JOIN users u
                ON r.user_id = u.id
            WHERE r.game_id = %s
            ORDER BY r.created_at DESC
        """

        cursor.execute(review_query, (game_id,))
        reviews = cursor.fetchall()

        return render_template(
            "game.html",
            game=game,
            reviews=reviews,
            username=session["username"]
        )

    except mysql.connector.Error as error:
        print("MySQL Error:", error)
        flash("Unable to load game details.")
        return redirect(url_for("dashboard"))

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# =========================================================
# RATE GAME
# =========================================================

@app.route("/rate/<int:game_id>", methods=["POST"])
def rate_game(game_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect(url_for("login"))

    rating = request.form.get("rating")
    review = request.form.get("review", "").strip()

    if not rating:
        flash("Please select a rating.")
        return redirect(url_for("game_details", game_id=game_id))

    try:
        rating = int(rating)
    except ValueError:
        flash("Invalid rating.")
        return redirect(url_for("game_details", game_id=game_id))

    # Rating must be between 1 and 5
    if rating < 1 or rating > 5:
        flash("Rating must be between 1 and 5.")
        return redirect(url_for("game_details", game_id=game_id))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Check whether this user already reviewed this game
        cursor.execute(
            """
            SELECT id
            FROM reviews
            WHERE user_id = %s AND game_id = %s
            """,
            (session["user_id"], game_id)
        )

        existing_review = cursor.fetchone()

        if existing_review:

            # Update existing review
            cursor.execute(
                """
                UPDATE reviews
                SET rating = %s,
                    review = %s
                WHERE user_id = %s
                  AND game_id = %s
                """,
                (
                    rating,
                    review,
                    session["user_id"],
                    game_id
                )
            )

            flash("Your review has been updated!")

        else:

            # Add new review
            cursor.execute(
                """
                INSERT INTO reviews
                    (user_id, game_id, rating, review)
                VALUES
                    (%s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    game_id,
                    rating,
                    review
                )
            )

            flash("Review submitted successfully!")

        db.commit()

        return redirect(
            url_for("game_details", game_id=game_id)
        )

    except mysql.connector.Error as error:
        print("MySQL Error:", error)
        flash("Unable to submit review.")
        return redirect(
            url_for("game_details", game_id=game_id)
        )

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")
    return redirect(url_for("login"))


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)