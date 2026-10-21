import streamlit as st
import asyncio
import edge_tts
import requests
import json
from streamlit_mic_recorder import speech_to_text # 引入麦克风库

st.set_page_config(page_title="语音哲人", page_icon="🎙️")
st.title("🎙️ 青年与哲人（语音版）")

# 获取你的 API Key
api_key = st.secrets["DEEPSEEK_API_KEY"]

# 1. 语音转文字（你说话 -> 变成字）
st.write("### 第一步：点击麦克风开始说话")
text = speech_to_text(
    language='zh-CN',
    start_prompt="🎤 点击录音",
    stop_prompt="⏹️ 停止并识别",
    just_once=True,
    use_container_width=True,
    key='STT'
)

# 2. 如果识别到了文字，就发给大模型
if text:
    st.success(f"你说：{text}")
    
    with st.spinner("哲人正在思考..."):
        # 调用 DeepSeek
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一位深谙阿德勒心理学的智者。用苏格拉底式提问，简短回答，控制在50字以内。"},
                {"role": "user", "content": text}
            ]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            ai_reply = response.json()["choices"][0]["message"]["content"]
            st.info(f"哲人回复：{ai_reply}")
            
            # 3. 文字转语音（AI回答 -> 变成声音）
            async def text_to_speech(t, voice):
                communicate = edge_tts.Communicate(t, voice)
                await communicate.save("reply.mp3")
            
            # 生成语音文件
            asyncio.run(text_to_speech(ai_reply, "zh-CN-YunxiNeural"))
            
            # 播放语音（不用自动播放，让用户手动点，避免被浏览器拦截）
            st.audio("reply.mp3", format="audio/mp3")
        else:
            st.error("AI 思考出错了。")