import os

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

import mysql.connector
from flask_restx import Api, Resource, fields


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()


# ==================================================
# FLASK APP
# ==================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "gkb_project_secret_key"
)


# ==================================================
# DATABASE CONNECTION - TiDB CLOUD
# ==================================================

def get_db_connection():

    print("TIDB HOST:", os.environ.get("TIDB_HOST"))

    return mysql.connector.connect(
        host=os.environ.get("TIDB_HOST"),
        port=4000,
        user=os.environ.get("TIDB_USER"),
        password=os.environ.get("TIDB_PASSWORD"),
        database=os.environ.get("TIDB_DATABASE"),
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )


# ==================================================
# SWAGGER / FLASK-RESTX
# ==================================================

api = Api(
    app,
    version="1.0",
    title="GameRate API",
    description="API for GameRate Gaming Rating Application",
    doc="/swagger/"
)


# ==================================================
# SWAGGER MODELS
# ==================================================

user_model = api.model(
    "User",
    {
        "username": fields.String(required=True),
        "email": fields.String(required=True),
        "password": fields.String(required=True)
    }
)


review_model = api.model(
    "Review",
    {
        "user_id": fields.Integer(required=True),
        "game_id": fields.Integer(required=True),
        "rating": fields.Integer(required=True),
        "review": fields.String(required=False)
    }
)


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():
    return redirect(url_for("login"))


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        try:

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s AND password = %s
                """,
                (email, password)
            )

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:

                session["user_id"] = user["id"]
                session["username"] = user["username"]

                return redirect(url_for("dashboard"))

            flash(
                "Invalid email or password",
                "error"
            )

        except Exception as e:

            print("Database error:", e)

            flash(
                "Unable to connect to database",
                "error"
            )

    return render_template("login.html")


# ==================================================
# REGISTER
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        try:

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO users
                (username, email, password)
                VALUES (%s, %s, %s)
                """,
                (
                    username,
                    email,
                    password
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:

            flash(
                "Email already exists.",
                "error"
            )

        except Exception as e:

            print("Database error:", e)

            flash(
                "Registration failed.",
                "error"
            )

    return render_template("register.html")


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM games
            """
        )

        games = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "dashboard.html",
            games=games,
            username=session.get("username")
        )

    except Exception as e:

        print("Database error:", e)

        flash(
            "Unable to load games.",
            "error"
        )

        return redirect(url_for("login"))


# ==================================================
# GAME DETAILS
# ==================================================

@app.route("/game/<int:game_id>")
def game(game_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ------------------------------------------
        # GET GAME
        # ------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM games
            WHERE id = %s
            """,
            (game_id,)
        )

        game_data = cursor.fetchone()

        if not game_data:

            cursor.close()
            conn.close()

            flash(
                "Game not found.",
                "error"
            )

            return redirect(url_for("dashboard"))

        # ------------------------------------------
        # GET REVIEWS
        # ------------------------------------------

        cursor.execute(
            """
            SELECT
                reviews.id,
                reviews.rating,
                reviews.review,
                reviews.created_at,
                users.username
            FROM reviews
            JOIN users
                ON reviews.user_id = users.id
            WHERE reviews.game_id = %s
            ORDER BY reviews.created_at DESC
            """,
            (game_id,)
        )

        reviews = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "game.html",
            game=game_data,
            reviews=reviews
        )

    except Exception as e:

        print("Database error:", e)

        flash(
            "Unable to load game.",
            "error"
        )

        return redirect(url_for("dashboard"))


# ==================================================
# RATE GAME
# ==================================================

@app.route("/rate/<int:game_id>", methods=["POST"])
def rate(game_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    rating = request.form.get("rating")
    review = request.form.get(
        "review",
        ""
    )

    try:

        rating = int(rating)

        # ------------------------------------------
        # VALIDATE RATING
        # ------------------------------------------

        if rating < 1 or rating > 5:

            flash(
                "Rating must be between 1 and 5.",
                "error"
            )

            return redirect(
                url_for(
                    "game",
                    game_id=game_id
                )
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = session["user_id"]

        # ------------------------------------------
        # CHECK EXISTING REVIEW
        # ------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM reviews
            WHERE user_id = %s
            AND game_id = %s
            """,
            (
                user_id,
                game_id
            )
        )

        existing_review = cursor.fetchone()

        # ------------------------------------------
        # UPDATE REVIEW
        # ------------------------------------------

        if existing_review:

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
                    user_id,
                    game_id
                )
            )

        # ------------------------------------------
        # INSERT NEW REVIEW
        # ------------------------------------------

        else:

            cursor.execute(
                """
                INSERT INTO reviews
                (
                    user_id,
                    game_id,
                    rating,
                    review
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    game_id,
                    rating,
                    review
                )
            )

        # ------------------------------------------
        # CALCULATE AVERAGE RATING
        # ------------------------------------------

        cursor.execute(
            """
            SELECT AVG(rating)
            FROM reviews
            WHERE game_id = %s
            """,
            (game_id,)
        )

        result = cursor.fetchone()

        average_rating = result[0]

        if average_rating is None:
            average_rating = 0

        # ------------------------------------------
        # UPDATE GAME RATING
        # ------------------------------------------

        cursor.execute(
            """
            UPDATE games
            SET rating = %s
            WHERE id = %s
            """,
            (
                round(float(average_rating), 1),
                game_id
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash(
            "Your rating has been saved!",
            "success"
        )

    except ValueError:

        flash(
            "Invalid rating.",
            "error"
        )

    except Exception as e:

        print("Database error:", e)

        flash(
            "Unable to save rating.",
            "error"
        )

    return redirect(
        url_for(
            "game",
            game_id=game_id
        )
    )


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==================================================
# SWAGGER API - USERS
# ==================================================

users_namespace = api.namespace(
    "users",
    path="/users",
    description="User operations"
)


@users_namespace.route("/")
class UserList(Resource):

    @users_namespace.doc(
        description="Get all registered users"
    )
    def get(self):

        try:

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    email
                FROM users
                """
            )

            users = cursor.fetchall()

            cursor.close()
            conn.close()

            return users, 200

        except Exception as e:

            print("Database error:", e)

            return {
                "message": "Unable to fetch users"
            }, 500


# ==================================================
# SWAGGER API - REVIEWS
# ==================================================

reviews_namespace = api.namespace(
    "reviews",
    path="/reviews",
    description="Review operations"
)


@reviews_namespace.route("/")
class ReviewList(Resource):

    @reviews_namespace.doc(
        description="Get all game reviews"
    )
    def get(self):

        try:

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    reviews.id,
                    reviews.user_id,
                    reviews.game_id,
                    reviews.rating,
                    reviews.review,
                    reviews.created_at
                FROM reviews
                ORDER BY reviews.created_at DESC
                """
            )

            reviews = cursor.fetchall()

            cursor.close()
            conn.close()

            return reviews, 200

        except Exception as e:

            print("Database error:", e)

            return {
                "message": "Unable to fetch reviews"
            }, 500

    @reviews_namespace.expect(review_model)
    def post(self):

        data = request.get_json()

        if not data:

            return {
                "message": "JSON body is required"
            }, 400

        user_id = data.get("user_id")
        game_id = data.get("game_id")
        rating = data.get("rating")
        review = data.get(
            "review",
            ""
        )

        if (
            user_id is None
            or game_id is None
            or rating is None
        ):

            return {
                "message":
                "user_id, game_id and rating are required"
            }, 400

        try:

            rating = int(rating)

        except (TypeError, ValueError):

            return {
                "message": "Rating must be a number"
            }, 400

        if rating < 1 or rating > 5:

            return {
                "message":
                "Rating must be between 1 and 5"
            }, 400

        try:

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO reviews
                (
                    user_id,
                    game_id,
                    rating,
                    review
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    game_id,
                    rating,
                    review
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            return {
                "message":
                "Review added successfully"
            }, 201

        except Exception as e:

            print("Database error:", e)

            return {
                "message":
                "Unable to add review"
            }, 500


# ==================================================
# SWAGGER API - GAMES
# ==================================================

games_namespace = api.namespace(
    "games",
    path="/games",
    description="Game operations"
)


@games_namespace.route("/")
class GameList(Resource):

    @games_namespace.doc(
        description="Get all games"
    )
    def get(self):

        try:

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT *
                FROM games
                """
            )

            games = cursor.fetchall()

            cursor.close()
            conn.close()

            return games, 200

        except Exception as e:

            print("Database error:", e)

            return {
                "message": "Unable to fetch games"
            }, 500


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )