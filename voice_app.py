import streamlit as st
import asyncio
import edge_tts
import os

st.set_page_config(page_title="语音测试", page_icon="🎙️")
st.title("🎙️ 语音魔法测试")

# 1. 这是微软 Edge 的免费语音引擎配置
VOICE = "zh-CN-YunxiNeural" # 云希（男声，比较有磁性），你也可以换成 zh-CN-XiaoxiaoNeural（晓晓，女声）

# 2. 核心函数：把文字变成 mp3 文件
async def text_to_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("output.mp3")

st.write("点击下方按钮，让哲人开口说话：")

# 3. 简单的交互
if st.button("让哲人说话"):
    # 假装这是哲人的回答
    reply_text = "青年啊，你之所以感到痛苦，是因为你一直活在别人的期待里。放下对他人认可的执着，你才能获得真正的自由。"
    
    with st.spinner("哲人正在清嗓子..."):
        # 运行异步语音生成函数
        asyncio.run(text_to_speech(reply_text, VOICE))
        
    st.success("语音生成完毕！")
    # 播放生成的音频
    st.audio("output.mp3", format="audio/mp3", autoplay=True)