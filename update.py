# -*- coding: utf-8 -*-
"""
一键更新：国家统计局「规模以上工业企业利润」分行业财务指标看板
功能：抓取最新各期发布页 -> 解析分行业表3 -> 合并 -> 重新生成 index.html -> 提交并推送 GitHub Pages
运行：python update.py   （需要已配置好 git 且能 push 到 origin，SSH 密钥或凭据已就绪）
"""
import re, json, os, sys, subprocess, urllib.request, urllib.error, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "industry_data.json")
TPL_PATH  = os.path.join(HERE, "template.html")
OUT_PATH  = os.path.join(HERE, "index.html")
REMOTE   = "origin"   # 仓库需已添加远程 origin（git@github.com:ppistone/industry_profit.git）

CANON = ["总计","煤炭开采和洗选业","石油和天然气开采业","黑色金属矿采选业","有色金属矿采选业",
"非金属矿采选业","开采专业及辅助性活动","其他采矿业","农副食品加工业","食品制造业",
"酒、饮料和精制茶制造业","烟草制品业","纺织业","纺织服装、服饰业","皮革、毛皮、羽毛及其制品和制鞋业",
"木材加工和木、竹、藤、棕、草制品业","家具制造业","造纸和纸制品业","印刷和记录媒介复制业",
"文教、工美、体育和娱乐用品制造业","石油、煤炭及其他燃料加工业","化学原料和化学制品制造业",
"医药制造业","化学纤维制造业","橡胶和塑料制品业","非金属矿物制品业","黑色金属冶炼和压延加工业",
"有色金属冶炼和压延加工业","金属制品业","通用设备制造业","专用设备制造业","汽车制造业",
"铁路、船舶、航空航天和其他运输设备制造业","电气机械和器材制造业","计算机、通信和其他电子设备制造业",
"仪器仪表制造业","其他制造业","废弃资源综合利用业","金属制品、机械和设备修理业",
"电力、热力生产和供应业","燃气生产和供应业","水的生产和供应业"]
CANON_NORM = {re.sub(r"[\s、，,（）()·]", "", c): c for c in CANON}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def norm(s):
    return re.sub(r"[\s、，,（）()·]", "", s)

def strip_tags(x):
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", x))

def parse_num(s):
    s = strip_tags(s)
    if s in ("", "…", "—", "-"):
        return None
    s = s.replace(",", "")
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group(0)) if m else None

def find_table(html):
    for t in re.findall(r"<table.*?</table>", html, re.S):
        if "煤炭开采" in t and "利润总额" in t:
            return t
    return None

def parse_page(url):
    try:
        html = http_get(url)
    except Exception as e:
        print(f"  ! 下载失败 {url}: {e}")
        return None
    tab = find_table(html)
    if tab is None:
        print(f"  ! 未找到分行业表格 {url}")
        return None
    out = {}
    for r in re.findall(r"<tr.*?</tr>", tab, re.S):
        tds = re.findall(r"<td.*?</td>", r, re.S)
        if not tds:
            continue
        name = strip_tags(tds[0])
        if not name or name == "行业":
            continue
        nums = [parse_num(td) for td in tds[1:]]
        if len(nums) < 5:
            continue
        while len(nums) < 6:
            nums.append(None)
        key = norm(name)
        if key in CANON_NORM:
            out[CANON_NORM[key]] = {"revenue": nums[0], "cost": nums[2], "profit": nums[4]}
    return out

def discover_periods():
    """从最新发布栏目翻页，找出所有《XX年1—X月份全国规模以上工业企业利润》发布页。"""
    found = {}
    for i in range(0, 31):
        url = "https://www.stats.gov.cn/sj/zxfb/" + ("" if i == 0 else f"index_{i}.html")
        try:
            html = http_get(url)
        except Exception:
            break
        for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if "工业企业利润" in txt and "规模" in txt and "1" in txt and "月份" in txt:
                # 跳过年度汇总（如"2025年全国..."），只取 X年1—X月份
                mm = re.search(r"(\d{4})年1[—-](\d{1,2})月份", txt)
                if not mm:
                    continue
                year, month = mm.group(1), int(mm.group(2))
                period = f"{year}-{month:02d}"
                rel = href.lstrip("./")
                found[period] = "https://www.stats.gov.cn/sj/zxfb/" + rel
    return found

def build_records_from_existing(existing):
    recs = {}
    if not existing:
        return recs
    periods = existing.get("periods", [])
    data = existing.get("data", {})
    for idx, p in enumerate(periods):
        rec = {}
        for ind, vals in data.items():
            rec[ind] = {"revenue": vals["revenue"][idx],
                        "cost": vals["cost"][idx],
                        "profit": vals["profit"][idx]}
        recs[p] = rec
    return recs

def main():
    print("== 1/5 发现统计局发布页 ==")
    found = discover_periods()
    if not found:
        print("未能从官网发现任何发布页，请检查网络/官网结构。")
        sys.exit(1)
    print(f"  官网找到 {len(found)} 期：{', '.join(sorted(found))}")

    existing = None
    if os.path.exists(DATA_PATH):
        existing = json.load(open(DATA_PATH, encoding="utf-8"))
    old_periods = set(existing.get("periods", [])) if existing else set()
    print(f"  本地已有 {len(old_periods)} 期：{', '.join(sorted(old_periods))}")

    recs = build_records_from_existing(existing)
    # 仅向前更新：只接受晚于本地已有最末期的新期次，避免回填历史数据
    max_old = max(old_periods) if old_periods else ""
    new_periods = [p for p in sorted(found) if p not in old_periods and p > max_old]
    if old_periods and new_periods:
        print(f"  本地最末期 {max_old}，向前新增 {len(new_periods)} 期")
    print(f"== 2/5 抓取新增期次（{len(new_periods)} 期）==")
    for p in new_periods:
        print(f"  -> {p}: {found[p]}")
        parsed = parse_page(found[p])
        if parsed:
            recs[p] = parsed
            print(f"     解析到 {len(parsed)} 个行业")
        else:
            print(f"     ! 解析失败，跳过 {p}")

    all_periods = sorted(set(recs.keys()) | old_periods)
    print(f"== 3/5 合并为 {len(all_periods)} 期 ==")

    labels = {}
    for p in all_periods:
        y, m = p.split("-")
        labels[p] = f"{y}年1-{int(m)}月" if int(m) > 2 else f"{y}年1-2月"
    if "2025-12" in labels:
        labels["2025-12"] = "2025年1-12月"

    data = {"meta": {"source": "国家统计局《全国规模以上工业企业利润》月度发布 (stats.gov.cn)",
                     "note": "累计值，单位：亿元",
                     "updated": __import__("datetime").date.today().isoformat()},
            "periods": all_periods,
            "period_labels": [labels[p] for p in all_periods],
            "industries": CANON,
            "data": {}}
    missing = []
    for c in CANON:
        rev, cost, prof = [], [], []
        for p in all_periods:
            rec = recs.get(p, {}).get(c)
            if rec:
                rev.append(rec["revenue"]); cost.append(rec["cost"]); prof.append(rec["profit"])
            else:
                rev.append(None); cost.append(None); prof.append(None)
                missing.append(f"{c}@{p}")
        data["data"][c] = {"revenue": rev, "cost": cost, "profit": prof}
    if missing:
        print("  部分行业缺失：", ", ".join(missing[:20]), "..." if len(missing) > 20 else "")
    json.dump(data, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  已写 {DATA_PATH}")

    print("== 4/5 重新生成 index.html ==")
    tpl = open(TPL_PATH, encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    open(OUT_PATH, "w", encoding="utf-8").write(html)
    print(f"  已写 {OUT_PATH}")

    print("== 5/5 提交并推送到 GitHub ==")
    for cmd in [
        ["git", "add", "-A"],
        ["git", "commit", "-m", f"数据更新至 {all_periods[-1]}（{len(all_periods)}期）"],
        ["git", "push", REMOTE, "main"],
    ]:
        r = subprocess.run(cmd, cwd=HERE)
        if r.returncode != 0:
            print(f"  ! 命令失败：{' '.join(cmd)} (rc={r.returncode})")
            sys.exit(r.returncode)
    print("完成。站点将在 GitHub Pages 几分钟内更新。")

if __name__ == "__main__":
    main()
