# Lucid (观微) - 智能高考志愿填报辅助与 RAG 风控系统

`Lucid`（观微）是一款高精度的高考志愿填报辅助系统，旨在通过科学的**等效位次化**、**高斯分布累积概率积分**、**双重推荐漏斗模型**以及**大语言模型 RAG（检索增强生成）技术**，为考生提供“极度量化、安全排雷、步步引导”的智能决策方案。

---

## 🌟 核心特色与技术

### 1. 🎯 录取概率的高斯正态分布建模 (定量决策)
摒弃传统“冲、稳、保、垫”全凭感性猜测的评估方式。`Lucid` 将高校往年最低录取位次 $R_{cutoff}$ 建模为服从正态分布的随机变量 $R_{cutoff} \sim \mathcal{N}(\mu, \sigma^2)$。根据考生的全省等效位次 $R_{user}$，精确计算出其绝对录取胜率 $P(Accept)$：
$$P(Accept) = \Phi\left(\frac{\mu - R_{user}}{\sigma}\right)$$
系统根据胜率进行严格的志愿梯度打标：
- **激进冲刺 (Reach)**: $15\% \le P < 45\%$
- **合理匹配 (Match)**: $45\% \le P < 75\%$
- **安全保底 (Safety)**: $75\% \le P < 95\%$
- **极限托底 (Fall-back)**: $P \ge 95\%$
- 对于录取胜率低于 $15\%$ 的学校，系统实行“硬性拦截剔除”，杜绝滑档。

### 2. 🌪️ 双重推荐漏斗模型
- **第一道漏斗（粗排）**：基于考生当前位次，向上和向下设定一定比例的“宽位次带宽”（上浮 $20\%$，下浮 $30\%$），在大池子中捞出近 3-5 年有录取希望的全部专业。
- **第二道漏斗（精排）**：交集过滤城市偏好（如长三角、不出省）、高校级别（985/211/双一流）、学费预算上限等硬性条件。

### 3. 🛡️ 基于 RAG 的招生章程安全风控
招生章程中往往包含体检色弱/色盲限制、单科英语分数限制、新高考选科组合硬性绑定等暗雷。
- **章程向量化**：系统将非结构化简章文本按 `~500` 字符重叠切片，使用 Google **`models/text-embedding-004`** 计算 Embedding，并存入高性能向量数据库 **ChromaDB** 中。
- **AI 智能排雷**：通过语义检索关联条款，调度 **`models/gemini-1.5-flash`** 大模型（附带离线启发式正则双重保障）对初筛志愿进行极限排雷。若触发红线（如视力不合格报医学、英语低于单科限分），直接标注 `red` 并进行自动安全拦截，切实杜绝退档。

---

## 📂 项目结构

```text
lucid/
  ├── plan/                      # 架构设计与开发计划文件夹
  │   ├── Lucid_Development_Plan.md  # 总体开发计划书
  │   ├── Database_Design.md         # 数据库与向量库表设计文档
  │   ├── Algorithm_Design.md        # 高斯概率模型与 Python 逼近算法推导
  │   └── Testing_Strategy.md        # 环境要求与分层自动化测试规范
  ├── src/                       # 🐍 系统源代码目录
  │   ├── __init__.py
  │   ├── calculator.py          # 高斯积分录取概率计算核心库 (支持 Scipy/纯 Python 逼近)
  │   ├── mapper.py              # SQLite 一分一段高精度双向映射器
  │   ├── ingester.py            # CSV / JSON 历年提档线/一分一段表原子性导入器 (CLI)
  │   ├── engine.py              # 粗排 + 精排 + 胜率打标 双重漏斗推荐引擎
  │   ├── audit_engine.py        # ChromaDB 向量检索 + Gemini 风控智能排雷引擎
  │   ├── profile_manager.py     # SQLite 考生 Profile 资料持久化管理器
  │   ├── reporter.py            # Markdown 报表多端适配导出器
  │   ├── tools.py               # ⌨️ 本地调试与测试命令行工具 (CLI)
  │   └── mcp_server.py          # 🔌 零依赖高性能 stdio-based 官方标准 MCP 服务
  ├── tests/                     # 🧪 自动化测试套件
  │   ├── test_calculator.py     # 概率计算测试
  │   ├── test_engine.py         # 推荐引擎双重漏斗测试
  │   ├── test_ingester.py       # 清洗导入与原子性回滚测试
  │   ├── test_mapper.py         # 位次映射测试
  │   ├── test_profile_manager.py# 考生资料持久化测试
  │   ├── test_regulation_ingester.py # 招生章程向量化导入测试
  │   ├── test_audit_engine.py   # AI 智能排雷与 Heuristic Fallback 测试
  │   ├── test_integration_audit.py   # 端到端整体集成流水线测试
  │   └── test_reporter.py       # 控制台 Markdown 报表导出测试
  ├── data/                      # 💾 数据库存储目录 (自动创建)
  │   ├── lucid.db               # SQLite 结构化数据库 (含 admissions & user_profiles)
  │   └── chroma_db/             # ChromaDB 向量库 (招生简章 embedding 存储)
  ├── requirements.txt           # 依赖清单
  └── lucid_skill_prompt.md      # 🤖 OpenClaw Skill 对话状态机配置文件
```

---

## ⚡ 安装与环境配置

`Lucid` 严格要求在隔离的 Python 虚拟环境中运行。

### 1. 克隆 / 下载项目
```bash
cd ~/public/lucid
```

### 2. 创建并激活虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 3. 安装依赖包
```bash
pip install -r requirements.txt
```

---

## 🚀 快速上手使用

### 步骤一：导入一分一段与历史提档线数据
在进行推荐前，需要将真实的数据文件（CSV或JSON）清洗并导入 SQLite。
```bash
# 以导入 CSV 格式数据为例 (支持断点和原子性回滚)
python3 src/ingester.py path/to/your/admissions_data.csv --db data/lucid.db --clear
```

### 步骤二：利用本地 CLI (`src/tools.py`) 进行调试

`tools.py` 提供了快速运行整套底层体系的通道：

1. **初始化/修改考生 Profiles 资料**：
   ```bash
   PYTHONPATH=. python3 src/tools.py initialize_user_profile \
     --province Zhejiang --score 635 --rank 4800 \
     --category Physics --subjects Physics,Chemistry,Biology \
     --english_score 115 --eyesight_color Normal \
     --city_preferences "Shanghai,Hangzhou"
   ```
2. **读取已保存考生资料**：
   ```bash
   PYTHONPATH=. python3 src/tools.py load_profile --user-id testuser
   ```
3. **一键运行双漏斗推荐与高斯录取概率积分（自动触发 RAG 排雷）**：
   ```bash
   PYTHONPATH=. python3 src/tools.py run_lucid_engine --user-id testuser
   ```

---

## 🔌 接入 OpenClaw 平台交互 (Skill 部署)

`Lucid`（观微）已经完全打通了与 OpenClaw 智能助理及其连接端（如飞书、Telegram 等）的交互。系统不仅提供底层的标准 MCP 工具集，还提供了完整的**本地对话状态机 Skill 交互流**：

### 1. 注册全局 MCP 服务
由于 `mcp_server.py` 是一个**零三方依赖的高性能官方标准 MCP 服务**，您可以直接将以下配置加入到 OpenClaw 的总配置文件 `~/.openclaw/openclaw.json` 中的 `"mcp"."servers"` 栏：

```json
"mcp": {
  "servers": {
    "lucid": {
      "enabled": true,
      "command": "/home/designer/public/lucid/venv/bin/python",
      "args": ["/home/designer/public/lucid/src/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/home/designer/public/lucid",
        "GOOGLE_API_KEY": "您的_GEMINI_API_KEY",
        "GEMINI_API_KEY": "您的_GEMINI_API_KEY"
      }
    }
  }
}
```

### 2. 部署为 OpenClaw Workspace Skill
要将 Lucid 作为 OpenClaw 的原生 Skill 启用，请在您的 OpenClaw 运行环境中建立软连接：

```bash
# 在 OpenClaw 扫描的 workspace/skills/ 目录下创建软连接指向 Lucid
ln -s /home/designer/public/lucid /home/designer/.openclaw/workspace/skills/lucid
```

软连接创建后，OpenClaw 会在启动时自动扫描并加载本 Skill 目录（包含 `SKILL.md`，`skill-card.md` 以及 `references/` 等规范文件）。

---

## 🚀 用户对话使用方法 (How to Use)

部署完成后，任何连接到 OpenClaw 的聊天终端（如飞书、Telegram）均可无缝开启“观微（Lucid）高考志愿填报指导”。

### 📢 1. 触发 Skill 启动
在聊天窗口中发送自然语言意图来激活此 Skill：
* *“我想填报志愿”*
* *“启动观微志愿填报助手”*
* *“帮我推荐一下高考志愿”*

### 🔄 2. 状态机分步引导交互流 (4 步提问法)

系统被触发后，Lucid 助手会以**冷静、客观、充满人文关怀的语气（禅道观心）**切入，引导考生分步输入，每次只提问 1-2 个相关问题，杜绝一次性索要大量信息的压迫感。

#### 📍 步骤一：建立基准坐标 (State 1)
* **AI 引导**：*“你好，我是观微高考志愿决策 AI。在开始数学计算前，位次是跨越年份波动的唯一硬通货，我们需要先建立基准坐标。请问：你的所在省份、高考总分及全省排位位次是多少？另外你的选科组合是什么？”*
* **用户输入**：*“浙江，635分，全省排位 4800，物理、化学、生物”*

#### 🛡️ 步骤二：探查硬性约束 (State 2)
* **AI 引导**：*“已锁定你的等效位次基准。许多高分滑档并非分数不够，而是意外触发了高校招生章程中的红线。为了帮你建立安全防火墙，请告诉我：你的英语单科成绩是多少？身体有无色盲、色弱等体检限报情况？”*
* **用户输入**：*“英语 115 分，视力无色盲色弱，一切正常”*

#### 🗺️ 步骤三：挖掘主观偏好 (State 3)
* **AI 引导**：*“非常好，风控排雷的安全防火墙已经建立。为了精排过滤出最心仪的范围，请问：你期望去哪些地域或城市（如长三角、不出省）？对院校层级（985/211/双一流/不限）或特定专业大类有何偏好、排斥，或者学费预算有无特殊要求？”*
* **用户输入**：*“想去上海或杭州，倾向 985 或双一流，学费正常”*

#### 📊 步骤四：信息 Checkpoint 确认与报表生成 (State 4)
* **AI 引导**：会汇总之前的所有参数：
  * *“好的，为你整理最终画像 Checkpoint：\n- 成绩位次：浙江 635 分，排位 4800（物化生）\n- 硬性限制：英语 115，体检无限制\n- 偏好设定：上海/杭州，首选双一流院校\n请核对以上画像，若无误，请输入‘确认’。我将立刻为你静默调度推荐引擎与 RAG 章程审查。”*
* **用户输入**：*“确认”*

---

### 📈 3. 获取《观微志愿决策报表》

用户回复“确认”后，AI 会自动调用后台工具（`initialize_user_profile`, `run_lucid_engine`, `run_rag_audit`），执行粗排、精排和高斯分布概率胜率推演，结合 ChromaDB 进行章程内容向量化审查排雷，并在聊天端直接输出精美的 Markdown 报表：

#### 📝 报表示例：

#### 🎓 观微高考志愿决策推荐表 (用户: testuser)
> **基准坐标**：浙江省 635分 (排位: 4800) | 物理、化学、生物 | 英语: 115分 | 体检: 正常

| 推荐梯度 | 高校名称 | 专业名称 | 录取胜率 $P(Accept)$ | 招生章程 RAG 排雷结论 |
| :--- | :--- | :--- | :--- | :--- |
| **激进冲刺 (Reach)** | 复旦大学 | 电子信息类 | $22.4\%$ | ✅ 经章程审查，无体检与单科限制，服从调剂不退档。 |
| **合理匹配 (Match)** | 浙江大学 | 计算机科学与技术 | $68.5\%$ | ✅ 经章程审查，物理选科匹配，无体检红线限制。 |
| **合理匹配 (Match)** | 上海交通大学 | 机械工程（中外合作）| $55.0\%$ | ⚠️ 提示：英语 115 分符合要求，但该专业年学费 8 万元，请确认预算。 |
| **安全保底 (Safety)** | 同济大学 | 土木工程 | $88.2\%$ | ✅ 经章程审查，无特殊单科与体检要求。 |
| **极限托底 (Fall-back)** | 华东师范大学 | 数据科学与大数据技术 | $98.1\%$ | ✅ 经章程审查，完全符合选科与健康标准，完美闭环。 |

*注：若用户的偏好与分数实力产生巨大数学冲突（如 5 万名希望“稳”上清华），AI 将会展示科学的概率胜率（如 $<0.01\%$），并温和客观地引导用户重新调整偏好参数，确保填报万无一失。*

---

## 🧪 运行自动化测试 ( pytest )

`Lucid` 遵循高标准的可测试粒度规范，包含 30 个覆盖了各个核心算法和端到端集成链路的测试。涉及权限相关的测试使用内置的全局测试账号。

**标准测试账号：**
- 用户名：`testuser`
- 密码：`testpassword123`
- 邮箱：`testuser@example.com`

**运行测试命令：**
```bash
# 运行全部 30 个自动化测试
pytest tests/
```

---

## 📝 许可证与注意事项

- **免责声明**：本系统计算出的“录取胜率/概率”以及通过 AI 招生章程审查得出的“排雷说明”仅供考生及家长参考。正式填报时请务必再次校对省教育考试院和各高校官方发布的纸质简章。
- **License**: MIT License. 
