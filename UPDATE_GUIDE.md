# 分行业财务指标看板 · 更新手册

- 线上地址：https://ppistone.github.io/industry_profit/
- 数据源：国家统计局《全国规模以上工业企业利润》月度发布（stats.gov.cn）
- 仓库：git@github.com:ppistone/industry_profit.git（GitHub Pages 自动发布）

## 文件结构（site/ 目录）
| 文件 | 说明 |
|------|------|
| `industry_data.json` | 数据本体（42 行业 × 30 期 × 3 指标：营业收入 / 营业成本 / 利润总额），由脚本生成或更新 |
| `template.html` | **页面源模板（你只改这个文件）**，内含 `const DATA = __DATA__` 占位符 |
| `index.html` | **生成产物**，由 `template.html` + `industry_data.json` 注入得到，**不要手改** |
| `update.py` | 一键更新脚本（抓新数据 + 重生成 + 提交推送） |
| `qrcode.png` | “联系作者”二维码 |

## 一、数据更新（统计局每月约 27 日发布新一期）
在 `site/` 目录下运行：

```bash
python update.py
```

脚本自动完成：
1. 翻页发现官网最新各期发布页；
2. **仅向前新增**晚于本地最末期的新期次（不回填历史数据）；
3. 合并、重写 `industry_data.json` 并重新生成 `index.html`；
4. `git add` / `git commit` / `git push` 到 `origin/main`。

**前提**：本地 git 已配好 SSH 密钥（能 push 到 origin）。
提交后 GitHub Pages 通常 **1–3 分钟**重建生效，期间刷新可能还是旧版，稍等即可。

## 二、改版（改样式 / 加功能 / 调文案 / 改标题）
1. **只编辑 `template.html`**（源），不要直接改 `index.html`；
2. 重新生成并推送，二选一：
   - 省事：`python update.py`（会重生成 `index.html` 并自动 commit + push，即使没有新数据也会把 template 改动带上去）；
   - 或手动生成（可控）：
     ```bash
     python -c "import json;t=open('template.html',encoding='utf-8').read();d=open('industry_data.json',encoding='utf-8').read();open('index.html','w',encoding='utf-8').write(t.replace('__DATA__',json.dumps(json.loads(d),ensure_ascii=False)))"
     git add -A && git commit -m "改版说明" && git push origin main
     ```
3. 等 1–3 分钟，刷新线上页面。

## 重要约定
- **永远只改 `template.html`**，`index.html` 一律由脚本生成 → 避免两边手工改造成内容漂移（已踩过坑）。
- 同比着色遵循中国习惯：**涨 = 红、跌 = 绿**（负同比 = 绿）。
- 单月值口径：每年 1 月、2 月各取当年 1–2 月累计的一半；3 月及以后为相邻两期累计之差（差分推算，非官方单月统计，仅供趋势参考）。
- 左侧行业列表支持 **↑ / ↓** 方向键切换行业，右侧自动刷新（焦点在搜索框时同样可用）。

## 三、在本对话里更新（最省事）
直接回到这个 WorkBuddy 对话，说 **“更新数据”** 或 **“把 XX 改成 XX”**，我会跑命令、生成并推送到你的仓库，无需自己敲命令。
