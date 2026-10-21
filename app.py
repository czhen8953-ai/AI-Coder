import streamlit as st
import requests
import json
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# ==========================================
# 1. 页面基本配置
# ==========================================
st.set_page_config(
    page_title="青年与哲人", 
    page_icon="🧘‍♂️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 隐藏 Streamlit 默认的顶部菜单栏
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🧘‍♂️ 青年与哲人：阿德勒心理对话室")

# ==========================================
# 2. 核心逻辑：文本切片与向量检索
# ==========================================
@st.cache_resource # 缓存模型，避免每次对话都重新加载
def load_model():
    return SentenceTransformer('BAAI/bge-small-zh-v1.5')

model = load_model()

@st.cache_data
def load_and_chunk_book(file_path, chunk_size=500):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
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

book_chunks = load_and_chunk_book("book.txt")

def retrieve_relevant_context(query, chunks, top_k=2):
    if not chunks:
        return ""
    # 1. 把用户的问题变成向量坐标
    query_embedding = model.encode([query])
    # 2. 把书里的所有切块也变成向量坐标
    chunk_embeddings = model.encode(chunks)
    # 3. 计算余弦相似度
    similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
    # 4. 找出得分最高的前 top_k 个块
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    # 5. 拼起来返回
    best_context = "\n---\n".join([chunks[i] for i in top_indices if similarities[i] > 0.3])
    return best_context

# ==========================================
# 3. 侧边栏 UI
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/brain--v2.png", width=80)
    st.header("关于哲人")
    st.info("我是一个基于阿德勒心理学《被讨厌的勇气》打造的数字对话者。我不是来给你答案的，我是来向你提问的。")
    st.divider()
    if st.button("🗑️ 清空聊天记录", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. 聊天主循环
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染历史消息
for msg in st.session_state.messages:
    if msg["role"] != "system":
        avatar = "🙋‍♂️" if msg["role"] == "user" else "🧘‍♂️"
        with st.chat_message(msg["role"], avatar=avatar):
            st.write(msg["content"])

# 接收用户输入
if user_input := st.chat_input("青年，你在为什么烦恼？"):
    
    # 显示用户输入
    with st.chat_message("user", avatar="🙋‍♂️"):
        st.write(user_input)
    
    # 检索相关书本内容
    relevant_book_text = retrieve_relevant_context(user_input, book_chunks)
    
    # 动态生成系统提示词
    system_prompt = f"""你是一位深谙阿德勒心理学的智者（哲人）。称呼用户为青年。
你必须用苏格拉底式提问，绝对不要直接给答案。每次回复控制在200字以内。

【参考以下书中的相关内容进行回答】：
{relevant_book_text}
"""

    # 打包发送给 API 的消息
    messages_to_send = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 🔑 读取 API Key（兼容环境变量和 secrets）
    api_key = os.getenv("DEEPSEEK_API_KEY") or st.secrets["DEEPSEEK_API_KEY"]
    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": messages_to_send,
        "stream": True
    }
    
    # 显示 AI 回复
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