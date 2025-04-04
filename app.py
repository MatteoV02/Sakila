from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_flash'

# Configuracion de la base de datos RDS
DB_HOST = "sakila-db.cnnxkpxqcklc.us-east-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "admin12345"
DB_NAME = "sakila"

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

@app.route('/')
def index():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT customer_id, first_name, last_name FROM customer")
        customers = cursor.fetchall()

        cursor.execute("SELECT store_id FROM store")
        stores = cursor.fetchall()

        cursor.execute("SELECT DISTINCT title FROM film")
        films = cursor.fetchall()

    conn.close()
    return render_template('index.html', customers=customers, stores=stores, films=films)

@app.route('/add_rental', methods=['POST'])
def add_rental():
    customer_id = request.form['customer_id']
    store_id = request.form['store_id']
    film_title = request.form['film_title']
    rental_date_str = request.form['rental_date']

    now = datetime.now().strftime('%H:%M:%S')
    rental_date = f"{rental_date_str} {now}"

    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Obtener inventory_id disponible
        query_inventory = """
            SELECT i.inventory_id, st.staff_id FROM inventory i
            JOIN film f ON i.film_id = f.film_id
            JOIN store s ON i.store_id = s.store_id
            JOIN staff st ON s.store_id = st.store_id  -- Agregamos JOIN con staff
            WHERE f.title = %s AND i.store_id = %s AND
                i.inventory_id NOT IN (
                    SELECT inventory_id FROM rental
                    WHERE return_date IS NULL
                )
            LIMIT 1
        """
        cursor.execute(query_inventory, (film_title, store_id))
        inventory_data = cursor.fetchone()

        if not inventory_data:
            conn.close()
            flash("No hay copias disponibles para esta película en esta tienda.", "danger")
            return redirect(url_for('index'))

        inventory_id, staff_id = inventory_data

        # Obtener el siguiente rental_id
        cursor.execute("SELECT MAX(rental_id) FROM rental")
        last_id = cursor.fetchone()[0] or 0
        new_rental_id = last_id + 1

        # Insertar en la tabla rental
        insert_query = """
            INSERT INTO rental (rental_id, rental_date, inventory_id, customer_id, return_date, staff_id, last_update)
            VALUES (%s, %s, %s, %s, NULL, %s, %s)
        """
        cursor.execute(insert_query, (new_rental_id, rental_date, inventory_id, customer_id, staff_id, rental_date))
        conn.commit()

    conn.close()
    flash("¡Reserva realizada exitosamente!", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
