import streamlit as st
import numpy as np
from PIL import Image
import io
import os
import cv2
import sys

# --- 1. 路径修复：强制程序认领本地 blind_watermark 文件夹 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from blind_watermark import WaterMark
except ImportError:
    st.error("无法加载算法库。请确保 GitHub 仓库中有一个名为 blind_watermark 的文件夹，且内部包含 __init__.py")

# --- 页面设置 ---
st.set_page_config(page_title="GITO 品牌保护工具", layout="wide")
st.title("🛡️ GITO 专用：频域盲水印 (最终修复版)")
st.write("已优化：解决提取失败、找不到文件夹及体积过大问题。")

# 算法密钥（保持固定）
PWD_IMG = 1
PWD_WM = 1

def process_embed(file, text):
    # 读取图片并转为 PNG 临时处理以保证精度
    img = Image.open(file)
    orig_format = img.format
    temp_in = "temp_in.png"
    img.save(temp_in)

    # 初始化算法
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    
    # 【兼容性修复】：直接操作属性，避开 read_img 报错
    bwm.img = cv2.imread(temp_in)
    bwm.read_wm(text, mode='str')
    bwm.embed("temp_out.png")
    
    # 读取生成的图片
    wm_img = Image.open("temp_out.png")
    buf = io.BytesIO()
    
    # 【体积修复】：如果是 JPG，用 85 质量压回，防止体积暴涨
    if orig_format in ["JPG", "JPEG"]:
        wm_img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
        ext = "jpg"
    else:
        wm_img.save(buf, format="PNG", optimize=True)
        ext = "png"
    
    return buf.getvalue(), len(text), ext

def process_extract(file, wm_len):
    # 保存待检测图
    temp_ext = "temp_ext.png"
    with open(temp_ext, "wb") as f:
        f.write(file.getvalue())
    
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    
    # 【兼容性修复】：直接操作属性读取图片
    bwm.img_wm = cv2.imread(temp_ext)
    
    # 提取水印
    return bwm.extract(wm_shape=wm_len, mode='str')

# --- 界面交互 ---
mode = st.radio("功能切换", ["添加盲水印", "提取盲水印"])

if mode == "添加盲水印":
    upload = st.file_uploader("上传原图", type=["jpg", "jpeg", "png"])
    text = st.text_input("水印内容 (例如: GITO-2026)", "GITO-2026")
    
    if upload and st.button("开始加密"):
        with st.spinner("正在进行频域加密..."):
            res_bytes, length, ext = process_embed(upload, text)
            st.image(res_bytes, caption="水印已成功嵌入")
            st.success(f"✅ 提示：提取此图时，字符长度请填入 {length}")
            st.download_button("下载受保护图片", res_bytes, f"gito_protected.{ext}")

else:
    upload = st.file_uploader("上传带水印的图片", type=["jpg", "jpeg", "png"])
    wm_len = st.number_input("请输入当初设定的水印长度", min_value=1, value=9)
    
    if upload and st.button("开始提取"):
        try:
            res = process_extract(upload, wm_len)
            if res:
                st.success(f"🔍 识别到信息：{res}")
            else:
                st.warning("未能识别到水印，请确保是使用本工具生成的图片。")
        except Exception as e:
            st.error(f"提取出错：长度不符或图片已被严重裁剪。")
