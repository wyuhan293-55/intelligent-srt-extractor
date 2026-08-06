# -*- coding: utf-8 -*-
# ==================================================================
# Medical Aesthetics Term Corrections for Whisper ASR
# 医美专业术语词典 — 用于修正 Whisper 转录的常见误识别
# ==================================================================
# Usage:
#   from lexicon.medical_terms import TERM_CORRECTIONS, apply_term_fix
#   fixed_text = apply_term_fix(original_text)
#
# To add new terms, just append to TERM_CORRECTIONS dict:
#   "whisper误识词": "正确术语"
# ==================================================================
# Version: 1.0.0
# License: MIT
# ==================================================================

TERM_CORRECTIONS = {

    # ──────────── 鼻整形 (Rhinoplasty) ────────────
    # 膨体 (ePTFE implant) — Whisper 最常见的误识别群
    "棚体": "膨体", "棱体": "膨体", "彭体": "膨体", "朋体": "膨体",
    "头体": "膨体", "头铁": "膨体", "藤体": "膨体",

    # 驼峰 (dorsal hump)
    "和风": "驼峰", "驼风": "驼峰", "和峰": "驼峰", "驼封": "驼峰",
    "突风": "驼峰", "脱风": "驼峰",

    # 下颌 (mandible / chin)
    "下和": "下颌", "下壳": "下颌", "下河": "下颌",

    # 鼻唇角 (nasolabial angle)
    "住上唇角": "鼻唇角", "比上唇角": "鼻唇角", "闭上唇角": "鼻唇角",
    "上从讲": "鼻唇角", "上存角": "鼻唇角",

    # 鼻背 (nasal dorsum)
    "被背": "鼻背", "鼻被": "鼻背",

    # 鼻尖 (nasal tip)
    "笔尖": "鼻尖",

    # 鼻翼 (nasal alar)
    "鼻易": "鼻翼", "鼻意": "鼻翼",

    # 鼻小柱 (columella)
    "鼻小住": "鼻小柱", "鼻小注": "鼻小柱", "比小柱": "鼻小柱",

    # 鼻中隔 (nasal septum)
    "鼻中格": "鼻中隔", "比中隔": "鼻中隔",

    # 软骨 (cartilage)
    "软鼓": "软骨",

    # 耳软骨 (ear cartilage)
    "儿软骨": "耳软骨",

    # 鼻基底 (nasal base)
    "笔基底": "鼻基底", "鼻基地": "鼻基底",

    # 假体 (implant) — 跨项目通用
    "甲体": "假体", "假题": "假体", "年体": "假体",

    # ──────────── 眼部整形 (Blepharoplasty) ────────────
    # 提肌 (levator muscle)
    "提鸡": "提肌", "提激": "提肌", "提积": "提肌",

    # 上睑提肌 (levator palpebrae superioris)
    "上简提肌": "上睑提肌", "上尖提肌": "上睑提肌", "上减提肌": "上睑提肌",

    # 眶隔脂肪 (orbital septum fat)
    "矿阁脂肪": "眶隔脂肪", "框格脂肪": "眶隔脂肪", "光隔脂肪": "眶隔脂肪",

    # 内眦 / 外眦 (inner / outer canthus)
    "内资": "内眦", "外资": "外眦", "内置": "内眦",

    # 睑板 (tarsal plate)
    "简版": "睑板", "减版": "睑板",

    # 双眼皮 (double eyelid)
    "双脸皮": "双眼皮",

    # 开眼角 (canthoplasty)
    "开眼脚": "开眼角", "开眼较": "开眼角",

    # ──────────── 胸部整形 (Breast Augmentation) ────────────
    # 下皱襞 (inframammary fold)
    "下皱壁": "下皱襞", "下周闭": "下皱襞", "下轴闭": "下皱襞",
    "下周必": "下皱襞", "下皱闭": "下皱襞",

    # 傲诺拉 (Alora implant brand)
    "浪诺拉": "傲诺拉", "傲洛拉": "傲诺拉", "奥诺拉": "傲诺拉",
    "傲罗拉": "傲诺拉", "奥若拉": "傲诺拉",

    # 星熠 (implant product line)
    "新艺": "星熠", "心意": "星熠", "新一": "星熠", "星艺": "星熠", "星翼": "星熠",

    # CC 体积 (implant volume)
    "240皙皙": "240CC", "240嘻嘻": "240CC",
    "皙皙": "CC", "嘻嘻": "CC",

    # 毛面 / 光面 (textured / smooth surface)
    "毛免": "毛面", "毛冕": "毛面",
    "光绵": "光面", "光免": "光面",

    # 隆胸 (breast augmentation)
    "隆兄": "隆胸", "龙胸": "隆胸", "隆凶": "隆胸",

    # 放置 (placement)
    "放制": "放置",

    # 剥离 (dissection)
    "拨离": "剥离",

    # 切口 (incision)
    "切扣": "切口",

    # 形态 (shape/form)
    "型态": "形态",

    # ──────────── 通用手术术语 (General Surgical) ────────────
    # 术后 (post-op)
    "术号": "术后", "速后": "术后",

    # 术前 (pre-op)
    "速前": "术前", "书前": "术前",

    # 拆线 (suture removal)
    "拆现": "拆线", "拆县": "拆线",

    # 缝合 (suture)
    "逢合": "缝合", "封合": "缝合",

    # 麻醉 (anesthesia)
    "马醉": "麻醉",

    # 医生 / 患者
    "一升": "医生", "一声": "医生",

    # 手术 (surgery)
    "手速": "手术", "手竖": "手术",

    # 恢复期 (recovery period)
    "恢復期": "恢复期", "恢复起": "恢复期",

    # 消肿 (reduce swelling)
    "萧肿": "消肿", "消总": "消肿",

    # ──────────── 皮肤/注射类 (Dermatology / Injection) ────────────
    # 玻尿酸 (hyaluronic acid)
    "玻鸟酸": "玻尿酸", "博尿酸": "玻尿酸", "波尿酸": "玻尿酸",

    # 肉毒素 (botulinum toxin)
    "肉读素": "肉毒素", "肉度素": "肉毒素",

    # 水光针 (skin booster injection)
    "水光真": "水光针", "水光增": "水光针",

    # 线雕 (thread lift)
    "现雕": "线雕", "线调": "线雕",

    # 光电 (laser/IPL)
    "光店": "光电", "光垫": "光电",

    # 热玛吉 (Thermage)
    "热马吉": "热玛吉", "热麻吉": "热玛吉",

    # ──────────── 唇部/面部 (Lip / Facial) ────────────
    # M唇 (M-shaped lip)
    "M纯": "M唇", "M春": "M唇",

    # 微笑唇 (smile lip surgery)
    "微小唇": "微笑唇", "微小纯": "微笑唇",

    # 人中 (philtrum)
    "人钟": "人中",
}


# ==================================================================
# Helper functions
# ==================================================================

def apply_term_fix(text: str) -> str:
    """对单段文本应用术语修正（长匹配优先，避免短词误替换）。"""
    for wrong, correct in sorted(TERM_CORRECTIONS.items(), key=lambda x: -len(x[0])):
        if wrong in text and wrong != correct:
            text = text.replace(wrong, correct)
    return text


def apply_term_fix_to_segments(segments: list) -> list:
    """对全部转录段批量修正术语。"""
    for seg in segments:
        seg['text'] = apply_term_fix(seg.get('text', ''))
    return segments
