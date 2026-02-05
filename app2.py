import json
from PIL import Image
from bs4 import BeautifulSoup
import re
import requests as rq
import pandas as pd
import numpy as np
import pickle
import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from streamlit_lottie import st_lottie


def loadJSON(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def getRequest(keyword, display, start):
    url = f'https://openapi.naver.com/v1/search/news.json?query={keyword}&display={display}&start={start}'
    headers = {'X-Naver-Client-Id': st.session_state['client_id'], 'X-Naver-Client-Secret': st.session_state['client_secret']}
    res = rq.get(url, headers=headers)
    if res.status_code != 200:
        st.error(f"HTTP Error {res.status_code}")
        return []
    my_json = res.json()
    if 'items' not in my_json:
        st.error(f"API Error: {my_json}")
        return []
    return my_json['items']

@st.cache_data
def cleanText(text):
    text = re.sub(r'\d|[a-zA-Z]|\W',' ', text)
    text = re.sub(r'\s+',' ', text)
    return text

@st.cache_resource
def getTokenizer():
    with open('./resources/my_tokenizer1.model', 'rb') as f:
        return pickle.load(f)

def makeTable(tokens, nmin=2, nmax=5, ncut=1):
    tokens_new = []
    for token in tokens:
        if len(token) >= nmin and len(token) <= nmax:
            tokens_new.append(token)
    ser = pd.Series(tokens_new)
    ser = ser.value_counts()
    ser = ser[ser >= ncut]
    return dict(ser.sort_values(ascending=False))

def plotChart(count_dict, back_mask, max_words_, container):
    if back_mask == '타원':
        img = Image.open('./resources/background_1.png')
    elif back_mask == '말풍선':
        img = Image.open('./resources/background_2.png')
    elif back_mask == '하트':
        img = Image.open('./resources/background_3.png')
    else:
        img = Image.open('./resources/background_0.png')
    my_mask=np.array(img)
    wc = WordCloud(
        font_path='./resources/NanumSquareR.ttf', 
        background_color='white', 
        contour_color='grey', 
        contour_width=3, 
        max_words=max_words_, 
        mask=my_mask
    )   
    wc.generate_from_frequencies(count_dict)
    fig = plt.figure(figsize=(10,10))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis("off")
    container.pyplot(fig)


col1, col2 = st.columns([1,2])
with col1:
    lottie = loadJSON('./resources/lottie-full-movie-experience-including-music-news-video-weather-and-lots-of-entertainment.json')
    st_lottie(lottie, speed=1, loop=True, width=200, height=200)
with col2:
    st.markdown("### ")
    st.title('뉴스 키워드 시각화')


if 'client_id' not in st.session_state:
    st.session_state['client_id'] = ''
if 'client_secret' not in st.session_state:
    st.session_state['client_secret'] = ''
with st.sidebar.form(key="client_settings", clear_on_submit=False):
    st.header('API 설정')
    client_id = st.text_input('Client ID:', value= st.session_state['client_id'] )
    client_secret = st.text_input('Client Secret:', type='password', value=st.session_state['client_secret'])
    if st.form_submit_button(label="OK"):
        st.session_state['client_id'] = client_id
        st.session_state['client_secret'] = client_secret
        st.rerun()


chart_container = st.empty()


with st.form('search', clear_on_submit=False):
    search_keyword = st.selectbox('분야:', ['경제', '정치', '사회', '국제', '연예', 'IT', '문화'])
    user_keyword = st.text_input('구체적인 키워드 (선택 사항):', '')

    final_keyword = f"{search_keyword} {user_keyword}".strip()

    data_amount = st.slider('분량:', min_value=1, max_value=5, step=1, value=1)
    back_mask = st.radio('백마스크:', ['없음', '타원', '말풍선', '하트'], horizontal=True)

    if not final_keyword and st.form_submit_button('OK'):
        st.warning("키워드를 입력해주세요!")
    elif st.form_submit_button('OK'):
        chart_container.info(':red[데이터 가져오는 중...]')
        corpus = ''
        items = []
        
        for i in range(data_amount):
            result = getRequest(final_keyword, 100, 100*i + 1)
            if not result:
                break
            items.extend(result)
        
        articles = []
        for item in items:
            title = item.get('title')
            pubDate = item.get('pubDate')
            link = item.get('link')
            articles.append([title, pubDate, link])

        if articles:
            df_articles = pd.DataFrame(articles, columns=['제목', '날짜', '링크'])
            show_articles = st.checkbox('기사 목록 보기', value=True)
            if show_articles:
                st.dataframe(df_articles)
        
        for item in items:
            link = item.get('link')
            if not link or 'n.news.naver' not in link:
                continue
            try:
                res = rq.get(link, headers={'User-Agent': 'Mozilla'}, timeout=5)
                if res.status_code != 200:
                    continue
                soup = BeautifulSoup(res.text, 'html.parser')
                news_tag = soup.select_one('#dic_area')
                if news_tag:
                    corpus += news_tag.text + '\n'
            except Exception:
                continue
        
        if len(corpus) > 100:
            chart_container.info(':red[이미지 생성 중...]')
            corpus = cleanText(corpus)
            my_tokenizer = getTokenizer()
            tokens = [t1 for t1, t2 in my_tokenizer.tokenize(corpus, flatten=False)]
            count_dict = makeTable(tokens)
            plotChart(count_dict, back_mask, 70, chart_container)
        else:
            chart_container.error(':red[데이터 불충분 오류!]')