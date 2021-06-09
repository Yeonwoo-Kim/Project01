import pymongo
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import jwt
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

db.users.delete_one({'username': 'test1'})


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


#
#


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
