import streamlit as st
import numpy as np
from PIL import Image
import io
import os
import cv2
import sys
import zipfile

# ============================================================
# 1. 强制路径修复 — 解决 Streamlit 云端找不到本地包的问题
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from blind_watermark import WaterMark
except ImportError:
    st.error(
        "❌ 找不到 blind_watermark 算法库！\n\n"
        "请确认 GitHub 仓库根目录下存在 blind_watermark/ 文件夹，"
        "且文件夹内包含 __init__.py、blind_watermark.py、bwm_core.py、pool.py"
    )
    st.stop()

# ============================================================
# 2. 页面配置
# ============================================================
st.set_page_config(
    page_title="GITO 盲水印 · 批量版",
    page_icon="🛡️",
    layout="wide"
)
st.title("🛡️ GITO 品牌保护 · 批量频域盲水印工具")
st.caption("支持批量上传 · 尺寸完全不变 · 肉眼不可见的版权水印")

# ============================================================
# 3. 固定密钥（生成和提取必须用同一套密钥）
# ============================================================
PWD_IMG = 1
PWD_WM  = 1

# ============================================================
# 4. 核心函数
# ============================================================

def embed_watermark(image_bytes: bytes, filename: str, text: str):
    """
    嵌入盲水印
    - 保持原始图片尺寸（宽高像素完全不变）
    - JPEG 以 quality=85 输出（控制体积）
    - PNG 无损输出
    返回: (处理后字节, 扩展名)
    """
    ext = filename.rsplit('.', 1)[-1].lower()
    pid = os.getpid()
    temp_in  = f"_tmp_in_{pid}.png"
    temp_out = f"_tmp_out_{pid}.png"

    try:
        # 打开原图，记录原始尺寸
        img = Image.open(io.BytesIO(image_bytes))
        original_size = img.size   # (width, height)
        img.save(temp_in)

        # 嵌入水印（兼容性修复：直接操作属性，跳过报错的 read_img）
        bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
        bwm.img = cv2.imread(temp_in)
        bwm.read_wm(text, mode='str')
        bwm.embed(temp_out)

        # 读回结果
        wm_img = Image.open(temp_out)

        # 保险：若算法意外改变尺寸则强制还原
        if wm_img.size != original_size:
            wm_img = wm_img.resize(original_size, Image.LANCZOS)

        buf = io.BytesIO()
        if ext in ('jpg', 'jpeg'):
            wm_img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
            out_ext = "jpg"
        else:
            wm_img.save(buf, format="PNG", optimize=True)
            out_ext = "png"

        return buf.getvalue(), out_ext

    finally:
        # 清理临时文件
        for f in (temp_in, temp_out):
            if os.path.exists(f):
                os.remove(f)


def extract_watermark(image_bytes: bytes, wm_len: int) -> str:
    """
    从图片提取盲水印
    返回: 水印文字字符串
    """
    pid = os.getpid()
    temp_ext = f"_tmp_ext_{pid}.png"
    try:
        with open(temp_ext, "wb") as f:
            f.write(image_bytes)

        # 兼容性修复：直接操作属性
        bwm = WaterMark(password_img=PWD_IMG, password_wm=PWD_WM)
        bwm.img_wm = cv2.imread(temp_ext)
        return bwm.extract(wm_shape=wm_len, mode='str')
    finally:
        if os.path.exists(temp_ext):
            os.remove(temp_ext)


# ============================================================
# 5. 界面 — 两个 Tab
# ============================================================
tab1, tab2 = st.tabs(["📤 批量添加盲水印", "🔍 提取 / 验证水印"])

# ──────────────────────────────────────────
# Tab 1：批量加水印
# ──────────────────────────────────────────
with tab1:
    uploads = st.file_uploader(
        "上传图片（可同时选多张，支持 JPG / PNG）",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    text = st.text_input("水印文字（建议：品牌名 + 年份）", value="GITO-2026")
    wm_length = len(text)
    st.info(f"📌 当前水印长度：**{wm_length}**  ← 提取验证时必须填这个数字，请务必记好！")

    if uploads:
        st.write(f"已选中 **{len(uploads)}** 张图片，点击下方按钮开始处理。")

    if uploads and st.button("🚀 开始批量加水印", type="primary"):
        results  = []   # [(输出文件名, bytes)]
        failures = []   # [(原文件名, 错误信息)]

        progress = st.progress(0, text="准备中…")
        status   = st.empty()

        for idx, up in enumerate(uploads):
            status.text(f"正在处理：{up.name}  ({idx + 1} / {len(uploads)})")
            try:
                out_bytes, out_ext = embed_watermark(up.getvalue(), up.name, text)
                base     = up.name.rsplit('.', 1)[0]
                out_name = f"{base}_wm.{out_ext}"
                results.append((out_name, out_bytes))
            except Exception as e:
                failures.append((up.name, str(e)))

            progress.progress((idx + 1) / len(uploads))

        status.empty()
        progress.empty()

        # ── 成功结果 ──
        if results:
            st.success(f"✅ 成功处理 {len(results)} / {len(uploads)} 张")
            st.warning(f"⚠️ 重要：提取水印时，字符长度请填 **{wm_length}**")

            if len(results) == 1:
                # 单张：直接预览 + 下载
                name, data = results[0]
                st.image(data, caption=name)
                st.download_button("📥 下载此图片", data, file_name=name)
            else:
                # 多张：打包 ZIP 下载
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for name, data in results:
                        zf.writestr(name, data)
                zip_buf.seek(0)

                st.download_button(
                    label=f"📦 下载全部 {len(results)} 张（ZIP 打包）",
                    data=zip_buf.getvalue(),
                    file_name="GITO_watermarked.zip",
                    mime="application/zip"
                )

                # 预览前 3 张
                st.subheader("预览（前 3 张）")
                cols = st.columns(min(3, len(results)))
                for i, (name, data) in enumerate(results[:3]):
                    cols[i].image(data, caption=name, use_column_width=True)

        # ── 失败列表 ──
        if failures:
            st.error(f"❌ {len(failures)} 张处理失败：")
            for fname, err in failures:
                st.write(f"- **{fname}**：{err}")


# ──────────────────────────────────────────
# Tab 2：提取验证
# ──────────────────────────────────────────
with tab2:
    up_verify = st.file_uploader(
        "上传待验证的图片",
        type=["jpg", "jpeg", "png"],
        key="verify_uploader"
    )
    wm_len_input = st.number_input(
        "水印字符长度（加水印时页面显示的那个数字）",
        min_value=1,
        max_value=200,
        value=9
    )

    if up_verify and st.button("🔎 开始验证", type="primary"):
        with st.spinner("正在从频域提取水印信息…"):
            try:
                result = extract_watermark(up_verify.getvalue(), int(wm_len_input))
                if result and result.strip():
                    st.success(f"✅ 识别到版权信息：**{result}**")
                else:
                    st.warning(
                        "⚠️ 未检测到有效水印。\n\n"
                        "可能原因：① 字符长度填错了  ② 图片经过严重压缩/裁剪  ③ 不是本工具生成的图片"
                    )
            except Exception as e:
                st.error(
                    f"❌ 提取失败：字符长度不匹配或图片已被破坏。\n\n"
                    f"详细错误：{e}"
                )
