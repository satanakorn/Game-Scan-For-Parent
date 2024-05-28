from asyncio.windows_events import NULL
import os
from re import I
import sqlite3 as sql
from sre_constants import SUCCESS
from turtle import title
from xml.etree.ElementTree import tostring
from flask import Flask, render_template, redirect, url_for, request,g ,session, flash
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import uuid #for create token new add by owen พี่เปาเพิ่ม กอลลั่ม ชื่อว่า token ให้หน่อยนะครับ 
import re
from helper import admin_required, login_required

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

con = sql.connect('./db/data.db')

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, '_database'):
        g.sqlite_db.close()

#article menu
def menuArticle():
    con = sql.connect('./db/data.db')
    db = con.cursor()
    articles = db.execute("SELECT title FROM articles")
    articles = db.fetchall()
    con.close
    return articles


#home page
@app.route("/")
def index():
    con = sql.connect('./db/data.db')
    db = con.cursor()
    raw_reviews_new = []
    raw_reviews_new = db.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT 5").fetchall()
    reviews_new = getReviewCard(raw_reviews_new)

    trend_id = db.execute("SELECT id FROM scores ORDER BY player_score DESC LIMIT 5").fetchall()
    raw_reviews_trend = []
    for i in range(5):
        raw_reviews_trend.append(db.execute("SELECT * FROM reviews WHERE id = {0}".format(trend_id[i][0])).fetchone())
    reviews_trend = getReviewCard(raw_reviews_trend)

    top_id = db.execute("SELECT id FROM scores ORDER BY review_score DESC LIMIT 5").fetchall()
    raw_reviews_top = []
    for i in range(5):
        raw_reviews_top.append(db.execute("SELECT * FROM reviews WHERE id = {0}".format(top_id[i][0])).fetchone())
    reviews_top = getReviewCard(raw_reviews_top)
    
    articles_title = menuArticle()
    return render_template("index.html", articles_title=articles_title,reviews_new=reviews_new, reviews_trend=reviews_trend, reviews_top=reviews_top)

def getReviewCard(raw_reviews):
    con = sql.connect('./db/data.db')
    db = con.cursor()
    reviews = []
    for each in raw_reviews:
        review = []
        cover = db.execute("SELECT cover FROM review_pics WHERE id=?", (each[0],)).fetchone()
        review.append(cover)
        review.append(each[1])
        desc = (each[3][:85] + '...') if len(each[3]) > 85 else each[3]
        review.append(desc)
        raw_scores = db.execute("SELECT * FROM scores WHERE id=?", (each[0],)).fetchall()[0]
        admin_score = raw_scores[1]
        ribbons = db.execute("SELECT * FROM ribbons WHERE id=?", (each[0],)).fetchall()[0]
        if(raw_scores[2] is not None):
            parent_score = raw_scores[2]
        else:
            parent_score = 0
        if(raw_scores[4] is not None):
            parent_score_negative = raw_scores[4]
        else:
            parent_score_negative = 0
        if(raw_scores[3] is not None):
            player_score = raw_scores[3]
        else:
            player_score = 0
        if(raw_scores[5] is not None):
            player_score_negative = raw_scores[5]
        else:
            player_score_negative = 0
        parent_vote = parent_score+parent_score_negative
        player_vote = player_score+player_score_negative
        try:
            percent_parent = '{:.1f}'.format(parent_score/(parent_vote)*100)
        except:
            percent_parent = "N/A"
        try:
            percent_player = '{:.1f}'.format(player_score/(player_vote)*100)
        except:
            percent_player = "N/A"
        scores = [admin_score,percent_parent,parent_vote,percent_player,player_vote]
        review.append(scores)
        if(ribbons[5] == 1):
            review.append('Not Approved')
        elif(ribbons[2] == 1):
            review.append('recommended')
        elif(ribbons[1] == 1):
            review.append('Approved')
        ## After All done ##
        reviews.append(review)
    con.close()
    return reviews

@app.route("/logout")
def logout():
    session['username'] = None
    articles_title = menuArticle()
    return render_template("login.html", articles_title=articles_title)
    

#Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return render_template('login.html', messgae = 'กรุณากรอกชื่อผู้ใช้')
        elif not request.form.get("password"):
            return render_template('login.html', messgae = 'กรุณากรอกรหัสผ่าน')
        con = sql.connect('./db/data.db')
        db = con.cursor()
        rows = db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"), ))
        rows = db.fetchall()
        user = rows[0]
        #print(rows)
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return render_template('login.html', messgae = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
        con.close()
        session['username'] = request.form.get('username')
        session['id_type'] = user[3]
        return redirect("/")
    else:
        articles_title = menuArticle()
        return render_template("login.html", articles_title=articles_title)
        
#Registration page
@app.route("/register", methods=['GET', 'POST'])
def register():
    message = ''  # Define the message variable
    if request.method == "POST":
        u_name = request.form.get('username')
        pw = request.form.get('password')
        c_pw = request.form.get('confirm_password')
        email = request.form.get('email')
        id_type = request.form.get('id_type')
        Fu_name = request.form.get('full_name')
        
        # Check if username or email already exists
        con = sql.connect('./db/data.db')
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (u_name, email))
        existing_user = cur.fetchone()
        con.close()

        if existing_user:
            message =  "ชื่อผู้ใช้หรืออีเมลนี้มีอยู่แล้ว"

        if not u_name: 
            message = "กรุณากรอกชื่อผู้ใช้"
        elif not pw:
            message = "กรุณากรอกรหัสผ่าน"
        elif not c_pw:
            message = "กรุณากรอกยืนยันรหัสผ่าน"
        elif not email: 
            message = "กรุณากรอกอีเมล"
        elif not Fu_name:
            message = "กรุณากรอกชื่อ-นามสกุล"
        elif not id_type:
            message = "กรุณากรอกประเภทผู้ใช้"
        elif '@' not in email:
            message = "อีเมลไม่ถูกต้อง"    
        elif pw != c_pw:
            message = "รหัสผ่านไม่ตรงกัน"
        elif not re.match("^[a-zA-Zก-๏\s]+$", Fu_name): 
            message = "ชื่อ-นามสกุลสามารถมีได้เฉพาะตัวอักษรไทยและอักษรภาษาอังกฤษเท่านั้น"

        elif len(pw) and len(c_pw) > 6:
            message = "รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัว"
        
        else:
            pass_hash = generate_password_hash(pw)

            try:
                que = "INSERT INTO users (username, email, password, id_type, fullname) VALUES (?, ?, ?, ?, ?) "
                con = sql.connect('./db/data.db')
                db = con.cursor()
                db.execute(que, (u_name, email, pass_hash, id_type, Fu_name))
                con.commit()
                con.close()
                return redirect('/login')
            except:
                message = "มีชื่อผู้ใช้อยู่แล้ว"
                pass_hash = ''  # Initialize pass_hash here
    
    day = list(range(1, 32))
    month = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    year = list(range(2466, 2566))
    return render_template("register.html", d=day, m=month, y=year, message=message)


# forgotpassword page new add
@app.route("/forgot_password")
def forgot_password():
    
    
    articles_title = menuArticle()
    return render_template('forgot_password.html',  articles_title=articles_title)

#reset password page new add
@app.route("/reset_password/<username>", methods=['POST','GET'])
def reset_password(username):
    if request.method == "POST":
        old_p = request.form.get('old_password')
        new_p = request.form.get('new_password')
        c_new_p = request.form.get('confirm_new_password')
        print(old_p)
        print(new_p)
        print(c_new_p)
        
        if new_p != c_new_p:
            return "password not match again"
        
        new_p = generate_password_hash(new_p)
        
        cur = sql.connect('./db/data.db')
        result = cur.execute("SELECT * FROM users WHERE username = ?", [username])
        print(result)
        if result > 0:
            user = cur.fetchone()
            pass_ = user['password']
            if generate_password_hash(pass_, old_p):
                cur = sql.connect('./db/data.db')
                cur.execute("UPDATE users SET password=? WHERE username = ?", (new_p, username))
                cur.commit()
                cur.close()
                return redirect('/reset_password')
            else:
                return "old password do not match"
    
    
    articles_title = menuArticle()
    return render_template('reset_password.html',  articles_title=articles_title)

@app.route("/profile")
def profile():
    '''if request.method == "POST":
        username = session.get('username')
        con = sql.connect('./db/data.db')
        cur = con.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = ?", [username])
        data = result.fetchone()
        con.close()'''
    articles_title = menuArticle()
    return render_template("profile.html", articles_title=articles_title,username = session.get('username'))
    

#สร้าง route เพิ่มครับ แก้ตรงนี้ครับพี่
''''@app.route("/update", methods=['POST'])
def update():
    if request.method == "POST":
        id_update = request.form.get('id')
        u_name = request.form.get('username')
        email = request.form.get('email')
        Fu_name = request.form.get('full_name')

        print(u_name)
        print(email)
        print(Fu_name)

        con = sql.connect('./db/data.db')
        with con:
            cursor = con.curosr()
            que = "UPDATE users SET username=?, email=?, fullname=? WHERE id=?"
            cursor.execute(que, (u_name, email, Fu_name, id_update))
            con.commit()
        con.close()
        return redirect(url_for('profile'))'''
         
        

@app.route("/search", methods=['GET', 'POST'])
def search():
    
    search = request.form.get('search')
        
    print(search)
    con = sql.connect('./db/data.db')
    db = con.cursor()
    raw_reviews = []
    if (search is None): 
        raw_reviews = db.execute("SELECT * FROM reviews ORDER BY name").fetchall()
    else:
        raw_reviews = db.execute("SELECT * FROM reviews WHERE name LIKE '%{0}%' ORDER BY name".format(search)).fetchall()
    reviews = getReviewCard(raw_reviews)


    con.close()
    if request.method == "POST":
        search = request.form.get('search')
        
        print(search)
        con = sql.connect('./db/data.db')
        db = con.cursor()
        raw_reviews = []
        if (search is None): 
            raw_reviews = db.execute("SELECT * FROM reviews ORDER BY name").fetchall()
        else:
            raw_reviews = db.execute("SELECT * FROM reviews WHERE name LIKE '%{0}%' ORDER BY name".format(search)).fetchall()
        reviews = reviews = getReviewCard(raw_reviews)
        articles_title = menuArticle()
        return render_template("search.html", articles_title=articles_title,reviews=reviews)
    articles_title = menuArticle()
    return render_template("search.html", articles_title=articles_title,reviews=reviews)

    print(count)

@app.route("/parentguide")
def guide():
    articles_title = menuArticle()
    return render_template("guide.html", articles_title=articles_title)

@app.route("/detail")
def detail():

    #just for test
    ribbons = ["approve","recommended","for_fun_only","for_family","not_for_kid","in_game_purchase"]
    genres = ["rpg","strategy","survival","adventure","action","arcade","multiplayer","sport","horror","moba","battle_royale","fighting","dialog","puzzle","shooting","sandbox"]
    skills = ["analysis","imagination","emotional","communication","teamwork","reaction","strategy","memory"]
    subjects = ["science","math","language","engineering","art","social","sport"]
    rates = ["3","7","12","16","18","!"]
    platforms = ["apple","android","pc","xbox","playstation","nintendo","others"]

    articles_title = menuArticle()
    return render_template("detail.html", articles_title=articles_title, ribbons=ribbons, genres=genres, skills=skills, subjects=subjects, rates=rates, platforms=platforms)

@app.route("/c_review", methods=['GET', 'POST'])
#@login_required
#@admin_required
def c_review():
    if request.method == "POST":
        # vvv get data vvv
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        review = request.form.get('review')
        suggestion = request.form.get('suggestion')
        score = request.form.get('score')
        rate = request.form.get('rate')
        cover = request.form.get('cover')
        pic1 = request.form.get('pic1')
        pic2 = request.form.get('pic2')
        pic3 = request.form.get('pic3')
        
        checkbox = ['ribbons','genres','skills','subjects','platforms']
        table_name = ["ribbons","genres","skills","subjects","platforms"]
        data = []
        for i in checkbox:
            data.append(request.form.getlist(i))
        ### check null
        if (title=="" or author=="" or description=="" or review=="" or suggestion=="" or score=="" or rate==""
                or cover=="" or pic1=="" or pic2=="" or pic3==""):
            return "cant regist review : please insert all box"
        ### Add to database ###
        con = sql.connect('./db/data.db')
        db = con.cursor()
        que = "INSERT INTO reviews (name, author, description, review, suggestion, rate) VALUES (?,?,?,?,?,?)"
        db.execute(que, (title, author, description, review, suggestion, rate))
        con.commit()
            
        t_id = db.execute("SELECT id FROM reviews WHERE name=?", (title,))
        t_id = db.fetchone()
        print("fetch id completed ",t_id)
        id = int(t_id[0])
        print(id)
            
        que = "INSERT INTO scores (id, review_score, parent_score, player_score, parent_score_negative, player_score_negative) VALUES (?,?,0,0,0,0)"
        db.execute(que, (id,score))
        con.commit()

        que = "INSERT INTO review_pics (id, cover, pic1, pic2, pic3) VALUES (?,?,?,?,?)"
        print("cover " + cover)
        print("pic1 " + pic1)
        print("pic2 " + pic2)
        print("pic3 " + pic3)
        db.execute(que, (id,cover,pic1,pic2,pic3))
        con.commit()

        i = 0
        for table in checkbox:         #'ribbons','genres','skills','subjects','platforms'
            temp_table = data[i]
            #print ("INSERT INTO {0} (id) VALUES ({1})".format(table_name[i],id),)
            que = "INSERT INTO {0} (id) VALUES ({1})"
            db.execute(que.format(table_name[i],id)) #stuck here
            con.commit()
            #print("insert row in "+ table_name[i] +" completed, id=",id)
                
            for item in temp_table:
                if(item is None):
                    print("dont have "+ table_name[i])
                else:
                    que = "UPDATE {0} SET {1} = 1 WHERE id={2}"
                    db.execute(que.format(table_name[i],item,id))
                    con.commit()
                    print("update "+ item + " of " + table_name[i] +" completed, id=",id)
            i += 1
        i = 0  
        con.close()
        print("All done.")
        url = "d_" + title
        return redirect(url)
        try:
            con = sql.connect('./db/data.db')
            db = con.cursor()
            que = "INSERT INTO reviews (name, author, description, review, suggestion, rate) VALUES (?,?,?,?,?,?)"
            db.execute(que, (title, author, description, review, suggestion, rate))
            con.commit()
            
            t_id = db.execute("SELECT id FROM reviews WHERE name=?", (title,))
            t_id = db.fetchone()
            print("fetch id completed ",t_id)
            id = int(t_id[0])
            print(id)
            
            que = "INSERT INTO scores (id, review_score) VALUES (?,?)"
            db.execute(que, (id,score))
            con.commit()

            que = "INSERT INTO review_pics (id, cover, pic1, pic2, pic3) VALUES (?,?,?,?,?)"
            print("cover " + cover)
            print("pic1 " + pic1)
            print("pic2 " + pic2)
            print("pic3 " + pic3)
            db.execute(que, (id,cover,pic1,pic2,pic3))
            con.commit()

            i = 0
            for table in checkbox:         #'ribbons','genres','skills','subjects','platforms'
                temp_table = data[i]
                #print ("INSERT INTO {0} (id) VALUES ({1})".format(table_name[i],id),)
                que = "INSERT INTO {0} (id) VALUES ({1})"
                db.execute(que.format(table_name[i],id)) #stuck here
                con.commit()
                #print("insert row in "+ table_name[i] +" completed, id=",id)
                
                for item in temp_table:
                    if(item is None):
                        print("dont have "+ table_name[i])
                    else:
                        que = "UPDATE {0} SET {1} = 1 WHERE id={2}"
                        db.execute(que.format(table_name[i],item,id))
                        con.commit()
                        print("update "+ item + " of " + table_name[i] +" completed, id=",id)
                i += 1
            i = 0  
            con.close()
            print("All done.")
            url = "d_" + title
            return redirect(url)
        except:
            return "cant regist review : some value conflict in database or this game has already reviewed."
    else:
        ribbons = ["approve","recommended","for_fun_only","for_family","not_for_kid","in_game_purchase"]
        genres = ["rpg","strategy","survival","adventure","action","arcade","multiplayer","sport","horror","moba","battle_royale","fighting","dialog","puzzle","shooting","sandbox"]
        skills = ["analysis","imagination","emotional","communication","teamwork","reaction","strategy","memory"]
        subjects = ["science","math","language","engineering","art","social","sport"]
        rates = ["3","7","12","16","18","!"]
        platforms = ["apple","android","pc","xbox","playstation","nintendo","others"]
        articles_title = menuArticle()
        return render_template("createreview.html", articles_title=articles_title, ribbons=ribbons, genres=genres, 
            skills=skills, subjects=subjects, rates=rates, platforms=platforms)


@app.route("/c_article", methods=['GET', 'POST'])
@login_required
@admin_required
def c_article():
    if request.method == "POST":
        title = request.form.get('title')
        content = request.form.get('content')
        try:
            que = "INSERT INTO articles (title, content) VALUES (?, ?) "
            con = sql.connect('./db/data.db')
            db = con.cursor()
            db.execute(que, (title, content))
            con.commit()
            con.close()
            print("prepare to redirect")
            url = "/a_" + title
            return redirect(url)
        except:
            return "#Username already existed"
    articles_title = menuArticle()
    return render_template("createarticle.html", articles_title=articles_title)

@app.route("/<url>", methods=['GET', 'POST'])
def requestData(url):
    articles_title = menuArticle()
    ### article ###
    if (url[0]=='a' and url[1]=='_'):
        title = url.replace('a_', '')
        con = sql.connect('./db/data.db')
        db = con.cursor()
        articles = db.execute("SELECT * FROM articles WHERE title=?", (title,))
        articles = db.fetchall()
        print(articles)
        if(articles!="" or articles is not None):
            article = articles[0]
        else:
            article = ["none","none","none","none","none","none","none"]
        con.close()

        return render_template("article.html", articles_title=articles_title, datas=article)
        ### detail ###
    elif (url[0]=='d' and url[1]=='_'):
        title = url.replace('d_','')
        con = sql.connect('./db/data.db')
        db = con.cursor()
        details = db.execute("SELECT * FROM reviews WHERE name=?", (title,)).fetchall()
        detail = details[0]

        id = detail[0]

        raw_scores = db.execute("SELECT * FROM scores WHERE id=?", (id,)).fetchall()[0]
        admin_score = raw_scores[1]
        if(raw_scores[2] is not None):
            parent_score = raw_scores[2]
        else:
            parent_score = 0
        if(raw_scores[4] is not None):
            parent_score_negative = raw_scores[4]
        else:
            parent_score_negative = 0
        if(raw_scores[3] is not None):
            player_score = raw_scores[3]
        else:
            player_score = 0
        if(raw_scores[5] is not None):
            player_score_negative = raw_scores[5]
        else:
            player_score_negative = 0
        parent_vote = parent_score+parent_score_negative
        player_vote = player_score+player_score_negative
        try:
            percent_parent = '{:.1f}'.format(parent_score/(parent_vote)*100)
        except:
            percent_parent = "N/A"
        try:
            percent_player = '{:.1f}'.format(player_score/(player_vote)*100)
        except:
            percent_player = "N/A"
        scores = [admin_score,percent_parent,parent_vote,percent_player,player_vote]
        
        raw_ribbons = db.execute("SELECT * FROM ribbons WHERE id=?", (id,)).fetchall()[0]
        ribbons_name = ["approve","recommended","for_fun_only","for_family","not_for_kid","in_game_purchase"]
        ribbons = []
        for i in range(1, len(raw_ribbons), 1):
            if(raw_ribbons[i]==1):
                ribbons.append(ribbons_name[i-1])

        raw_skills = db.execute("SELECT * FROM skills WHERE id=?", (id,)).fetchall()[0]
        skills_name = ["analysis","imagination","emotional","communication","teamwork","reaction","strategy","memory"]
        skills = []
        for i in range(1, len(raw_skills), 1):
            if(raw_skills[i]==1):
                skills.append(skills_name[i-1])

        raw_subjects = db.execute("SELECT * FROM subjects WHERE id=?", (id,)).fetchall()[0]
        subjects_name = ["science","math","language","engineering","art","social","sport"]
        subjects = []
        for i in range(1, len(raw_subjects), 1):
            if(raw_subjects[i]==1):
                subjects.append(subjects_name[i-1])

        raw_genres = db.execute("SELECT * FROM genres WHERE id=?", (id,)).fetchall()[0]
        genres_name = ["rpg","strategy","survival","adventure","action","arcade","multiplayer","sport","horror","moba","battle_royale","fighting","dialog","puzzle","shooting","sandbox"]
        genres = []
        for i in range(1, len(raw_genres), 1):
            if(raw_genres[i]==1):
                genres.append(genres_name[i-1])

        raw_platforms = db.execute("SELECT * FROM platforms WHERE id=?", (id,)).fetchall()[0]
        platforms_name = ["apple","android","pc","xbox","playstation","nintendo","others"]
        platforms = []
        for i in range(1, len(raw_platforms), 1):
            if(raw_platforms[i]==1):
                platforms.append(platforms_name[i-1])

        pictures = db.execute("SELECT * FROM review_pics WHERE id=?", (id,)).fetchall()[0]

        if request.method == "POST":
            votes = request.form['vote']
            print(votes)
            uid = 0
            if(session.get('username') is not None):
                uid = db.execute("SELECT id FROM users WHERE username=?",(format(session.get('username')),)).fetchone()[0]
                print("UID :",uid)
                print("reviewID :",id)
                rid = id
                #old_scores = db.execute("SELECT * FROM scores WHERE id=?",(id,)).fetchall[0]
                #negative_score = [old_scores[4],old_scores[5]] #get negative score
                check_votes = db.execute("SELECT * FROM votes WHERE uid={0} AND review_id={1}".format(uid,id)).fetchall()
                print("check_votes :",check_votes)
                
                if(check_votes != []):
                    check_vote = list(check_votes[0])
                    not_vote = check_vote[2]
                    vote_up = check_vote[3]
                    vote_down = check_vote[4]
                    if(votes == 'vote_up'):
                        if(vote_down==1): # old = vote down
                            vote_down = 0
                            vote_up = 1
                            updateScore(id, 1, -1)
                        elif(not_vote == 1): # new vote up
                            not_vote = 0
                            vote_up = 1
                            updateScore(id, 1, 0)
                        elif(vote_up == 1): # old = vote up
                            vote_up = 0
                            not_vote = 1
                            updateScore(id, -1, 0)

                    elif (votes == 'vote_down'):
                        if(vote_up==1): # old = vote up
                            vote_up = 0
                            vote_down = 1
                            updateScore(id, -1, 1)
                        elif(not_vote == 1): # new vote down
                            not_vote = 0
                            vote_down = 1
                            updateScore(id, 0, 1)
                        elif(vote_down == 1): # old = vote down
                            vote_down = 0
                            not_vote = 1
                            updateScore(id, 0, -1)

                    #print("check_vote2 :",check_vote)
                    
                    #print(not_vote,vote_up,vote_down, uid, id)
                    db.execute("UPDATE votes SET not_vote={0}, vote_up={1}, vote_down={2} WHERE uid={3} AND review_id={4}"
                        .format(not_vote,vote_up,vote_down, uid, rid))
                    con.commit()
                    
                else:
                    vote_up=0
                    vote_down=0
                    not_vote = 0
                    if(votes == 'vote_up'):
                        vote_up = 1
                        updateScore(id, 1, 0)
                    elif (votes == 'vote_down'):
                        vote_down = 1
                        updateScore(id, 0, 1)
                    db.execute("INSERT INTO votes (review_id, not_vote, vote_up, vote_down, uid) VALUES ({0},{1},{2},{3},{4})"
                        .format(rid,not_vote,vote_up,vote_down,uid))
                    con.commit()

            new_url = '/'+url
            return redirect(new_url) 
        con.close()
        return render_template("detail.html", articles_title=articles_title,
            name = detail[1], author = detail[2],description = detail[3],
            review = detail[4],suggestion = detail[5],date = detail[6],rate = detail[7], pictures=pictures,
            ribbons=ribbons, skills=skills, subjects=subjects, genres=genres, platforms=platforms, scores=scores,url=url)
    
    ### RESET PROFILE ###
    elif(url=="reset profile"):
        username = session.get('username')
        con = sql.connect('./db/data.db')
        cur = con.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = ?", [username])
        data = result.fetchone()
        if request.method == "POST":
            email = request.form.get('email')
            Fu_name = request.form.get('full_name')
            print(username,email,Fu_name)
            cur.execute("UPDATE users SET email=?, fullname=? WHERE username=?", (email, Fu_name, username,))
            con.commit()
            flash("Edit profile success")
            return redirect('/profile')
        con.close()
        articles_title = menuArticle()
        return render_template("reset_profile.html",data = data, articles_title=articles_title)

    ### RESET PASSWORD ###
    elif(url=="reset password"):
        if request.method == "POST":
            username = session.get('username')
            old_p = request.form.get('old_password')
            new_p = request.form.get('new_password')
            c_new_p = request.form.get('confirm_new_password')
            print(old_p)
            print(new_p)
            print(c_new_p)
                
            if new_p != c_new_p:
                return "error code: OWEN401 - new password not match"
                
            new_p = generate_password_hash(new_p)
                
            con = sql.connect('./db/data.db')
            cur = con.cursor()
            result = cur.execute("SELECT * FROM users WHERE username = ?", [username]).fetchall()[0]
            print(result)
            if check_password_hash(result[2], old_p):
                cur.execute("UPDATE users SET password=? WHERE username = ?", (new_p, username))
                con.commit()
                con.close()
                return redirect('/profile')
            else:
                con.close()
                return "error code: OWEN401 - old password do not match"
            
        articles_title = menuArticle()
        return render_template('reset_password.html',  articles_title=articles_title)
    else:
        return "error code: OWEN404 - page not found"
        
def updateScore(id, score, negative):
    
    con = sql.connect('./db/data.db')
    db = con.cursor()
    if(session.get('id_type')=='Parent'):
        db.execute("UPDATE scores SET parent_score=parent_score+{1} WHERE id={0}".format(id, score))
        con.commit()

        db.execute("UPDATE scores SET parent_score_negative=parent_score_negative+{1} WHERE id={0}".format(id, negative))
        con.commit()
    elif(session.get('id_type')=='Player'):
        db.execute("UPDATE scores SET player_score=player_score+{1} WHERE id={0}".format(id, score))
        con.commit()

        db.execute("UPDATE scores SET player_score_negative=player_score_negative+{1} WHERE id={0}".format(id, negative))
        con.commit()
        print("Score updated")
    con.close()


@app.route("/about")
def about():
    
    articles_title = menuArticle()
    return render_template("aboutus.html", articles_title=articles_title)

if __name__ == '__main__':
    app.run(debug = True)
