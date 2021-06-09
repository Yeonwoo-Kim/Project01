from pymongo import MongoClient
import jwt
import requests
from bs4 import BeautifulSoup
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

client = MongoClient('localhost', 27017)
db = client.hansarang


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        all = list(db.dbsparta_p1.find())
        popular = list(db.dbsparta_p1.find().sort('like', -1))

        return render_template("index.html", all=all, popular=popular)

        #return render_template('index.html')
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
        "profile_name": username_receive,  # 프로필 이름 기본값은 아이디
        "profile_pic": "",  # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지
        "profile_info": ""  # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

# --------------------main page----------------------------------

@app.route('/main')
def main():
    # status_receive = request.args.get("status_give")
    # print(status_receive)
    #
    # # API에서 단어 뜻 찾아서 결과 보내기
    # r = requests.get(f"https://owlbot.info/api/v4/dictionary/{keyword}", headers={"Authorization": "Token 8d0d9d0e32a84ba7fdebc5040d4a3b77991aefb4"})
    # result = r.json()
    # print(result)
    all = list(db.dbsparta_p1.find())
    popular = list(db.dbsparta_p1.find().sort('like', -1))

    return render_template("index.html", all=all,popular=popular)



@app.route('/api/save_music', methods=['POST'])
def save_music():
    #  저장하기

    if db.dbsparta_p1.count_documents({}) == 0:
        index = 1
    else:  # document 가 있으면
        data = list(db.dbsparta_p1.find({}).sort('_id', pymongo.DESCENDING).limit(1))
        data1 = data[0]
        index = data1['_id'] + 1

    url_receive = request.form["url_give"]
    print('url_receive?', url_receive)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url_receive, headers=headers)

    soup = BeautifulSoup(data.text, 'html.parser')

    title = soup.select_one('#body-content > div.album-detail-infos > div.info-zone >h2').text
    artist = soup.select_one('#body-content > div.album-detail-infos > div.info-zone > ul > li:nth-child(1) > span.value > a').text

    albumArt = soup.select_one('#body-content > div.album-detail-infos > div.photo-zone > a > span.cover > img')['src']
    print(title)
    test = db.dbsparta_p1.find_one({'title': title}, {'artist': artist})

    print(test, 'test')

    doc = {
        '_id': index,
        'title': title,
        'artist': artist,
        "albumArt": albumArt,
        'like': 0

    }

    if test:
        print('lololo')
    else:
        db.dbsparta_p1.insert_one(doc)

    return jsonify({'result': 'success', 'msg': f'word "{artist}" saved'})

@app.route('/api/like', methods=['POST'])
def like_music():
    title_receive = request.form['title_give']
    artist_receive = request.form['artist_give']

    target_music = db.dbsparta_p1.find_one({'artist': artist_receive, 'title': title_receive})
    print(target_music['_id'])
    current_like = target_music['like']

    new_like = current_like + 1

    db.dbsparta_p1.update_one({'_id': target_music['_id']}, {'$set': {'like': new_like}})

    return jsonify({'msg': '좋아요 완료!'})

# ---------------------main page-----------------------------

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
