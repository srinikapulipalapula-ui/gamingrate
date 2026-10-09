from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_restx import Api, Resource, fields

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

import os
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
api = Api(app, title="GameRate API", version="1.0", doc="/swagger/")
review_model = api.model("Review", {
    "user_id": fields.Integer(required=True),
    "game_id": fields.Integer(required=True),
    "rating": fields.Float(
    required=True,
    min=1,
    max=5,
    description="Game rating from 1 to 5"
),
    "review": fields.String(required=True)
})
@api.route("/users")
class Users(Resource):
    def get(self):
        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, username, email
                FROM users
            """)

            users = cursor.fetchall()

            return users, 200

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()

            if db:
                db.close()
@api.route("/reviews/<int:review_id>")
class ReviewById(Resource):

    @api.expect(review_model)
    def put(self, review_id):
        data = request.get_json()

        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                UPDATE reviews
                SET user_id = %s,
                    game_id = %s,
                    rating = %s,
                    review = %s
                WHERE id = %s
            """, (
                data["user_id"],
                data["game_id"],
                data["rating"],
                data["review"],
                review_id
            ))

            db.commit()

            if cursor.rowcount == 0:
                return {"message": "Review not found"}, 404

            return {"message": "Review updated successfully"}, 200

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()
    def delete(self, review_id):
        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                DELETE FROM reviews
                WHERE id = %s
            """, (review_id,))

            db.commit()

            if cursor.rowcount == 0:
                return {"message": "Review not found"}, 404

            return {"message": "Review deleted successfully"}, 200

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()
game_model = api.model("Game", {
    "name": fields.String(required=True),
    "genre": fields.String(required=True),
    "description": fields.String(required=True)
})             
@api.route("/games")
class Games(Resource):
    def get(self):
        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, name, genre, description
                FROM games
            """)

            games = cursor.fetchall()

            return games, 200

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()

            if db:
                db.close()


@api.route("/games/<int:game_id>")
class GameById(Resource):

    @api.expect(game_model)
    def put(self, game_id):
        data = request.get_json()

        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                UPDATE games
                SET name = %s,
                    genre = %s,
                    description = %s
                WHERE id = %s
            """, (
                data["name"],
                data["genre"],
                data["description"],
                game_id
            ))

            db.commit()

            if cursor.rowcount == 0:
                return {"message": "Game not found"}, 404

            return {"message": "Game updated successfully"}, 200

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()

            if db:
                db.close()
@api.route("/reviews")
class Reviews(Resource):
    def get(self):
        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute("""
    SELECT r.id, r.user_id, r.game_id,
           r.rating, r.review,
           DATE_FORMAT(r.created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
           u.username
    FROM reviews r
    JOIN users u ON r.user_id = u.id
    ORDER BY r.created_at DESC
""")
            reviews = cursor.fetchall()

            return reviews, 200

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()

            if db:
                db.close()
    @api.expect(review_model)
    def post(self):
        data = request.get_json()

        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO reviews (user_id, game_id, rating, review)
                VALUES (%s, %s, %s, %s)
            """, (
                data["user_id"],
                data["game_id"],
                data["rating"],
                data["review"]
            ))

            db.commit()

            return {
                "message": "Review added successfully"
            }, 201

        except mysql.connector.Error as error:
            return {
                "message": "Database error",
                "error": str(error)
            }, 500

        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()
#Secret key
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "gkb_project_secret_key"
)


# =========================================================
# DATABASE CONNECTION - TiDB CLOUD
# =========================================================


def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.environ.get("TIDB_HOST"),
            port=int(os.environ.get("TIDB_PORT", "4000")),
            user=os.environ.get("TIDB_USER"),
            password=os.environ.get("TIDB_PASSWORD"),
            database=os.environ.get("TIDB_DATABASE"),
            ssl_ca=os.environ.get("SSL_CA"),
        )
    except mysql.connector.Error as e:
        print("TIDB CONNECTION ERROR:", repr(e), flush=True)
        raise


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login")
def login():

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

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]

            return redirect(url_for("dashboard"))

        else:

            flash("Invalid email or password.")
            return redirect(url_for("login"))

    except mysql.connector.Error as error:

        print("Database Error:", error)
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

        # Check existing email
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

        print("Database Error:", error)
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

    if "user_id" not in session:

        flash("Please login first.")
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

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
        """

        if search:

            query += """
                WHERE g.name LIKE %s
                   OR g.genre LIKE %s
            """

            search_value = "%" + search + "%"

            params = (search_value, search_value)

        else:

            params = ()

        query += """
            GROUP BY
                g.id,
                g.name,
                g.genre,
                g.description
            ORDER BY rating DESC
        """

        cursor.execute(query, params)

        games = cursor.fetchall()

        return render_template(
            "dashboard.html",
            games=games,
            username=session["username"],
            search=search
        )

    except mysql.connector.Error as error:

        print("Database Error:", error)
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

        print("Database Error:", error)
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
        return redirect(
            url_for("game_details", game_id=game_id)
        )

    try:

        rating = int(rating)

    except ValueError:

        flash("Invalid rating.")
        return redirect(
            url_for("game_details", game_id=game_id)
        )

    # Rating must be 1-5
    if rating < 1 or rating > 5:

        flash("Rating must be between 1 and 5.")
        return redirect(
            url_for("game_details", game_id=game_id)
        )

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor()

        # Check existing review
        cursor.execute(
            """
            SELECT id
            FROM reviews
            WHERE user_id = %s
              AND game_id = %s
            """,
            (
                session["user_id"],
                game_id
            )
        )

        existing_review = cursor.fetchone()

        if existing_review:

            # Update review
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

            # Insert new review
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

        print("Database Error:", error)
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
