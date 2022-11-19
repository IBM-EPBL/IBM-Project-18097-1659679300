from flask import Flask, render_template, redirect, url_for, request, flash, escape, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField
from wtforms.validators import InputRequired, Length, Email, EqualTo
import ibm_db
import time
import openapi_client
from com.spoonacular import misc_api
from openapi_client.model.image_analysis_by_url200_response import ImageAnalysisByURL200Response
from pprint import pprint
from flask import Flask,redirect,url_for,render_template,request
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import json
import os
from dotenv import load_dotenv

load_dotenv()
COS_ENDPOINT="https://s3.jp-tok.cloud-object-storage.appdomain.cloud"
COS_API_KEY_ID= os.getenv("COSAPI")
COS_INSTANCE_CRN= os.getenv("COSINSTANCE")

# Create resource https://s3.ap.cloud-object-storage.appdomain.cloud
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)




DB_HOSTNAME = os.getenv("DB_HOSTNAME")
DB_PORT = os.getenv("DB_PORT")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASS")

conn = ibm_db.connect(f"DATABASE=bludb;HOSTNAME={DB_HOSTNAME};PORT={DB_PORT};SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID={DB_USERNAME};PWD={DB_PASS}",'','')
print(conn)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECERT_KEY")

class LoginForm(FlaskForm):
    email = EmailField("email", validators=[InputRequired("Email is required"), Email()])
    password = PasswordField("password", validators=[InputRequired("Password is required")])

class RegisterForm(FlaskForm):
    username = StringField("username", validators=[InputRequired("Username is required")])
    email = EmailField("email", validators=[InputRequired("Email is required"), Email()])
    pass1 = PasswordField("pass1", validators=[InputRequired("Password is required"), EqualTo('pass2', message="Passwords must match"), Length(min=4, max=30, message="Length must be between 4 and 30")])
    pass2 = PasswordField("pass2")

class ForgetPassword(FlaskForm):
    email = EmailField("email", validators=[InputRequired("Email is required"), Email()])

@app.route("/")
def home():
    username = request.cookies.get('username')
    return render_template("home.html", username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if request.method=='POST' and form.validate_on_submit():
        email = request.form['email']
        password = request.form['password']
        sql = f"SELECT * FROM user WHERE EMAIL='{escape(email)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        dic = ibm_db.fetch_both(stmt)
        if not dic or password != dic['PASSWORD']:
            flash("Incorrect email or password", "error")
            return redirect(url_for('login'))

        session['username'] =  dic['USERNAME']
        return redirect(url_for('home'))
    else:
        return render_template("login.html", form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()

    if request.method=='POST' and form.validate_on_submit():
        username = request.form['username']
        email = request.form['email']
        pass1 = request.form['pass1']
        sql = f"SELECT * FROM user WHERE EMAIL='{escape(email)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        dic = ibm_db.fetch_both(stmt)
        if dic:
            flash("User with the email already exist", "error")
            return redirect(url_for('login'))
        sql = "INSERT INTO user(username,email,password) VALUES (?, ?, ?)"
        prep_stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(prep_stmt, 1, username)
        ibm_db.bind_param(prep_stmt, 2, email)
        ibm_db.bind_param(prep_stmt, 3, pass1)
        ibm_db.execute(prep_stmt)
        flash("Registration Successful", "success")
        response = redirect('/login',307)
        return response
    else:
        return render_template("register.html", form=form)

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    form = ForgetPassword()
    if request.method=='POST' and form.validate_on_submit():
        email = request.form['email']
        sql = f"SELECT * FROM user WHERE EMAIL='{escape(email)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        dic = ibm_db.fetch_both(stmt)
        if dic:
            flash("Email has been sent if user exist", "success")
            return redirect(url_for('forgot_password'))
        
        return render_template("forgot_password.html", form=form)

    return render_template("forgot_password.html", form=form)
    
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username')
    return redirect(url_for('home'))




@app.route('/pictures')
def index():
    files = get_bucket_contents('flask-app-2k22')
    return render_template('index.html', files = files)

	




 
def nutitionapi(imagelink,image_id):
    configuration = openapi_client.Configuration(
        host = "https://api.spoonacular.com"
    )
    configuration.api_key['apiKeyScheme'] = os.getenv("NUTRITIONAPI")

    with openapi_client.ApiClient(configuration) as api_client:
        api_instance = misc_api.MiscApi(api_client)
        image_url =imagelink
    try:
        api_response = api_instance.image_analysis_by_url(image_url)
        pprint(api_response)
        y =api_response
        cal= y["nutrition"]["calories"]["value"]
        print(cal)
        Carb= y["nutrition"]["carbs"]["value"]
        fat= y["nutrition"]["fat"]["value"]
        protein= y["nutrition"]["protein"]["value"]
        name=y["category"]["name"]
        image=image_id["ID"]
        sql = f"INSERT INTO nutritiondetails1(calories,carbs,fat,protein,ref_id,name) VALUES('{escape(cal)}','{escape(Carb)}','{escape(fat)}','{escape(protein)}','{escape(image)}','{escape(name)}')"
        
        prep_stmt = ibm_db.prepare(conn, sql)

        ibm_db.execute(prep_stmt)
        flash("Successful db operation", "success")
        
    except openapi_client.ApiException as e:
        print("Exception when calling MiscApi->image_analysis_by_url: %s\n" % e) 


@app.route('/foodinfo', methods = ['GET', 'POST'])
def test():
    sql = f"SELECT * FROM imagedetails "
    stmt = ibm_db.exec_immediate(conn, sql)
    pic = ibm_db.fetch_both(stmt)
    pics=[]
    while pic != False:
     x=[pic["IMG_LINK"],pic["ID"]]   
     pics.append(x)
     print(pic)
     pic = ibm_db.fetch_both(stmt)
     print(pics)
    return render_template('index.html', files = pics)



@app.route('/nutritioninfo/<id>', methods = ['GET', 'POST'])
def test1(id):
    print(id)
    sql = f"SELECT * FROM nutritiondetails1,imagedetails where nutritiondetails1.ref_id=imagedetails.id and ref_id='{escape(id)}'"
    stmt = ibm_db.exec_immediate(conn, sql)
    pic = ibm_db.fetch_both(stmt)
    
    print(pic)
    return render_template('foodinfo.html', files = pic)


        


if __name__ == '__main__':
    app.run(debug=True)