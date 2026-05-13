import streamlit as st
import numpy as np
from PIL import Image
from blind_watermark import WaterMark
import io
import os

st.set_page_config(page_title="GITO 专业盲水印", layout="wide")
st.title("🛡️ 基于 guofei9987 算法的专业盲水印")
st.info("此版本采用频域变换算法，支持微信压缩、截图、抗噪，且严格控制画质。")

# 初始化算法 (设置固定密钥，确保嵌入和提取匹配)
PWD_IMG = 1
PWD_WM = 1

def process_embed(img_bytes, text):
    # 临时保存以便库读取
    with open("temp_orig.jpg", "wb") as f:
        f.write(img_bytes)
    
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    bwm.read_img("temp_orig.jpg")
    bwm.read_wm(text, mode='str')
    bwm.embed("temp_wm.png") # 库默认生成png以保证算法准确
    
    # 关键：将生成的PNG转回原格式并压缩体积
    wm_img = Image.open("temp_wm.png")
    buf = io.BytesIO()
    # 质量设为 85-90 是最平衡的，体积几乎不会变大
    wm_img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()

def process_extract(img_bytes, wm_len):
    with open("temp_to_extract.jpg", "wb") as f:
        f.write(img_bytes)
    
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    # 该算法提取时必须知道当初嵌入的字符长度
    res = bwm.extract("temp_to_extract.jpg", wm_shape=wm_len, mode='str')
    return res

mode = st.radio("功能切换", ["添加水印", "提取溯源"])

if mode == "添加水印":
    file = st.file_uploader("上传图片", type=["jpg", "jpeg", "png"])
    text = st.text_input("水印内容 (建议英文)", "GITO-QC-2026")
    
    if file and st.button("开始无损嵌入"):
        res_bytes = process_embed(file.getvalue(), text)
        st.image(res_bytes, caption="嵌入成功")
        st.success(f"⚠️ 提取提示：提取此图时，请记住水印长度为 {len(text)}")
        st.download_button("下载图片", res_bytes, "GITO_Protected.jpg")

else:
    file = st.file_uploader("上传待检测图片", type=["jpg", "jpeg", "png"])
    # 这一步是关键，guofei9987 的算法需要知道长度
    wm_len = st.number_input("请输入已知水印字符长度", min_value=1, value=12)
    
    if file and st.button("开始深度解析"):
        try:
            res = process_extract(file.getvalue(), wm_len)
            st.success(f"✅ 成功提取溯源信息：{res}")
        except Exception as e:
            st.error("解析失败：请确保输入的长度正确，且图片确实包含该算法的水印。")
