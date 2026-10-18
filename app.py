import streamlit as st
import sqlite3, secrets, time
from pathlib import Path

st.set_page_config(page_title='Food Twin Finder',page_icon='🍕',layout='centered')
DB=Path(__file__).with_name('food_twin.sqlite3')
QUESTIONS=[('매운 음식','안 매운 음식'),('치킨 다리살','퍽퍽살'),('뜨아','아아'),('밀떡','쌀떡'),('김치찌개','된장찌개')]

def connect():
    c=sqlite3.connect(DB,timeout=15)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, pin TEXT NOT NULL, created INTEGER NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS responses (room TEXT NOT NULL, nickname TEXT NOT NULL, answers TEXT NOT NULL, created INTEGER NOT NULL, PRIMARY KEY(room,nickname))')
    return c

def get_room(code):
    with connect() as c: return c.execute('SELECT code FROM rooms WHERE code=?',(code,)).fetchone()

def rows(code):
    with connect() as c: return c.execute('SELECT nickname,answers FROM responses WHERE room=? ORDER BY created,nickname',(code,)).fetchall()

st.title('🍕 Food Twin Finder')
st.caption('Lesson 3 · The World of Tastes · Find someone who shares your taste!')
role=st.radio('접속 유형', ['학생','교사'],horizontal=True)
if role=='교사':
    st.subheader('새 학급 만들기')
    pin=st.text_input('관리용 비밀번호 (4자리 이상)',type='password',key='newpin')
    if st.button('새 학급 코드 생성',disabled=len(pin)<4):
        with connect() as c:
            for _ in range(20):
                code=str(secrets.randbelow(900000)+100000)
                if not c.execute('SELECT 1 FROM rooms WHERE code=?',(code,)).fetchone():
                    c.execute('INSERT INTO rooms VALUES(?,?,?)',(code,pin,int(time.time())))
                    st.success(f'학급 코드: {code} · 학생들에게 이 코드와 앱 주소를 알려주세요.')
                    break
    st.divider()
    code=st.text_input('기존 학급 코드',max_chars=6,key='teacher_code')
    secret=st.text_input('관리 비밀번호',type='password',key='teacher_pin')
    with connect() as c: valid=c.execute('SELECT 1 FROM rooms WHERE code=? AND pin=?',(code,secret)).fetchone() if code and secret else None
    if valid:
        data=rows(code)
        st.metric('참여 학생',len(data))
        if data:
            for i,(a,b) in enumerate(QUESTIONS):
                n=sum(r[1][i]=='0' for r in data)
                st.write(f'**{i+1}. {a} vs {b}** · {a} {n}명 / {b} {len(data)-n}명')
                st.progress(n/len(data))
        if st.button('이 학급의 응답 모두 삭제',type='secondary'):
            with connect() as c:c.execute('DELETE FROM responses WHERE room=?',(code,))
            st.success('학급 응답이 삭제되었습니다.');st.rerun()
        if st.button('학급과 응답 완전 삭제'):
            with connect() as c:
                c.execute('DELETE FROM responses WHERE room=?',(code,))
                c.execute('DELETE FROM rooms WHERE code=?',(code,))
            st.success('학급이 삭제되었습니다.');st.rerun()
    elif code and secret:st.warning('학급 코드 또는 비밀번호를 확인해주세요.')
else:
    code=st.text_input('학급 코드 6자리',max_chars=6)
    nickname=st.text_input('별명 또는 출석번호 (중복 불가)',max_chars=20)
    if code and not get_room(code):st.warning('학급 코드를 확인해주세요.')
    if code and get_room(code) and nickname.strip():
        data=rows(code)
        mine=next((r for r in data if r[0]==nickname.strip()),None)
        if not mine:
            with st.form('survey'):
                st.write('**Which do you prefer?**')
                ans=[]
                for i,(a,b) in enumerate(QUESTIONS):
                    ans.append(st.radio(f'Q{i+1}',[a,b],index=None,key=f'q{i}'))
                submit=st.form_submit_button('제출하고 매칭하기',type='primary')
                if submit:
                    if any(x is None for x in ans):st.error('5문항을 모두 선택해주세요.')
                    else:
                        bits=''.join('0' if x==QUESTIONS[i][0] else '1' for i,x in enumerate(ans))
                        try:
                            with connect() as c:c.execute('INSERT INTO responses VALUES(?,?,?,?)',(code,nickname.strip(),bits,int(time.time())))
                            st.rerun()
                        except sqlite3.IntegrityError:st.error('이미 사용 중인 별명이에요. 다른 별명을 선택해주세요.')
        else:
            st.success(f'{nickname}님, 제출 완료!')
            others=[(n,sum(x==y for x,y in zip(mine[1],a))) for n,a in data if n!=nickname.strip()]
            if not others:st.info('아직 다른 친구가 없어요. 친구가 제출하면 새로고침하세요.')
            else:
                high=sorted(others,key=lambda x:(-x[1],x[0]))
                low=sorted(others,key=lambda x:(x[1],x[0]))
                st.subheader('💚 Food Twin TOP 3')
                for n,s in high[:3]:st.write(f'**{n}** · {s}/5개 일치 ({s*20}%)')
                st.subheader('⚡ Food Opposite')
                st.write(f'**{low[0][0]}** · {low[0][1]}/5개 일치 ({low[0][1]*20}%)')
                st.caption('동점자가 있을 수 있어요. 동점일 때는 별명순으로 표시해요.')
                st.info('Find your twin! 어떤 음식이 같고 어떤 음식이 다른지 직접 물어보세요.')
            if st.button('🔄 결과 새로고침'):st.rerun()
st.caption('수업용: 실명 대신 별명 사용 권장. 교사가 수업 후 학급 응답을 삭제해주세요. 서버 운영자는 데이터 저장 정책을 확인하세요.')
