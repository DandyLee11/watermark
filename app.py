import streamlit as st
import numpy as np
from PIL import Image
from invisible_watermark import WaterMark
import io

st.set_page_config(page_title="无损盲水印工具", layout="wide")
st.title("🔒 无损版AI盲水印｜尺寸不变+原格式+抗压缩")

# 强化抗压缩水印参数
bw = WaterMark(
    password_wm=123456,
    password_img=654321,
    block_shape=(8, 8),
    process_flag=True
)

mode = st.radio("选择功能", ["添加盲水印",  "提取盲水印"])

# ========== 添加盲水印（严格保持原图尺寸、格式、无损） ==========
if mode == "添加盲水印":
    upload_img = st.file_uploader("上传图片", type=["jpg","jpeg","png"])
    wm_text = st.text_input("自定义水印溯源文字", "版权专属 不可外泄")

    if upload_img:
        # 读取原图，保留原始模式和尺寸
        img = Image.open(upload_img)
        orig_size = img.size
        orig_format = img.format
        st.image(img, caption=f"原图 | 尺寸{orig_size} | 格式{orig_format}", use_column_width=True)

        if st.button("一键加盲水印（无损不变）"):
            with st.spinner("嵌入抗压缩盲水印..."):
                # 转RGB处理水印，不改变尺寸
                img_rgb = img.convert("RGB")
                img_np = np.array(img_rgb)
                # 嵌入水印
                wm_np = bw.encode_wm(img_np, wm=wm_text)
                # 转回PIL，强制还原原图尺寸
                wm_img = Image.fromarray(wm_np).resize(orig_size)

            # 按【原格式】导出，不强行转PNG
            buf = io.BytesIO()
            if orig_format in ["JPG", "JPEG"]:
                wm_img.save(buf, format="JPEG", quality=95, optimize=True)
                down_name = "原图无损带水印.jpg"
            else:
                wm_img.save(buf, format="PNG")
                down_name = "原图无损带水印.png"

            buf.seek(0)
            st.image(wm_img, caption="已加盲水印｜尺寸和原图完全一致", use_column_width=True)
            st.download_button("下载（原尺寸原格式）", buf, down_name)

# ========== 提取盲水印 ==========
else:
    upload_img = st.file_uploader("上传带水印图片", type=["jpg","jpeg","png"])
    if upload_img:
        img = Image.open(upload_img)
        st.image(img, caption="待检测图片", use_column_width=True)
        if st.button("提取盲水印信息"):
            with st.spinner("解析水印..."):
                res = bw.decode_wm(np.array(img.convert("RGB")))
            st.success(f"✅ 成功提取水印：{res}")