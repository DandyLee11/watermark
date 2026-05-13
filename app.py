import streamlit as st
import numpy as np
from PIL import Image
import io
import os
import cv2
import sys

# --- 1. 强制路径修复：手动将当前目录和子文件夹注入系统名单 ---
# 这能解决 Streamlit 云端无法识别本地盲水印包的问题
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    # 尝试从本地文件夹加载算法
    from blind_watermark import WaterMark
except ImportError:
    st.error("【关键报错】即便配置了路径，依然找不到算法库。请确保文件夹名是 blind_watermark 且内部有 __init__.py")
    st.stop()

# --- 页面设置 ---
st.set_page_config(page_title="GITO 品牌专用：无损盲水印", layout="wide")
st.title("🛡️ GITO 专用：频域盲水印 (稳定对比版)")
st.write("已优化：解决提取失败、路径识别及体积控制问题。")

# 算法密钥 (固定，生成和提取必须一致)
PWD_IMG = 1
PWD_WM = 1

def process_embed(file, text):
    # 1. 预处理：先存为临时 PNG 保证算法精度
    img = Image.open(file)
    orig_format = img.format
    temp_in = "temp_in.png"
    img.save(temp_in)

    # 2. 调用算法逻辑
    bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
    
    # 【兼容性修复】：直接操作属性读取，避开 read_img 报错
    bwm.img = cv2.imread(temp_in)
    bwm.read_wm(text, mode='str')
    bwm.embed("temp_out.png")
    
    # 3. 结果处理：控制导出体积
    wm_img = Image.open("temp_out.png")
    buf = io.BytesIO()
    
    if orig_format in ["JPG", "JPEG"]:
        # 质量设为 85 是保住水印且不增加体积的黄金点
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
    
    # 【兼容性修复】：直接操作属性读取待测图
    bwm.img_wm = cv2.imread(temp_ext)
    
    # 执行提取
    return bwm.extract(wm_shape=wm_len, mode='str')

# --- 界面交互 ---
mode = st.radio("功能切换", ["添加盲水印", "提取盲水印"])

if mode == "添加盲水印":
    upload = st.file_uploader("上传原图", type=["jpg", "jpeg", "png"])
    text = st.text_input("水印内容 (例如: GITO-2026)", "GITO-2026")
    
    if upload and st.button("开始加密"):
        with st.spinner("正在进行频域变换..."):
            res_bytes, length, ext = process_embed(upload, text)
            st.image(res_bytes, caption="水印已成功嵌入")
            st.success(f"✅ 重要：提取此图时，字符长度请填入 {length}")
            st.download_button("保存受保护图片", res_bytes, f"gito_protected.{ext}")

else:
    upload = st.file_uploader("上传待检测图", type=["jpg", "jpeg", "png"])
    wm_len = st.number_input("请输入生成时告知的字符长度", min_value=1, value=9)
    
    if upload and st.button("开始解析"):
        try:
            res = process_extract(upload, wm_len)
            if res:
                st.success(f"🔍 识别到信息：{res}")
            else:
                st.warning("未能识别到水印，请检查图片是否被极端裁剪或压缩。")
        except Exception as e:
            st.error("解析失败：长度参数不匹配或图片结构已被破坏。")
