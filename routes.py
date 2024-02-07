from flask import Flask, flash, redirect, render_template, request, session, url_for
import pyodbc
from datetime import date, datetime, timedelta
from flask import render_template
from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import hashlib
from flask import render_template
from flask import jsonify 
app = Flask(__name__)
app.secret_key = 'secret'

# database connection
connection_string = (
    r'DRIVER={SQL Server};'
    r'SERVER=(local)\SQLEXPRESS;'  # YOUR SERVER NAME
    r'DATABASE=fitnessDatabase;'  # YOUR DATABASE NAME
    r'Trusted_Connection=yes;'
)
connection = pyodbc.connect(connection_string)
cursor = connection.cursor()

# Databasedeb fotoğraf alma
UPLOAD_FOLDER = 'static/assets/img'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def authenticated():
    # Oturum değişkeni kullanarak kimlik doğrulama
    if 'user_id' in session:
        return True
    else:
        return False

class Activity:
    def __init__(self, ActivityID, ActivityName, Description, InstructorID, InstructorName, photo_path, ActivityDay, DetailedDescription, ActivityTime):
        self.ActivityID = ActivityID
        self.ActivityName = ActivityName
        self.Description = Description
        self.InstructorID = InstructorID
        self.InstructorName = InstructorName  # New parameter
        self.photo_path = photo_path
        self.ActivityDay = ActivityDay
        self.DetailedDescription = DetailedDescription
        self.ActivityTime = ActivityTime

def save_activity_to_database(title, description, photo_path):
    cursor.execute('INSERT INTO Activities (ActivityName, Description, photo_path) VALUES (?, ?, ?)',
                   (title, description, photo_path))
    connection.commit()

# Function to get activities from the database
def get_activities_from_database():
    cursor.execute('SELECT * FROM Activities')
    activities = []

    for row in cursor.fetchall():
        activity_id = row[0]
        activity_name = row[1]
        description = row[2]
        instructor_id = row[3]
        photo_path = row[4]
        activity_day = row[5]
        detailed_description = row[6]
        activity_time = row[7]

        # Get instructor name using the get_instructor_name function
        instructor_name = get_instructor_name(instructor_id)

        # Create an Activity object with the updated information (excluding photo_path)
        activity = Activity(
            ActivityID=activity_id,
            ActivityName=activity_name,
            Description=description,
            InstructorID=instructor_id,  # Keeping the original ID for reference
            InstructorName=instructor_name,  # Replace InstructorID with InstructorName
            photo_path = photo_path,
            ActivityDay=activity_day,
            DetailedDescription=detailed_description,
            ActivityTime=activity_time
        )

        # Append the Activity object to the activities list
        activities.append(activity)

    return activities

@app.route('/')
def index():
    # Get the list of activities from the database
    activities = get_activities_from_database()

    # SQL query: Joining Reviews and Customers tables
    sql_query = """
        SELECT 
            r.ReviewID, r.ReviewText, r.Rating,
            c.FirstName, c.LastName
        FROM 
            Reviews r
        JOIN 
            Customers c ON r.CustomerID = c.CustomerID
        WHERE 
            r.Rating >= 3
    """

    cursor.execute(sql_query)
    result = cursor.fetchall()

    reviews = [
        {
            'ReviewID': row.ReviewID,
            'ReviewText': row.ReviewText,
            'Rating': row.Rating,
            'FirstName': row.FirstName,
            'LastName': row.LastName,
        }
        for row in result
    ]

    return render_template('index.html', activities=activities, reviews=reviews)

@app.route('/uye_giris', methods=['GET', 'POST'])
def uye_giris():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # MSSQL sorgusu
        sql_query = "SELECT * FROM Customers WHERE UserName=? AND Password=?"
        cursor.execute(sql_query, (username, hashed_password))
        user = cursor.fetchone()

        if user:
            # Kullanıcıyı oturum açık olarak işaretle
            session['user_id'] = user.CustomerID
            flash('Login successful', 'success')
            return redirect(url_for('customer_profile'))
        else:
            flash('Login failed. Check your username and password.', 'error')
            return redirect(url_for('uye_giris'))

    return render_template('uye_giris.html')

@app.route('/uye_kayit', methods=['GET', 'POST'])
def uye_kayit():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        password = request.form['password']
        password_repeat = request.form['password_repeat']
        email = request.form['email']
        phone_number = request.form['phone_number']

        # Kullanıcı adının mevcut olup olmadığını kontrol et
        existing_user_query = "SELECT COUNT(*) FROM Customers WHERE UserName = ?"
        cursor.execute(existing_user_query, (username,))
        existing_user_count = cursor.fetchone()[0]

        if existing_user_count > 0:
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('uye_kayit'))

        # Şifre kontrolü
        if password != password_repeat:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('uye_kayit'))

        # Parolayı hashle ve veritabanına kaydet
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # MüşteriID için benzersiz bir tanımlayıcı oluştur
        sql_query = "INSERT INTO Customers (FirstName, LastName, UserName, Password, Email, PhoneNumber, MembershipStartDate) VALUES (?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(sql_query, (first_name, last_name, username, hashed_password, email, phone_number, current_date))
        connection.commit()

        flash('Sign up successful. You can now log in.', 'success')
        return redirect(url_for('uye_giris'))

    return render_template('uye_kayit.html')

@app.route('/aktiviteler')
def aktiviteler():
    # Aktivite listesini almak için veritabanı sorgusu yapılabilir
    activities = get_activities_from_database()

    return render_template('aktiviteler.html', activities=activities)
get_instructors_query = '''
    SELECT 
        Instructors.*,
        Activities.ActivityName,
        Activities.Description,
        Activities.photo_path AS ActivityPhotoPath
    FROM 
        Instructors
    LEFT JOIN 
        Activities ON Instructors.InstructorID = Activities.InstructorID
'''

@app.route('/egitmenler')
def egitmenler():
    # Eğitmenleri ve bağlı oldukları aktiviteleri veritabanından al
    cursor.execute(get_instructors_query)
    instructor_activities = cursor.fetchall()

    # Eğitmenleri ve aktiviteleri HTML sayfasına geçir
    return render_template('egitmenler.html', instructor_activities=instructor_activities)

class Instructor:
    def __init__(self, InstructorID, FirstName, LastName):
        self.InstructorID = InstructorID
        self.FirstName = FirstName
        self.LastName = LastName

def get_instructor_name(instructor_id):
    cursor.execute('SELECT * FROM Instructors WHERE InstructorID = ?', (instructor_id,))
    row = cursor.fetchone()
    if row:
        return Instructor(InstructorID=row[0], FirstName=row[1], LastName=row[2])
    return None

@app.route('/aktivite_detay/<int:activity_id>')
def aktivite_detay(activity_id):
    # Aktiviteyi sorgula
    cursor.execute(f"SELECT * FROM activities WHERE ActivityID = {activity_id}")
    activity = cursor.fetchone()

    if activity:
        # Instructor tablosundan InstructorName'i al
        instructor = get_instructor_name(activity[3])

        if instructor:
            activity_time = format_activity_time(activity[7])

            # Aktiviteyi ve InstructorName'i HTML sayfasına aktar
            return render_template("aktivite_detay.html", activity=activity, instructor=instructor, activity_time=activity_time)

    # Handle cases where either the activity or the instructor data is not available
    return "Aktivite veya eğitmen bulunamadı."

def format_activity_time(raw_time):
    try:
        # raw_time bir string olarak kabul edilir
        datetime_obj = datetime.strptime(raw_time, '%H:%M:%S')
        formatted_time = datetime_obj.strftime('%H:%M')
        return formatted_time
    except ValueError as e:
        # Eğer hata alınırsa, hatayı yazdır ve boş bir string döndür
        print(f"Error formatting time: {e}")
        return ""

@app.route('/iletisim')
def iletisim():
    return render_template('iletisim.html')

@app.route('/uye_bilgiler', methods=['GET', 'POST'])
def uye_bilgiler():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('uye_giris'))

    if request.method == 'POST':
        # Formdan gelen tüm bilgileri al
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gender = request.form['gender']
        address = request.form['address']

        # MSSQL sorgusu
        sql_query = """
            UPDATE Customers
            SET UserName=?, FirstName=?, LastName=?, Gender=?, Address=?
            WHERE CustomerID=?
        """
        cursor.execute(sql_query, (username, first_name, last_name, gender, address, session['user_id']))

        # Password Update Logic
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if current_password and new_password and confirm_new_password:
            # Get the hashed password from the database
            cursor.execute("SELECT Password FROM Customers WHERE CustomerID=?", (session['user_id'],))
            stored_password = cursor.fetchone()[0]

            # Check if the current password matches the stored password
            if hashlib.sha256(current_password.encode()).hexdigest() == stored_password:
                # Validate the new password (e.g., length, complexity)
                # Hash the new password
                hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()

                # Update the password in the database
                cursor.execute("UPDATE Customers SET Password=? WHERE CustomerID=?", (hashed_new_password, session['user_id']))
                connection.commit()  # Commit the changes to the database
                flash('Password updated successfully.', 'success')
            else:
                flash('Current password is incorrect.', 'error')

        else:
            flash('Please fill in all password fields.', 'error')

        flash('Profile information updated successfully.', 'success')

    # Kullanıcının mevcut profil bilgilerini getir
    sql_query = "SELECT * FROM Customers WHERE CustomerID=?"
    cursor.execute(sql_query, (session['user_id'],))
    user = cursor.fetchone()

    return render_template('uye_bilgiler.html', user=user)

@app.route('/logout')
def logout():
    # Kullanıcı oturumunu sonlandır
    session.pop('user_id', None)
    session.pop('username', None)

    flash('Logout successful', 'success')
    return redirect(url_for('index')) 


@app.route('/customer_profile')
def customer_profile():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('uye_giris'))

    all_activities_query = "SELECT * FROM Activities"
    cursor.execute(all_activities_query)
    all_activities = cursor.fetchall()
    # Kullanıcının bilgilerini getir
    sql_query = "SELECT * FROM Customers WHERE CustomerID=?"
    cursor.execute(sql_query, (session['user_id'],))
    user = cursor.fetchone()

    # Kullanıcının aldığı aktiviteleri getir
    activities_query = "SELECT Activities.* FROM Activities WHERE Activities.ActivityID IN (SELECT ActivityID FROM Customers WHERE CustomerID=?)"
    cursor.execute(activities_query, (session['user_id'],))
    activities = cursor.fetchall()

    # Kullanıcının verdiği yorumları getir
    reviews_query = "SELECT * FROM Reviews WHERE CustomerID=?"
    cursor.execute(reviews_query, (session['user_id'],))
    reviews = cursor.fetchall()

    return render_template('customer_profile.html', user=user, activities=activities, reviews=reviews, all_activities=all_activities)

@app.route('/save_selected_activity', methods=['POST'])
def save_selected_activity():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('uye_giris'))

    if request.method == 'POST':
        selected_activity_id = request.form['selected_activity_id']

        # Seçilen aktivitenin ID'sini veritabanına kaydet
        save_activity_query = "UPDATE Customers SET ActivityID=? WHERE CustomerID=?"
        cursor.execute(save_activity_query, (selected_activity_id, session['user_id']))
        connection.commit()

        flash('Selected activity saved successfully.', 'success')
        return redirect(url_for('customer_profile'))

    return redirect(url_for('customer_profile'))

# Aktivitelerin değerlendirildiği sayfa
@app.route('/activity_reviews', methods=['GET'])
def activity_reviews():
    activities = get_activities_from_database()
    return render_template('activity_reviews.html', activities=activities)

# Aktivite değerlendirmesi gönderme
@app.route('/submit_activity_review/<int:activity_id>', methods=['POST'])
def submit_activity_review(activity_id):
    if 'user_id' not in session:
        flash('Please login to submit a review.', 'error')
        return redirect(url_for('uye_giris'))

    review_text = request.form['review_text']
    rating = int(request.form['rating'])

    try:
        # Aktiviteye yeni değerlendirme eklemek için SQL sorgusu
        sql_query = "INSERT INTO Reviews (CustomerID, ActivityID, ReviewText, Rating) VALUES (?, ?, ?, ?)"
        cursor.execute(sql_query, (session['user_id'], activity_id, review_text, rating))
        connection.commit()

        flash('Review submitted successfully.', 'success')
    except Exception as e:
        # Hata durumunda
        print(f"Error submitting review: {e}")
        flash('An error occurred while submitting the review.', 'error')

    return redirect(url_for('activity_reviews'))

def get_instructors_from_database_admin(cursor):
    # SQL sorgusu
    sql_query = 'SELECT InstructorID, FirstName, LastName, PhoneNumber, Email, Gender FROM Instructors'

    # Sorguyu çalıştır
    cursor.execute(sql_query)

    # Tüm verileri al
    instructors = cursor.fetchall()

    return instructors


def get_instructors_from_database():

    cursor.execute('SELECT * FROM Instructors')
    instructors = []

    for row in cursor.fetchall():
        instructor = Instructor(InstructorID=row[0], FirstName=row[1], LastName=row[2])
        instructors.append(instructor)

    return instructors



# Eğitmenlerin değerlendirildiği sayfa
@app.route('/instructor_reviews', methods=['GET'])
def instructor_reviews():
    instructors = get_instructors_from_database()
    return render_template('instructor_reviews.html', instructors=instructors)

# Eğitmene değerlendirme gönderme
@app.route('/submit_instructor_review/<int:instructor_id>', methods=['POST'])
def submit_instructor_review(instructor_id):
    if 'user_id' not in session:
        flash('Please login to submit a review.', 'error')
        return redirect(url_for('uye_giris'))

    review_text = request.form['review_text']
    rating = int(request.form['rating'])

    try:
        # Eğitmene yeni değerlendirme eklemek için SQL sorgusu
        sql_query = "INSERT INTO Reviews (CustomerID, InstructorID, ReviewText, Rating) VALUES (?, ?, ?, ?)"
        cursor.execute(sql_query, (session['user_id'], instructor_id, review_text, rating))
        connection.commit()

        flash('Review submitted successfully.', 'success')
    except Exception as e:
        # Hata durumunda
        print(f"Error submitting review: {e}")
        flash('An error occurred while submitting the review.', 'error')

    return redirect(url_for('instructor_reviews'))

class Review:
    def __init__(self, review_id, customer_id, review_text, rating):
        self.review_id = review_id
        self.customer_id = customer_id
        self.review_text = review_text
        self.rating = rating

def get_gym_reviews_from_database():
    cursor.execute('SELECT * FROM Reviews WHERE ActivityID IS NULL AND InstructorID IS NULL')
    gym_reviews = []

    for row in cursor.fetchall():
        review = Review(
            review_id=row[0],
            customer_id=row[1],
            review_text=row[2],
            rating=row[3],
        )
        gym_reviews.append(review)

    return gym_reviews

# Spor salonunun değerlendirildiği sayfa
@app.route('/gym_reviews', methods=['GET'])
def gym_reviews():
    gym_reviews = get_gym_reviews_from_database()
    return render_template('gym_reviews.html', gym_reviews=gym_reviews)


# Spor salonuna değerlendirme gönderme
@app.route('/submit_gym_review', methods=['POST'])
def submit_gym_review():
    if 'user_id' not in session:
        flash('Please login to submit a review.', 'error')
        return redirect(url_for('uye_giris'))

    review_text = request.form['review_text']
    rating = int(request.form['rating'])

    try:
        # Spor salonuna yeni değerlendirme eklemek için SQL sorgusu
        sql_query = "INSERT INTO Reviews (CustomerID, ReviewText, Rating) VALUES (?, ?, ?)"
        cursor.execute(sql_query, (session['user_id'], review_text, rating))
        connection.commit()

        flash('Review submitted successfully.', 'success')
    except Exception as e:
        # Hata durumunda
        print(f"Error submitting review: {e}")
        flash('An error occurred while submitting the review.', 'error')

    return redirect(url_for('gym_reviews'))

class PrivateLesson:
    def __init__(self, LessonID, LessonDateTime, CustomerID, InstructorID, ActivityID):
        self.LessonID = LessonID
        self.LessonDateTime = LessonDateTime
        self.CustomerID = CustomerID
        self.InstructorID = InstructorID
        self.ActivityID = ActivityID

def get_private_lessons_by_customer_id(customer_id):
    try:
        # Belirli bir müşteri ID'sine göre özel ders rezervasyonlarını getiren SQL sorgusu
        sql_query = """
            SELECT pl.LessonID, pl.LessonDateTime, pl.CustomerID, pl.InstructorID, pl.ActivityID,
                   i.FirstName AS InstructorFirstName, i.LastName AS InstructorLastName,
                   a.ActivityName
            FROM PrivateLessons pl
            INNER JOIN Instructors i ON pl.InstructorID = i.InstructorID
            INNER JOIN Activities a ON pl.ActivityID = a.ActivityID
            WHERE pl.CustomerID = ?
        """
        cursor.execute(sql_query, (customer_id,))
        private_lessons = cursor.fetchall()

        return private_lessons
    except Exception as e:
        # Hata durumunda
        print(f"Error getting private lessons: {e}")
        flash('An error occurred while getting private lessons.', 'error')
        return None



def save_private_lesson_to_database(lesson_datetime, instructor_id, activity_id):
    try:
        # Giriş yapmış kullanıcının ID'sini al
        customer_id = session.get('user_id')

        # Özel ders rezervasyonunu eklemek için SQL sorgusu
        sql_query = """
            INSERT INTO PrivateLessons (LessonDateTime, InstructorID, ActivityID, CustomerID)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql_query, (lesson_datetime, instructor_id, activity_id, customer_id))
        connection.commit()

        flash('Reservation made successfully.', 'success')
    except Exception as e:
        # Hata durumunda
        print(f"Error making reservation: {e}")
        flash('An error occurred while making the reservation.', 'error')


def get_activity_id_by_name(activity_name):
    cursor.execute('SELECT ActivityID FROM Activities WHERE ActivityName = ?', (activity_name,))
    result = cursor.fetchone()
    return result[0] if result else None


# Eğer activities ve instructors listelerini başka bir yerden alıyorsanız, bu listeleri güncelleyin.
activities = get_activities_from_database()
instructors = get_instructors_from_database()
# get_instructor_id_by_name fonksiyonunu güncelle

def get_instructor_id_by_name(first_name, last_name):
    cursor.execute('SELECT InstructorID FROM Instructors WHERE FirstName = ? AND LastName = ?', (first_name, last_name))
    result = cursor.fetchone()
    return result[0] if result else None

@app.route('/private_lesson_reservation', methods=['GET', 'POST'])
def private_lesson_reservation():
    if request.method == 'POST':
        activity_name = request.form['activity_name']
        instructor_name = request.form['instructor_name']
        lesson_datetime_str = request.form['lesson_datetime']

        # Eğitmen adını boşluğa göre ayır
        instructor_names = instructor_name.split()
        if len(instructor_names) == 2:
            first_name, last_name = instructor_names
        else:
            flash('Invalid instructor name format', 'error')
            return redirect(url_for('private_lesson_reservation'))

        # Aktivite ve eğitmenin ID'lerini al
        activity_id = get_activity_id_by_name(activity_name)
        instructor_id = get_instructor_id_by_name(first_name, last_name)

        # Tarih ve zamanı uygun formata çevir
        lesson_datetime = datetime.strptime(lesson_datetime_str, '%Y-%m-%dT%H:%M')

        # Özel ders rezervasyonunu kaydet
        save_private_lesson_to_database(lesson_datetime, instructor_id, activity_id)



    return render_template('private_lesson_reservation.html', activities=activities, instructors=instructors)


# Özel Ders Rezervasyonlarını Gösteren Sayfa
@app.route('/private_lessons')
def private_lessons():
    if 'user_id' not in session:
        flash('Please login to view your reservations.', 'error')
        return redirect(url_for('uye_giris'))

    # Kullanıcının özel ders rezervasyonlarını getir
    user_private_lessons = get_private_lessons_by_customer_id(session['user_id'])
    
    return render_template('private_lessons.html', user_private_lessons=user_private_lessons)

# View all private lessons with customer and instructor names
@app.route('/private_lessons')
def view_private_lessons():
    query = """
    SELECT pl.LessonID, pl.LessonDateTime, c.FirstName + ' ' + c.LastName AS CustomerName,
           i.FirstName + ' ' + i.LastName AS InstructorName, pl.ActivityID
    FROM PrivateLessons pl
    JOIN CustomersTable c ON pl.CustomerID = c.CustomerID
    JOIN Instructors i ON pl.InstructorID = i.InstructorID
    """
    cursor.execute(query)
    private_lessons = cursor.fetchall()
    return render_template('private_lessons.html', private_lessons=private_lessons)

# Admin Kısmı

def authenticate_admin(username, password):
    # Şifreyi hashle
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Admini veritabanında kontrol et
    sql_query = "SELECT * FROM Admins WHERE Username=? AND Password=?"
    cursor.execute(sql_query, (username, password_hash))
    admin = cursor.fetchone()

    return admin


@app.route('/admin_giris', methods=['GET', 'POST'])
def admin_giris():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = authenticate_admin(username, password)

        if admin:
            # Admin giriş yaptı, oturumu başlat
            session['admin_id'] = admin.AdminID
            flash('Admin login successful.', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Admin login failed. Check your username and password.', 'error')

    return render_template('admin_giris.html')

@app.route('/admin_logout')
def admin_logout():
    # Admin oturumunu sonlandır
    session.pop('admin_id', None)
    flash('Admin logout successful.', 'success')
    return redirect(url_for('admin_giris'))

@app.route('/admin_panel')
def admin_panel():
    # Admin oturumu kontrolü
    if 'admin_id' in session:
       
        return render_template('admin_panel.html')
    else:
        # Admin oturumu yoksa giriş sayfasına yönlendir
        flash('You need to log in as an admin first.', 'error')
        return redirect(url_for('admin_giris'))

def get_reviews_from_database():
    cursor.execute('SELECT * FROM Reviews')
    reviews = []

    for row in cursor.fetchall():
        review = {
            'ReviewID': row[0],
            'CustomerID': row[1],
            'ActivityID': row[2],
            'ReviewText': row[3],
            'Rating': row[4],
            'InstructorID': row[5],  # Eklenen satır
        }
        reviews.append(review)

    return reviews

def get_private_lessons_from_database():
    # SQL sorgusu
    sql_query = """
    SELECT
        pl.LessonID,
        pl.LessonDateTime,
        c.FirstName AS CustomerFirstName,
        c.LastName AS CustomerLastName,
        i.FirstName AS InstructorFirstName,
        i.LastName AS InstructorLastName,
        a.ActivityName
    FROM
        PrivateLessons pl
    JOIN
        Customers c ON pl.CustomerID = c.CustomerID
    JOIN
        Instructors i ON pl.InstructorID = i.InstructorID
    JOIN
        Activities a ON pl.ActivityID = a.ActivityID;
    """

    cursor.execute(sql_query)
    private_lessons = []

    for row in cursor.fetchall():
        private_lesson = {
            'LessonID': row[0],
            'LessonDateTime': row[1],
            'CustomerFirstName': row[2],
            'CustomerLastName': row[3],
            'InstructorFirstName': row[4],
            'InstructorLastName': row[5],
            'ActivityName': row[6],
        }
        private_lessons.append(private_lesson)

    return private_lessons

def get_customers_from_database():
    # MSSQL veritabanına bağlan
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    sql_query = """
    SELECT 
        c.CustomerID,
        c.FirstName as CustomerFirstName,
        c.LastName as CustomerLastName,
        c.UserName as CustomerUserName,
        c.Email,
        c.PhoneNumber,
        c.Gender,
        c.Address,
        c.MembershipStartDate,
        c.MembershipEndDate,
        a.ActivityName
    FROM Customers c
    JOIN Activities a ON c.ActivityID = a.ActivityID
    """
    
    cursor.execute(sql_query)
    customers = []

    for row in cursor.fetchall():
        customer = {
            'CustomerID': row[0],
            'FirstName': row[1],
            'LastName': row[2],
            'UserName': row[3],
            'Email': row[4],
            'PhoneNumber': row[5],
            'Gender': row[6],
            'Address': row[7],
            'MembershipStartDate': row[8],
            'MembershipEndDate': row[9],
            'ActivityName': row[10],
        }
        customers.append(customer)

    # Bağlantıyı ve cursor nesnesini kapat
    cursor.close()
    connection.close()

    return customers

# View all reviews with customer names
@app.route('/view_reviews')
def view_reviews():
    query = """
    SELECT 
        r.ReviewID, 
        c.FirstName + ' ' + c.LastName AS CustomerName, 
        a.ActivityName, 
        r.ReviewText, 
        r.Rating,
        i.FirstName + ' ' + i.LastName AS InstructorName
    FROM Reviews r
    JOIN Customers c ON r.CustomerID = c.CustomerID
    LEFT JOIN Activities a ON r.ActivityID = a.ActivityID
    LEFT JOIN Instructors i ON r.InstructorID = i.InstructorID
    """
    cursor.execute(query)
    reviews = cursor.fetchall()
    
    activity_reviews = [review for review in reviews if review.ActivityName is not None]
    instructor_reviews = [review for review in reviews if review.InstructorName is not None]
    general_reviews = [review for review in reviews if review.ActivityName is None and review.InstructorName is None]



    return render_template('view_reviews.html', activity_reviews=activity_reviews, instructor_reviews=instructor_reviews, general_reviews=general_reviews)

@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    try:
        # Review silme işlemleri burada gerçekleştirilecek
        cursor.execute("DELETE FROM Reviews WHERE ReviewID = ?", review_id)

        connection.commit()

        flash('Review deleted successfully!', 'success')
    except Exception as e:
        print(e)
        flash('Error occurred while deleting the review.', 'error')
    finally:
        return redirect(url_for('view_reviews'))

# Müşteri listesi görüntüleme
@app.route('/view_customers')
def view_customers():
    try:
        query = """
        SELECT c.CustomerID, c.FirstName + ' ' + c.LastName AS CustomerName, c.UserName, c.Email, c.PhoneNumber, c.Gender, c.Address, c.MembershipStartDate, c.MembershipEndDate
        FROM Customers c
        """
        cursor.execute(query)
        customers = cursor.fetchall()
        return render_template('view_customers.html', customers=customers)

    except pyodbc.Error as ex:
        print("Hata:", ex)
        flash('An error occurred while fetching customers!', 'error')
        return render_template('view_customers.html')

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        user_name = request.form['user_name']
        password = request.form['password']
        email = request.form['email']
        phone_number = request.form['phone_number']
        gender = request.form['gender']
        address = request.form['address']
        membership_start_date = request.form['membership_start_date']
        membership_end_date = request.form['membership_end_date']

        insert_query = """
        INSERT INTO Customers (FirstName, LastName, UserName, Password, Email, PhoneNumber, Gender, Address, MembershipStartDate, MembershipEndDate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query, (first_name, last_name, user_name, password, email, phone_number, gender, address, membership_start_date, membership_end_date))
        connection.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('view_customers'))

    return render_template('add_customer.html')

# Admin Customers - Update
@app.route('/update_customer/<int:customer_id>', methods=['GET', 'POST'])
def update_customer(customer_id):
    query = """
    SELECT CustomerID, FirstName, LastName, UserName, Password, Email, PhoneNumber, Gender, Address, MembershipStartDate, MembershipEndDate
    FROM Customers
    WHERE CustomerID = ?
    """
    cursor.execute(query, customer_id)
    customer = cursor.fetchone()

    if customer is None:
        flash('Customer not found!', 'error')
        return redirect(url_for('view_customers'))

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        user_name = request.form['user_name']
        password = request.form['password']
        email = request.form['email']
        phone_number = request.form['phone_number']
        gender = request.form['gender']
        address = request.form['address']
        membership_start_date = request.form['membership_start_date']
        membership_end_date = request.form['membership_end_date']

        update_query = """
        UPDATE Customers
        SET FirstName=?, LastName=?, UserName=?, Password=?, Email=?, PhoneNumber=?, Gender=?, Address=?, MembershipStartDate=?, MembershipEndDate=?
        WHERE CustomerID=?
        """
        cursor.execute(update_query, (first_name, last_name, user_name, password, email, phone_number, gender, address, membership_start_date, membership_end_date, customer_id))
        connection.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('view_customers'))

    return render_template('update_customer.html', customer=customer)

@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    try:
        # Delete related records in PaymentPlans table
        delete_payment_query = "DELETE FROM PaymentPlans WHERE CustomerID = ?"
        cursor.execute(delete_payment_query, customer_id)
        connection.commit()

        # Now, delete the customer from the Customers table
        delete_customer_query = "DELETE FROM Customers WHERE CustomerID = ?"
        cursor.execute(delete_customer_query, customer_id)
        connection.commit()

        flash('Customer deleted successfully!', 'success')
        return redirect(url_for('view_customers'))

    except pyodbc.IntegrityError as e:
        # Handle the IntegrityError, perhaps by displaying an error message or redirecting
        flash('Error deleting customer. There are related records in PaymentPlans table.', 'error')
        return redirect(url_for('view_customers'))

# View all activities
@app.route('/view_activities')
def view_activities():
    query = """
    SELECT a.ActivityID, a.ActivityName, a.Description, i.FirstName + ' ' + i.LastName AS InstructorName,
           a.photo_path, a.ActivityDay, a.DetailedDescription, a.ActivityTime
    FROM Activities a
    JOIN Instructors i ON a.InstructorID = i.InstructorID
    """
    cursor.execute(query)
    activities = cursor.fetchall()
    return render_template('view_activities.html', activities=activities)

# Admin Activities - Add
@app.route('/add_activity', methods=['GET', 'POST'])
def add_activity():
    if request.method == 'POST':
        try:
            # Form verilerini al
            activity_name = request.form['activity_name']
            description = request.form['description']
            instructor_id = request.form['instructor_id']
            activity_day = request.form['activity_day']
            detailed_description = request.form['detailed_description']
            activity_time = request.form['activity_time']

            # Veritabanına ekle
            insert_query = """
            INSERT INTO Activities (ActivityName, Description, InstructorID, ActivityDay, DetailedDescription, ActivityTime)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, activity_name, description, instructor_id, activity_day, detailed_description, activity_time)
            connection.commit()

            flash('Activity added successfully!', 'success')
            return redirect(url_for('view_activities'))

        except pyodbc.Error as ex:
            print("Hata:", ex)
            flash('An error occurred while adding the activity!', 'error')
            return render_template('add_activity.html')

    # Instructors' list for dropdown
    instructors_query = "SELECT InstructorID, FirstName + ' ' + LastName AS InstructorName FROM Instructors"
    cursor.execute(instructors_query)
    instructors = cursor.fetchall()

    return render_template('add_activity.html', instructors=instructors)

# Admin Activities - Update
@app.route('/update_activity/<int:activity_id>', methods=['GET', 'POST'])
def update_activity(activity_id):
    try:
        # Etkinlik verisini al
        query = """
        SELECT a.ActivityID, a.ActivityName, a.Description, i.FirstName + ' ' + i.LastName AS InstructorName,
               a.ActivityDay, a.DetailedDescription, a.ActivityTime
        FROM Activities a
        JOIN Instructors i ON a.InstructorID = i.InstructorID
        WHERE a.ActivityID = ?
        """
        cursor.execute(query, activity_id)
        activity = cursor.fetchone()

        if activity is None:
            flash('Activity not found!', 'error')
            return redirect(url_for('view_activities'))

        if request.method == 'POST':
            # Güncellenmiş form verilerini al
            activity_name = request.form['activity_name']
            description = request.form['description']
            instructor_id = request.form['instructor_id']
            activity_day = request.form['activity_day']
            detailed_description = request.form['detailed_description']
            activity_time = request.form['activity_time']

            # Veritabanını güncelle
            update_query = """
            UPDATE Activities
            SET ActivityName=?, Description=?, InstructorID=?, ActivityDay=?, DetailedDescription=?, ActivityTime=?
            WHERE ActivityID=?
            """
            cursor.execute(update_query, activity_name, description, instructor_id, activity_day, detailed_description, activity_time, activity_id)
            connection.commit()

            flash('Activity updated successfully!', 'success')
            return redirect(url_for('view_activities'))

    except pyodbc.Error as ex:
        print("Hata:", ex)
        flash('An error occurred while updating the activity!', 'error')
        return render_template('update_activity.html', activity=activity)

    # Instructors' list for dropdown
    instructors_query = "SELECT InstructorID, FirstName + ' ' + LastName AS InstructorName FROM Instructors"
    cursor.execute(instructors_query)
    instructors = cursor.fetchall()

    return render_template('update_activity.html', activity=activity, instructors=instructors)

# Admin Activities - Delete
@app.route('/delete_activity/<int:activity_id>', methods=['POST'])
def delete_activity(activity_id):
    delete_query = "DELETE FROM Activities WHERE ActivityID = ?"
    cursor.execute(delete_query, activity_id)
    connection.commit()
    flash('Activity deleted successfully!', 'success')
    return redirect(url_for('view_activities'))

# View all instructors
@app.route('/view_instructors')
def view_instructors():
    query = """
    SELECT InstructorID, FirstName, LastName, PhoneNumber, Email, Gender
    FROM Instructors
    """
    cursor.execute(query)
    instructors = cursor.fetchall()
    return render_template('view_instructors.html', instructors=instructors)

# Admin Instructors - Add
@app.route('/add_instructor', methods=['GET', 'POST'])
def add_instructor():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        gender = request.form['gender']

        insert_query = """
        INSERT INTO Instructors (FirstName, LastName, PhoneNumber, Email, Gender)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query, first_name, last_name, phone_number, email, gender)
        connection.commit()
        flash('Instructor added successfully!', 'success')
        return redirect(url_for('view_instructors'))

    return render_template('add_instructor.html')

# Admin Instructors - Update
@app.route('/update_instructor/<int:instructor_id>', methods=['GET', 'POST'])
def update_instructor(instructor_id):
    query = """
    SELECT InstructorID, FirstName, LastName, PhoneNumber, Email, Gender
    FROM Instructors
    WHERE InstructorID = ?
    """
    cursor.execute(query, instructor_id)
    instructor = cursor.fetchone()

    if instructor is None:
        flash('Instructor not found!', 'error')
        return redirect(url_for('view_instructors'))

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        gender = request.form['gender']

        update_query = """
        UPDATE Instructors
        SET FirstName=?, LastName=?, PhoneNumber=?, Email=?, Gender=?
        WHERE InstructorID=?
        """
        cursor.execute(update_query, first_name, last_name, phone_number, email, gender, instructor_id)
        connection.commit()
        flash('Instructor updated successfully!', 'success')
        return redirect(url_for('view_instructors'))

    return render_template('update_instructor.html', instructor=instructor)

# Admin Instructors - Delete
@app.route('/delete_instructor/<int:instructor_id>', methods=['POST'])
def delete_instructor(instructor_id):
    delete_query = "DELETE FROM Instructors WHERE InstructorID = ?"
    cursor.execute(delete_query, instructor_id)
    connection.commit()
    flash('Instructor deleted successfully!', 'success')
    return redirect(url_for('view_instructors'))

def update_private_lesson_by_id(lesson_id, updated_data):
    try:
        # Güncelleme sorgusu
        update_query = """
        UPDATE PrivateLessons
        SET LessonDateTime = ?
        WHERE LessonID = ?
        """

        # Güncelleme işlemi
        cursor.execute(update_query, updated_data.get('LessonDateTime'), lesson_id)
        connection.commit()

        flash('Private Lesson updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating Private Lesson: {str(e)}', 'error')

# Delete Private Lesson by ID
def delete_private_lesson_by_id(lesson_id):
    try:
        # Silme sorgusu
        delete_query = "DELETE FROM PrivateLessons WHERE LessonID = ?"

        # Silme işlemi
        cursor.execute(delete_query, lesson_id)
        connection.commit()

        flash('Private Lesson deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting Private Lesson: {str(e)}', 'error')

@app.route('/admin_ozel_ders')
def admin_ozel_ders():
    # Admin oturumu kontrolü
    if 'admin_id' in session:
        # Assuming you have functions to fetch data from the database
        private_lessons = get_private_lessons_from_database()

        admin_id = session['admin_id']

        # Admin özel ders panelini görüntüle
        return render_template('admin_ozel_ders.html', admin_id=admin_id, private_lessons=private_lessons)
    else:
        # Admin oturumu yoksa giriş sayfasına yönlendir
        flash('You need to log in as an admin first.', 'error')
        return redirect(url_for('admin_giris'))

@app.route('/update_private_lesson/<int:lesson_id>', methods=['GET', 'POST'])
def update_private_lesson(lesson_id):
    if request.method == 'POST':
        updated_data = {
            'LessonDateTime': request.form['lesson_datetime'],
            # Diğer güncellenecek alanları buraya ekleyin
        }
        update_private_lesson_by_id(lesson_id, updated_data)
        return redirect(url_for('admin_panel'))

    # Private Lesson'ı al
    lesson_query = "SELECT * FROM PrivateLessons WHERE LessonID = ?"
    lesson = cursor.execute(lesson_query, lesson_id).fetchone()

    return render_template('update_private_lesson.html', lesson=lesson)

@app.route('/delete_private_lesson/<int:lesson_id>', methods=['POST'])
def delete_private_lesson(lesson_id):
    delete_private_lesson_by_id(lesson_id)
    return redirect(url_for('admin_panel'))

@app.route('/admin_aktiviteler', methods=['GET', 'POST'])
def admin_aktiviteler():
    if request.method == 'POST':
        activity_name = request.form.get('activity_name')

        if not activity_name:
            flash('Invalid request', 'error')
            return redirect(url_for('admin_aktiviteler'))

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(url_for('admin_aktiviteler'))

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')

            file.save(file_path)

            # Update the photo_path of the activity
            cursor.execute('UPDATE Activities SET photo_path = ? WHERE ActivityName = ?', (file_path, activity_name))
            connection.commit()

            flash('Photo updated successfully', 'success')

    # Get the list of activities from the database
    activities = get_activities_from_database()

    return render_template('admin_aktiviteler.html', activities=activities)

@app.route('/membership_plans', methods=['GET', 'POST'])
def view_membership_plans():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('uye_giris'))

    # Fetch membership plans from the database
    cursor.execute('SELECT * FROM MembershipPlans')
    plans = cursor.fetchall()

    # Convert the result to a list of dictionaries
    plans_list = []
    for plan in plans:
        plan_dict = {
            'MembershipPlanID': plan.MembershipPlanID,
            'MembershipType': plan.MembershipType,
            'PlanDescription': plan.PlanDescription,
            'ActivityAccess': plan.ActivityAccess,
            'PrivateLessonAccess': plan.PrivateLessonAccess,
            'Price': plan.Price,
        }
        plans_list.append(plan_dict)

    return render_template('membership_plans.html', membership_plans=plans_list)

# Endpoint to purchase or renew a membership plan
@app.route('/purchase_membership', methods=['POST'])
def purchase_membership():
    if 'user_id' not in session:
        return redirect(url_for('uye_giris'))  # Redirect to the login page or another appropriate page

    # Extract data from the form submission
    plan_id = request.form.get('plan_id')
    duration_months = int(request.form.get('duration_months'))
    customer_id = session['user_id']

    # Fetch plan details from the database
    cursor.execute('SELECT * FROM MembershipPlans WHERE MembershipPlanID = ?', (plan_id,))
    plan_row = cursor.fetchone()

    if plan_row:
        # Access the fields using the correct indices
        plan = {
            'MembershipPlanID': plan_row[0],
            'MembershipType': plan_row[1],
            'PlanDescription': plan_row[2],
            'ActivityAccess': plan_row[3],
            'PrivateLessonAccess': plan_row[4],
            'Price': plan_row[5],
        }

        # Check if the customer has an expired membership
        cursor.execute('SELECT MembershipEndDate FROM Customers WHERE CustomerID = ?', (customer_id,))
        end_date_row = cursor.fetchone()

        current_date = datetime.now().date()

        # Check if the customer has no previous membership
        if not end_date_row:
            end_date = None
        else:
            end_date = end_date_row[0]

        # Check if the membership is expired or there is no previous membership
        if not end_date or current_date > datetime.strptime(end_date, '%Y-%m-%d').date():
            # Calculate total fee based on the selected duration
            bonus_months = 0

            if duration_months == 1:
                total_fee = plan['Price']
            elif duration_months == 6:
                total_fee = 6 * plan['Price']
                bonus_months = 1
            elif duration_months == 12:
                total_fee = 12 * plan['Price']
                bonus_months = 3
            else:
                flash('Invalid duration selected.', 'error')
                return redirect(url_for('membership_plans'))

            # Insert into PaymentPlans table
            cursor.execute(
                'INSERT INTO PaymentPlans (PlanName, Fee, DurationInMonths, MembershipPlanID, CustomerID) VALUES (?, ?, ?, ?, ?)',
                (plan['MembershipType'], total_fee, duration_months + bonus_months, plan_id, customer_id)
            )
            connection.commit()

            # Update MembershipStartDate and MembershipEndDate in Customers table
            start_date = current_date.strftime('%Y-%m-%d')
            new_end_date = (current_date + timedelta(days=30 * (duration_months + bonus_months))).strftime('%Y-%m-%d')

            cursor.execute(
                'UPDATE Customers SET MembershipStartDate = ?, MembershipEndDate = ? WHERE CustomerID = ?',
                (start_date, new_end_date, customer_id)
            )
            connection.commit()

            flash('Membership purchased successfully!', 'success')
            return redirect(url_for('view_membership_details'))
        else:
            flash('Cannot purchase or renew. Current membership is still active.', 'error')
    else:
        flash('Invalid plan ID', 'error')
        
    return redirect(url_for('view_membership_plans'))

@app.route('/cancel_membership', methods=['POST'])
def cancel_membership():
    if 'user_id' not in session:
        return jsonify({'error': 'Please login to cancel your membership.'})

    # Kullanıcının id'sini al
    customer_id = session['user_id']

    # Kullanıcının mevcut üyelik bilgilerini al
    cursor.execute('SELECT MembershipEndDate FROM Customers WHERE CustomerID = ?', (customer_id,))
    end_date_row = cursor.fetchone()

    if end_date_row:
        end_date = end_date_row[0]

        # Eğer mevcut üyelik tarihi geçerli ise, üyeliği iptal et
        current_date = datetime.now().date()
        if current_date <= datetime.strptime(end_date, '%Y-%m-%d').date():
            # PaymentPlans tablosundan ilgili üyelik bilgisini sil
            cursor.execute('DELETE FROM PaymentPlans WHERE CustomerID = ?', (customer_id,))
            connection.commit()

            # Customers tablosunu güncelle, üyeliği iptal et
            cursor.execute('UPDATE Customers SET MembershipEndDate = NULL WHERE CustomerID = ?', (customer_id,))
            connection.commit()

            flash('Membership canceled successfully!', 'success')
            return redirect(url_for('customer_profile'))  # Assuming you have a dashboard route, adjust accordingly
        else:
            flash('Cannot cancel. Current membership has already expired.', 'error')
            return redirect(url_for('membership_details'))  # Redirect to the appropriate route
    else:
        flash('No active membership found for the user.', 'error')
        return redirect(url_for('membership_details'))


@app.route('/membership_details', methods=['GET'])
def view_membership_details():
    if 'user_id' not in session:
        flash('Please login to view your membership details.', 'error')
        return redirect(url_for('uye_giris'))

    customer_id = session['user_id']

    # Fetch customer details from the database
    cursor.execute('SELECT * FROM Customers WHERE CustomerID = ?', (customer_id,))
    customer_row = cursor.fetchone()

    if customer_row:
        customer = {
            'CustomerID': customer_row[0],
            'FirstName': customer_row[1],
            'LastName': customer_row[2],
            'UserName': customer_row[3],
            'MembershipStartDate': customer_row[9],
            'MembershipEndDate': customer_row[10],
        }

        # Check if MembershipEndDate is not None before parsing
        if customer['MembershipEndDate'] is not None:
            try:
                end_date = datetime.strptime(customer['MembershipEndDate'], '%Y-%m-%d').date()
            except ValueError:
                # Handle the case where MembershipEndDate is not in the expected format
                flash('Error: MembershipEndDate is not in the expected format.', 'error')
                return redirect(url_for('some_error_page'))

            # Calculate the remaining days in the membership
            current_date = datetime.now().date()
            remaining_days = (end_date - current_date).days

            # Fetch the latest payment details from the PaymentPlans table
            cursor.execute('SELECT TOP 1 * FROM PaymentPlans WHERE CustomerID = ?', (customer_id,))
            payment_row = cursor.fetchone()

            if payment_row:
                payment_info = {
                    'PlanName': payment_row[1],
                    'Fee': payment_row[2],
                    'DurationInMonths': payment_row[3],
                }

                # Fetch the price from the MembershipPlans table
                cursor.execute('SELECT Price FROM MembershipPlans WHERE MembershipPlanID = ?', (payment_row[4],))
                price_row = cursor.fetchone()

                if price_row:
                    price = price_row[0]
                    return render_template('membership_details.html', customer=customer, remaining_days=remaining_days,
                                           payment_info=payment_info, price=price)
                else:
                    flash('Error: Price information not found.', 'error')
            else:
                # Kullanıcının hiç ödeme bilgisi yoksa, purchase_membership sayfasına yönlendir
                return redirect(url_for('purchase_membership'))
        else:
            # Handle the case where MembershipEndDate is None
            flash('Error: MembershipEndDate is None.', 'error')
            return redirect(url_for('index'))
    else:
        flash('Customer not found.', 'error')

    return render_template('membership_details.html', customer=customer, remaining_days=remaining_days)

@app.route('/payments')
def payments():
    try:
        # Fetch data from the PaymentPlans table and join with Customers table
        cursor.execute('''
            SELECT 
                pp.PlanID, 
                pp.PlanName, 
                pp.Fee, 
                pp.DurationInMonths, 
                pp.MembershipPlanID, 
                pp.CustomerID,
                c.FirstName,
                c.LastName,
                c.Email
            FROM PaymentPlans pp
            JOIN Customers c ON pp.CustomerID = c.CustomerID
        ''')
        payment_plans = cursor.fetchall()

        # Fetch data from the MembershipPlans table
        cursor.execute('SELECT * FROM MembershipPlans')
        membership_plans = cursor.fetchall()

        return render_template('payments.html', payment_plans=payment_plans, membership_plans=membership_plans)
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/edit_payment_plan/<int:plan_id>', methods=['GET', 'POST'])
def edit_payment_plan(plan_id):
    # Fetch the payment plan details for the selected PlanID
    cursor.execute('SELECT * FROM paymentplans WHERE PlanID = ?', plan_id)
    payment_plan = cursor.fetchone()

    if request.method == 'POST':
        # Update the payment plan details in the database
        form_data = request.form
        cursor.execute('''
            UPDATE paymentplans
            SET PlanName = ?, Fee = ?, DurationInMonths = ?, MembershipPlanID = ?, CustomerID = ?
            WHERE PlanID = ?
        ''', form_data['plan_name'], form_data['fee'], form_data['duration_in_months'],
           form_data['membership_plan_id'], form_data['customer_id'], plan_id)

        connection.commit()

        return redirect(url_for('index'))

    return render_template('edit_payment_plan.html', payment_plan=payment_plan)

@app.route('/edit_membership_plan/<int:membership_plan_id>', methods=['GET', 'POST'])
def edit_membership_plan(membership_plan_id):
    # Fetch the membership plan details for the selected MembershipPlanID
    cursor.execute('SELECT * FROM MembershipPlans WHERE MembershipPlanID = ?', membership_plan_id)
    membership_plan = cursor.fetchone()

    if request.method == 'POST':
        # Update the membership plan details in the database
        form_data = request.form
        cursor.execute('''
            UPDATE MembershipPlans
            SET MembershipType = ?, PlanDescription = ?, ActivityAccess = ?, PrivateLessonAccess = ?, Price = ?
            WHERE MembershipPlanID = ?
        ''', form_data['membership_type'], form_data['plan_description'], form_data['activity_access'],
           form_data['private_lesson_access'], form_data['price'], membership_plan_id)

        connection.commit()

        return redirect(url_for('index'))

    return render_template('edit_membership_plan.html', membership_plan=membership_plan)


if __name__ == '__main__':
    app.run(debug=True)
    cursor.close()
    connection.close()