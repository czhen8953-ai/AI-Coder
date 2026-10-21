import streamlit as st
import requests
import json
import re # 用于文本处理

# 1. 页面基本配置
st.set_page_config(
    page_title="青年与哲人", 
    page_icon="🧘‍♂️", 
    layout="wide",  # 🌟 关键：开启宽屏模式，让聊天框变宽
    initial_sidebar_state="expanded"
)

# 2. 隐藏 Streamlit 默认的顶部菜单栏（让它看起来像一个独立App）
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🧘‍♂️ 青年与哲人：阿德勒心理对话室")

# --- 核心升级：文本切片与检索 ---
@st.cache_data
def load_and_chunk_book(file_path, chunk_size=500):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        # 把书按段落切开，然后每 500 个字拼成一个小块（Chunk）
        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = p + "\n"
        if current_chunk:
            chunks.append(current_chunk)
        return chunks
    except FileNotFoundError:
        return ["书上空白一片。"]

# 把整本书切成小碎块（比如切成了 200 块）
book_chunks = load_and_chunk_book("book.txt")

# 检索函数：当用户提问时，去 200 个碎块里找最相关的 2 块
def retrieve_relevant_context(query, chunks, top_k=2):
    # 极简版检索：把用户的问题拆成字，看哪个碎块包含的这些字最多
    query_chars = set(query)
    scored_chunks = []
    for chunk in chunks:
        # 算重合度
        score = len(query_chars.intersection(set(chunk)))
        scored_chunks.append((score, chunk))
    
    # 按分数从高到低排序，取前 top_k 个
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # 把选出来的碎块拼起来
    best_context = "\n---\n".join([chunk for score, chunk in scored_chunks[:top_k]])
    return best_context

# ==========================================
# 🌟 侧边栏 UI
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/brain--v2.png", width=80) # 随便找了一个网上的大脑图标
    st.header("关于哲人")
    st.info("我是一个基于阿德勒心理学《被讨厌的勇气》打造的数字对话者。我不是来给你答案的，我是来向你提问的。")
    
    st.divider() # 加一条分割线
    
    if st.button("🗑️ 清空聊天记录", use_container_width=True):
        st.session_state.messages = [] # 清空记忆
        st.rerun() # 重新加载页面

# --- 以下逻辑和之前类似，但加入了检索 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] != "system":
        # 如果是用户，显示 🙋‍♂️；如果是 AI，显示 🧘‍♂️
        avatar = "🙋‍♂️" if msg["role"] == "user" else "🧘‍♂️"
        with st.chat_message(msg["role"], avatar=avatar):
            st.write(msg["content"])
if user_input := st.chat_input("青年，你在为什么烦恼？"):
    
    with st.chat_message("user",avatar="🙋‍♂️"):
        st.write(user_input)
    
    # 💡 核心：在发给 AI 之前，先去书里只找相关的部分！
    relevant_book_text = retrieve_relevant_context(user_input, book_chunks)
    
    # 动态生成系统提示词：这次不是塞整本书，只塞搜出来的段落
    system_prompt = f"""你是一位深谙阿德勒心理学的智者（哲人）。称呼用户为青年。
你必须用苏格拉底式提问，绝对不要直接给答案。每次回复控制在200字以内。

【参考以下书中的相关内容进行回答】：
{relevant_book_text}
"""

    # 把系统提示词和用户的话打包
    messages_to_send = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    data = {
        "model": "deepseek-chat",
        "messages": messages_to_send, # 注意这里发的是精简过的消息
        "stream": True
    }
    
    with st.chat_message("assistant", avatar="🧘‍♂️"):
        def generate_reply():
            response = requests.post(url, headers=headers, json=data, stream=True)
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            content = decoded_line[6:]
                            if content != "[DONE]":
                                try:
                                    json_data = json.loads(content)
                                    delta = json_data["choices"][0]["delta"]
                                    if "content" in delta:
                                        yield delta["content"]
                                except json.JSONDecodeError:
                                    pass
            else:
                yield f"出错了，状态码：{response.status_code}"
        
        full_reply = st.write_stream(generate_reply())
    
    st.session_state.messages.append({"role": "assistant", "content": full_reply})