import streamlit as st
import numpy as np
from PIL import Image
import io
import os

# ========== 核心：让程序认得你刚搬进去的文件夹 ==========
try:
    from blind_watermark import WaterMark
except ImportError:
    st.error("程序还是找不到文件夹，请检查你的文件夹名是否叫 blind_watermark (全小写+下划线)")

# 页面配置
st.set_page_config(page_title="GITO 品牌保护工具", layout="wide")
st.title("🛡️ GITO 专用：原版算法盲水印 (guofei9987)")

# 算法密钥 (固定，提取时也用这个)
PWD_IMG = 1
PWD_WM = 1

def process_embed(file, text):
    # 记录原图格式，防止体积暴涨
    img = Image.open(file)
    orig_format = img.format
    
    # 1. 保存临时原图
    temp_in = "temp_in" + (".jpg" if orig_format == "JPEG" else ".png")
    with open(temp_in, "wb") as f:
        f.write(file.getvalue())

    # 2. 调用你文件夹里的算法进行嵌入
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    bwm.read_img(temp_in)
    bwm.read_wm(text, mode='str')
    bwm.embed("temp_out.png") # 算法生成过程中推荐用png保证精度
    
    # 3. 压回原格式并控制体积
    wm_img = Image.open("temp_out.png")
    buf = io.BytesIO()
    
    if orig_format in ["JPG", "JPEG"]:
        # 质量设为 85，体积增加极小且能保住水印
        wm_img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
        ext = "jpg"
    else:
        wm_img.save(buf, format="PNG")
        ext = "png"
    
    return buf.getvalue(), len(text), ext

def process_extract(file, wm_len):
    # 保存待检测图
    with open("temp_ext.png", "wb") as f:
        f.write(file.getvalue())
    
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    # 提取时必须要传正确的长度 wm_shape
    return bwm.extract("temp_ext.png", wm_shape=wm_len, mode='str')

# 界面展示
mode = st.radio("功能切换", ["添加盲水印", "提取盲水印"])

if mode == "添加盲水印":
    upload = st.file_uploader("上传原图", type=["jpg", "jpeg", "png"])
    text = st.text_input("水印内容 (建议 12 位以内)", "GITO-2026")
    
    if upload and st.button("一键无损嵌入"):
        with st.spinner("正在频域加密中..."):
            res_bytes, length, ext = process_embed(upload, text)
            st.image(res_bytes, caption="嵌入成功")
            st.success(f"⚠️ 提取关键提示：提取此图时，长度请填入 {length}")
            st.download_button("下载图片", res_bytes, f"protected_img.{ext}")

else:
    upload = st.file_uploader("上传待检测图", type=["jpg", "jpeg", "png"])
    wm_len = st.number_input("请输入当初设定的水印长度", value=9)
    
    if upload and st.button("开始深度解析"):
        try:
            res = process_extract(upload, wm_len)
            if res:
                st.success(f"✅ 成功溯源信息：{res}")
            else:
                st.error("未能检测到水印。")
        except Exception as e:
            st.error("解析失败：长度不符或图片经过极端改动。")
