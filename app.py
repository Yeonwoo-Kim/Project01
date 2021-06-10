import pymongo
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
        user_info = db.users.find_one({"username": payload["id"]})

        all = list(db.music.find().sort('mId', -1))
        popular = list(db.music.find().sort('like', -1))

        return render_template("index.html", all=all, popular=popular, user_info=user_info)

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
    all = list(db.music.find())
    popular = list(db.music.find().sort('like', -1))

    return render_template("index.html", all=all, popular=popular)


@app.route('/api/save_music', methods=['POST'])
def save_music():
    #  저장하기

    if db.music.count_documents({}) == 0:
        index = 1
    else:  # document 가 있으면
        data = list(db.music.find({}).sort('_id', pymongo.DESCENDING).limit(1))
        data1 = data[0]
        index = data1['mId'] + 1

    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.users.find_one({"username": payload["id"]})
    writer = user_info['username']

    url_receive = request.form["url_give"]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url_receive, headers=headers)

    soup = BeautifulSoup(data.text, 'html.parser')

    title = soup.select_one('#body-content > div.album-detail-infos > div.info-zone >h2').text
    artist = soup.select_one(
        '#body-content > div.album-detail-infos > div.info-zone > ul > li:nth-child(1) > span.value > a').text

    albumArt = soup.select_one('#body-content > div.album-detail-infos > div.photo-zone > a > span.cover > img')['src']

    genre = soup.select_one(
        '#body-content > div.album-detail-infos > div.info-zone > ul > li:nth-child(2) > span.value').text
    release_date = soup.select_one(
        '#body-content > div.album-detail-infos > div.info-zone > ul > li:nth-child(5) > span.value').text
    check = db.music.find_one({'title': title}, {'artist': artist})

    doc = {
        'mId': index,
        'title': title,
        'artist': artist,
        "albumArt": albumArt,
        'like': 0,
        'url': url_receive,
        'writer': writer,
        'genre': genre,
        'release_date': release_date,


    }

    if check:
        return jsonify({'result': 'success', 'msg': f' "{title}" 은 이미 있는 곡입니다!'})
    else:
        db.music.insert_one(doc)
        return jsonify({'result': 'success', 'msg': f' "{artist}" 의 곡이 저장 완료되었습니다!'})


@app.route('/api/like', methods=['POST'])
def like_music():
    index_receive = int(request.form['index_give'])
    print(type(index_receive))
    target_music = db.music.find_one({'mId':index_receive})
    current_like = target_music['like']

    new_like = current_like + 1

    db.music.update_one({'_id': target_music['_id']}, {'$set': {'like': new_like}})

    return jsonify({'msg': '좋아요 완료!'})



@app.route('/api/delete_music', methods=['POST'])
def delete_music():


    target_music = int(request.form['index_give'])

    db.music.delete_one({"mId":target_music})
    d = list(db.posts.remove({'mId':target_music}))


    return jsonify({'result': 'success', 'msg': f'word "{target_music}" deleted'})


'''--------------------------------------------------------------------'''

@app.route('/detail')
def detail():
    token_receive = request.cookies.get('mytoken')

    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_info = db.users.find_one({"username": payload["id"]})

    mId = int(request.args.get("mId"))

    target_music = db.music.find_one({'mId': mId})

    return render_template("detail.html", doc=target_music,user_info=user_info)


@app.route('/posting', methods=['POST'])
def posting():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 포스팅하기
        user_info = db.users.find_one({"username": payload["id"]})
        comment_receive = request.form["comment_give"]
        date_receive = request.form["date_give"]
        mId = int(request.form["mId"])
        print(type(date_receive))
        doc = {
            "username": user_info["username"],
            "profile_name": user_info["profile_name"],
            "profile_pic_real": user_info["profile_pic_real"],
            "comment": comment_receive,
            "date": date_receive,
            "mId": mId
        }
        db.posts.insert_one(doc)
        return jsonify({"result": "success", 'msg': '포스팅 성공'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route("/get_posts", methods=['GET'])
def get_posts():

    mId = int(request.args.get("mId"))
    print(mId)

    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        my_username = payload["id"]

        target_music = db.music.find_one({'mId': mId})
        print(target_music)
        posts = list(db.posts.find({'mId': mId}).sort("date", -1).limit(20))

        print(posts)
        for post in posts:
            post["_id"] = str(post["_id"])

            post["count_heart"] = db.likes.count_documents({"post_id": post["_id"], "type": "heart"})
            post["heart_by_me"] = bool(
                db.likes.find_one({"post_id": post["_id"], "type": "heart", "username": my_username}))

            post["count_star"] = db.likes.count_documents({"post_id": post["_id"], "type": "star"})
            post["star_by_me"] = bool(
                db.likes.find_one({"post_id": post["_id"], "type": "star", "username": my_username}))

            post["count_like"] = db.likes.count_documents({"post_id": post["_id"], "type": "like"})
            post["like_by_me"] = bool(
                db.likes.find_one({"post_id": post["_id"], "type": "like", "username": my_username}))

        return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다.", "posts": posts})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/update_like', methods=['POST'])
def update_like():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 좋아요 수 변경
        user_info = db.users.find_one({"username": payload["id"]})
        post_id_receive = request.form["post_id_give"]
        type_receive = request.form["type_give"]
        action_receive = request.form["action_give"]
        doc = {
            "post_id": post_id_receive,
            "username": user_info["username"],
            "type": type_receive
        }
        if action_receive =="like":
            db.likes.insert_one(doc)
        else:
            db.likes.delete_one(doc)
        count = db.likes.count_documents({"post_id": post_id_receive, "type": type_receive})
        print(count)
        return jsonify({"result": "success", 'msg': 'updated', "count": count})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# ---------------------main page-----------------------------

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)