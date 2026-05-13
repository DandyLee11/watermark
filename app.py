import streamlit as st
import numpy as np
from PIL import Image
import io
import os

# 重点：直接导入你仓库里的文件夹
try:
    from blind_watermark import WaterMark
except:
    st.error("请确保你已经把 blind_watermark 的文件夹上传到了 GitHub 仓库中")

st.set_page_config(page_title="GITO 品牌保护", layout="wide")
st.title("🛡️ guofei9987 原版算法盲水印")

# 固定参数（钥匙）
PWD_IMG = 1
PWD_WM = 1

def process_embed(img_file, text):
    # 保存原始格式，防止体积爆炸
    img = Image.open(img_file)
    orig_format = img.format
    
    # blind_watermark 库需要文件路径，所以先存为临时文件
    temp_in = "temp_in" + (".jpg" if orig_format == "JPEG" else ".png")
    with open(temp_in, "wb") as f:
        f.write(img_file.getvalue())

    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    bwm.read_img(temp_in)
    bwm.read_wm(text, mode='str')
    
    # 强制生成到 temp_out
    bwm.embed("temp_out.png")
    
    # 核心：读取生成的图，按原格式压回，控制体积
    wm_img = Image.open("temp_out.png")
    buf = io.BytesIO()
    
    if orig_format in ["JPG", "JPEG"]:
        # 这里的质量 80-85 是 guofei 算法的抗压缩阈值，体积不会暴涨
        wm_img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
    else:
        wm_img.save(buf, format="PNG")
    
    buf.seek(0)
    return buf.getvalue(), len(text)

def process_extract(img_file, wm_len):
    with open("temp_ext.png", "wb") as f:
        f.write(img_file.getvalue())
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    # 提取：必须传长度参数
    return bwm.extract("temp_ext.png", wm_shape=wm_len, mode='str')

mode = st.radio("模式", ["添加水印", "提取水印"])

if mode == "添加水印":
    file = st.file_uploader("上传原图", type=["jpg", "jpeg", "png"])
    text = st.text_input("水印内容", "GITO-2026")
    if file and st.button("开始"):
        res_bytes, length = process_embed(file, text)
        st.image(res_bytes)
        st.success(f"已嵌入！提取时请输入长度: {length}")
        st.download_button("下载图片", res_bytes, "protected.jpg")

else:
    file = st.file_uploader("上传图片", type=["jpg", "jpeg", "png"])
    wm_len = st.number_input("输入水印字符长度", value=9)
    if file and st.button("开始提取"):
        try:
            res = process_extract(file, wm_len)
            st.success(f"成功：{res}")
        except:
            st.error("提取失败，请核对长度")
