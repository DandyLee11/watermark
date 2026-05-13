import streamlit as st
import numpy as np
from PIL import Image
import io
import os
import cv2

# ========== 核心：导入你仓库里的文件夹 ==========
try:
    from blind_watermark import WaterMark
except ImportError:
    st.error("找不到 blind_watermark 文件夹，请确认文件夹名正确且包含 __init__.py")

# 页面配置
st.set_page_config(page_title="GITO 品牌保护工具", layout="wide")
st.title("🛡️ GITO 专用：频域盲水印 (兼容修复版)")

# 算法密钥 (固定)
PWD_IMG = 1
PWD_WM = 1

def process_embed(file, text):
    # 1. 预处理图片
    img = Image.open(file)
    orig_format = img.format
    temp_in = "temp_in.png"
    img.save(temp_in)

    # 2. 初始化算法并嵌入
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    
    # 【兼容性修复】：手动读取图片并赋值给对象，跳过可能报错的 read_img 函数
    bwm.img = cv2.imread(temp_in)
    
    bwm.read_wm(text, mode='str')
    bwm.embed("temp_out.png")
    
    # 3. 控制导出体积
    wm_img = Image.open("temp_out.png")
    buf = io.BytesIO()
    
    if orig_format in ["JPG", "JPEG"]:
        # 质量设为 85，既保住水印又控制体积
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
    
    # 【兼容性修复】：手动读取待测图并赋值给属性
    bwm.img_wm = cv2.imread(temp_ext)
    
    # 提取：传入当初的字符长度
    return bwm.extract(wm_shape=wm_len, mode='str')

# 界面展示
mode = st.radio("功能切换", ["添加盲水印", "提取盲水印"])

if mode == "添加盲水印":
    upload = st.file_uploader("上传原图", type=["jpg", "jpeg", "png"])
    text = st.text_input("水印内容 (如：GITO-2026)", "GITO-2026")
    
    if upload and st.button("一键加密"):
        with st.spinner("频域变换处理中..."):
            res_bytes, length, ext = process_embed(upload, text)
            st.image(res_bytes, caption="已嵌入水印")
            st.success(f"⚠️ 提取关键提示：提取此图时，字符长度请填入 {length}")
            st.download_button("保存保护后的图片", res_bytes, f"gito_protected.{ext}")

else:
    upload = st.file_uploader("上传待检测图", type=["jpg", "jpeg", "png"])
    wm_len = st.number_input("请输入当初设定的水印长度", min_value=1, value=9)
    
    if upload and st.button("开始提取"):
        try:
            res = process_extract(upload, wm_len)
            if res:
                st.success(f"✅ 成功溯源信息：{res}")
            else:
                st.error("未能检测到水印信息。")
        except Exception as e:
            st.error(f"解析出错：请核对长度参数。详细错误：{str(e)}")
