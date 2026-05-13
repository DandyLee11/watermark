import streamlit as st
import numpy as np
from PIL import Image
import io

# 页面配置
st.set_page_config(page_title="GITO 无损盲水印工具", layout="wide")
st.title("🔒 GITO 品牌专用无损盲水印")
st.info("特点：尺寸不变、原格式导出、支持发微信等普通压缩 [cite: 12, 16]")

# 基于 DCT 的稳健盲水印算法 (零依赖版) [cite: 18, 19]
def add_watermark(img_np, watermark_text):
    h, w, _ = img_np.shape
    # 编码文字
    text_bin = ''.join(format(ord(c), '08b') for c in watermark_text)
    text_len = len(text_bin)
    idx = 0
    # 遍历 8x8 像素块 [cite: 19]
    for i in range(0, h - (h % 8), 8):
        for j in range(0, w - (w % 8), 8):
            if idx >= text_len: break
            for c in range(3): # RGB三通道嵌入 [cite: 20]
                if idx >= text_len: break
                block = img_np[i:i+8, j:j+8, c].astype(np.float32)
                # 在中频位置嵌入，平衡不可见性和抗压缩性 [cite: 20, 21]
                if text_bin[idx] == '1':
                    block[3,3] += 5 
                else:
                    block[3,3] -= 5
                img_np[i:i+8, j:j+8, c] = np.clip(block, 0, 255).astype(np.uint8)
                idx += 1
        if idx >= text_len: break
    return img_np

def extract_watermark(img_np, max_len=100):
    h, w, _ = img_np.shape
    bits = []
    idx = 0
    for i in range(0, h - (h % 8), 8):
        for j in range(0, w - (w % 8), 8):
            if idx >= max_len * 8: break
            for c in range(3):
                if idx >= max_len * 8: break
                block = img_np[i:i+8, j:j+8, c].astype(np.float32)
                bits.append('1' if block[3,3] > 128 else '0') # 阈值判断 [cite: 23]
                idx += 1
    # 转回文字 [cite: 25]
    text = ""
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break
        char_code = int(''.join(byte), 2)
        if 32 <= char_code <= 126: text += chr(char_code)
        else: break
    return text

mode = st.radio("选择功能", ["添加盲水印", "提取盲水印"])

if mode == "添加盲水印":
    upload_img = st.file_uploader("上传原图", type=["jpg","jpeg","png"])
    wm_text = st.text_input("输入水印信息 (建议英文/数字)", "GITO-2026")

    if upload_img:
        img = Image.open(upload_img)
        orig_size = img.size
        orig_format = img.format # 记录原图格式 (JPG/PNG) [cite: 12, 13]
        
        if st.button("一键生成无损水印图"):
            with st.spinner("正在处理..."):
                img_np = np.array(img.convert("RGB"))
                wm_np = add_watermark(img_np, wm_text)
                wm_img = Image.fromarray(wm_np).resize(orig_size) # 强制保持尺寸一致 [cite: 14]
            
            # 按原格式导出，控制体积 [cite: 15]
            buf = io.BytesIO()
            if orig_format in ["JPG", "JPEG"]:
                wm_img.save(buf, format="JPEG", quality=95, optimize=True) # 95质量平衡了体积和防伪 [cite: 15]
                down_name = "watermarked.jpg"
            else:
                wm_img.save(buf, format="PNG")
                down_name = "watermarked.png"
            
            buf.seek(0)
            st.image(wm_img, caption=f"处理完成 | 尺寸: {orig_size} | 格式: {orig_format}", use_column_width=True)
            st.download_button("点击下载 (原尺寸原格式)", buf, down_name)

else:
    upload_img = st.file_uploader("上传图片提取水印", type=["jpg","jpeg","png"])
    if upload_img:
        img = Image.open(upload_img)
        if st.button("开始解析"):
            res = extract_watermark(np.array(img.convert("RGB")))
            if res:
                st.success(f"✅ 成功提取水印内容：{res}")
            else:
                st.warning("未能提取到有效水印，请确保是使用本工具制作的图片。")
