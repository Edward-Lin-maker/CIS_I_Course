# AGENTS.md — CIS I (JHU 601.455/655) Assignment 2

本文件是本作业唯一的规则文件，所有 AI 助手共用。Claude Code 通过 CLAUDE.md 中的 `@AGENTS.md` 加载它；其他工具（Codex、ChatGPT 等）请先读本文件。
修改规则只改这里。本文件每次会话都会加载，请保持简短，详细内容放在 `docs/` 中按需读取。

## 1. 项目概述
- 任务：笛卡尔机器人（3 平移 + 3 转动关节）运动学标定。用 tracker 测量，估计真实运动学，实现 ImprovedFwdKins / ImprovedInvKins。
- 目标：全工作空间 ‖α‖ ≤ 1e-3 rad、‖ε‖ ≤ 0.2 mm；模拟标定时间 t_elap 尽量短；程序运行 ≤ 10 min。
- 截止日期：2026-11-03（以课程 schedule 为准）。

## 2. 工作准则（必须遵守）
- 回答用中文。**除本文件外，所有文件一律用英文**（reference、log、报告、代码、注释），保留讲义和题目原文的术语与记号。
- 代码用 Python（numpy）。回答简洁，先给结论再给推导。
- 对话中的公式用 Unicode 写在 `代码格式` 里（如 `‖Δa_{m,k}‖ ≤ δ_markers`），不用 `$…$`；LaTeX 只用于 `.tex` 文件。
- **不得修改 `assignment2/` 以外的任何文件**（包括仓库根目录的 `.gitignore`、`src/`、`assignment1/`），只读可以。唯一例外：根 `.gitignore` 中忽略 `report/build/` 的一行（用户同意）。
- **默认只回答问题。** 写 LaTeX、改代码、建立或修改文件、读仓库代码、运行命令，都只在用户明确要求时才做。例外：原文没写的内容可直接查本地仓库，不必另行请求（见第 3 节）。
- **先理论后应用。** 先完成理论推导（LaTeX），再做场景设计、标定流程和代码。不要提前设计流程或写代码。
- 节省 token：只读当前任务需要的文件或章节，不要整篇读报告或整份 PDF；需要公式或参数时先查 `docs/course_reference.md`。
- 忠实原文：题目要求以 `docs/2026_assignment_2.pdf` 为准；原文未给的数值写 "not specified"；原文的笔误和不一致保留原写法并单独标注，不擅自修正。
- 撰写报告的 notation 时，同步更新 `course_reference.md` 的 Part 3.3（只记记号、含义和代码变量；推导只写在 LaTeX，不进 reference）。发现原文疑似笔误：先在对话中提出并给出建议改法，用户确认后记入 `course_reference.md` Part 3.2（原文 → 改为，一行）。阶段结束时，把对话中得到的非显然澄清和阶段性结论蒸馏（每条先写依据再写结论，不写推断、不写显而易见的内容），经用户确认后记入 Part 3.4。
- 报告只写符合报告逻辑的内容（问题、方法、推导、假设、结果）。对话中的问答、澄清和讨论过程不写进报告，也不为此加脚注或强调性说明；原文笔误只在影响推导或实现时才在报告中简要说明。

## 3. 文件索引
```
assignment2/
├── AGENTS.md / CLAUDE.md
├── README.md                 课程仓库说明（环境、notebook 流程、报告要求）
├── src/robot.py, src/simulation/   课程提供，不要修改
├── src/student/              学生代码：metrics.py, registration.py, workflow.py, kinematics.py
├── tests/                    test_simulation.py（提供）, test_student.py（部分 TODO）
├── notebooks/assignment2_template.ipynb   驱动整个流程
├── docs/
│   ├── 2026_assignment_2.pdf  题目原文（权威）
│   ├── course_reference.md    Part 1 讲义压缩 | Part 2 A1 报告精简（格式） | Part 3 A2 任务精简与理解（3.2 笔误、3.3 记号、3.4 澄清与阶段性结论）
│   ├── a1_report.tex          A1 报告完整 LaTeX（格式参考，少读）
│   └── progress_log.md        操作日志（按需读取，见第 5 节）
└── report/
    ├── main.tex               导言区 + \subfile 各章节（各章可单独编译）
    ├── sections/01_introduction … 07_results.tex   每次只读、只改一个章节
    └── figures/
```
- A2 的代码从 `../assignment1/src` 导入 Tracker、MarkerBody 等，须保留整个 CIS_I_Course 仓库。
- 读代码以 `assignment2/src/` 为准：只有 A2 代码显式 import、或题目/代码明说要用时，才追到 `assignment1/src/` 里对应的那部分，并注明出处（A1/A2 文件）；A2 未导入的 A1 代码和常量（如 A1 的 `SENSOR_NOISE_STD = 0.02`）不得当作 A2 的行为。
- 原文没写的内容（用法、流程、数值等）直接查本地仓库，不必另行请求：先查 A2 的 `src/`、`notebooks/`、`tests/`、`README.md`，找不到再查本地整个 CIS_I_Course 仓库（A2 未导入的部分只作参考，按上一条处理）。回答中注明每条来自题目原文还是代码（写文件名）；都找不到时才可推断，并明确标为推断。
- 课程远程仓库 https://github.com/LCSR-CIIS/CIS_I_Course/tree/main 只在用户明确要求时才查（如对照本地文件被修改前的原始版本）。
- 题目中的函数名在代码里是 snake_case（CreateRobot → simulation.create_robot）。
- Ground truth（rob.actual_ee_pose、ground_truth_parameters、*_truth、actual_* 等）只能用于验证、调试和报告，不得用于标定。

## 4. 记号约定
- Taylor 记法：F = Frame(R, p)，F·b = Rb + p；F_{x,y} 表示 y 相对 x 的位姿。
- 小误差：ΔR(α) ≈ I + sk(α)，ΔF = Frame(ΔR(α), ε)。
- 误差乘在哪一侧按题目原文：F_tracker、F_we、F_ee 为右乘 F* = F·ΔF；F_mB、F_rob 为左乘 F* = ΔF·F。
- 上标 * 表示真实值，^ 表示估计值，无标记表示名义值（沿用 A1）。
- 题目 p3 中 F*_we 的误差符号与 p5 精度指标的 ΔF_ee 同名，报告里前者记为 ΔF_we。

## 5. 日志与 Git 流程
- **开始工作前**：先 `git pull`（可能在多台电脑上协作），并检查本机工具（见第 7 节）。
- **每次修改文件后**（仅限用户允许的修改）：在 `docs/progress_log.md` 的 `## Pending` 区末尾追加一行：`- MM-DD HH:MM | <agent (model)> | <files> | <brief change>`。追加时不需要读整个文件。`report/` 下记录 `main.tex`、`sections/`、`figures/` 的修改；`build/` 和临时预览章节不记录。
- **每次 commit 之前**（用户说"更新 log"，或让 agent 代为 commit 时）：
  1. 在 Commits 区找到最后一个号为 `TBD` 的块，用 `git log -1 --format='%h %ad %s'` 等命令查出它对应的 commit，补上号，同时把第 6 节 Current phase commits 里对应的 `TBD` 改成该 hash；用 `git log origin/assignment2..HEAD` 判断各块是否已 push，并更新状态。
  2. 新建一个块，号写 `TBD`，把 Pending 里的条目归并进去，然后清空 Pending。
  3. 更新本文件第 6 节：在 Current phase commits 小节末尾追加一行 `- TBD | MM-DD | <commit message>`，并勾选已完成的项。阶段完成时，把该小节压缩成 Completed phases 里的一行，只列 hash，详情查 log。
  4. 日志、本文件和工作改动放进同一个 commit 一起提交。
- 块的格式：`### <hash|TBD> | YYYY-MM-DD HH:MM | "<commit message>" | <pushed|not pushed|—>`，下面写 Agent、Changes、Files。
- 只有在最后一次提交之后，才单独提交一个 `log: fill hash for <hash>` 来补上最后一个号（同时把第 6 节里对应的 `TBD` 改成该 hash）；`log:` 开头的 commit 不记入日志。
- 只暂存 `assignment2/` 下的文件（以及上述根 `.gitignore` 例外），不要提交 `src/.DS_Store` 等外部文件。

## 6. Progress
### Plan（只展开当前阶段；后续阶段的已定细节见 progress_log 的 Phase 0 planning record）
- [x] Phase 0 Setup（文件结构、reference、规则、日志流程）
- [x] Phase 1 Line-by-line reading（Seg 1–6）
- [x] Phase 2 Variable table（`report/sections/02_variables.tex`；结论见 course_reference Part 3.4）
- [ ] **Phase 3 Theory**（当前阶段）→ `report/sections/03_mathematical_approach.tex`
- [ ] Phase 4 Design & code（src/student/、unit tests）
- [ ] Phase 5 Results & report（多 seed 结果表、其余章节）

### Current phase commits（Phase 3；阶段完成后压缩进下方一行）
- c0c22e1 | 10-25 | Reference: resolve tentative handout corrections in Part 3.2
- TBD | 10-26 | Phase 3: Mathematical Approach draft (error model, gauges, spacing, budget, IK)

### Completed phases
- Phase 0 Setup | 2026-10-20 ~ 10-23 | Claude (desktop app, Opus 5.5) | commits: 91ab914
- Phase 1 Line-by-line reading | 2026-10-23 ~ 10-25 | Claude Code / Claude desktop (Opus 5.5) | commits: dcf54bf, cd9aad0, fb2aed1, fddae14, 57a2718, dc3ef9b, 7c01a97
- Phase 2 Variable table | 2026-10-25 | Claude Code (Opus 5.5) | commits: 1d78b39, 037ed94

## 7. 其他
- 命名：全小写、下划线分隔，不用空格和中文。
- Git：在 assignment2 分支上工作；origin 是个人 fork，upstream 是课程仓库。
- 本机工具（macOS，Homebrew）：poppler（`pdftoppm`/`pdftotext`，读 PDF 页面和图）、tectonic（编译 LaTeX）。开始工作时用 `which pdftoppm tectonic` 检查；缺失则请用户运行 `brew install poppler tectonic`，agent 不自行安装。
- LaTeX 编译（`subfiles`）：`main.tex` 是完整报告（导言区 + `\subfile` 各章）；每个章节文件首尾固定为 `\documentclass[../main.tex]{subfiles}`、`\begin{document}` … `\end{document}`，可借用 `main.tex` 的导言区单独编译。`main.tex`、`sections/`、`figures/` 的相对位置不可改。每次修改 LaTeX 后，agent 在 `report/` 下运行 `mkdir -p build && tectonic --keep-logs --outdir build sections/<章节>.tex`（或 `main.tex` 编整份），修掉错误和 Overfull 后，在侧边文件面板打开 `build/<章节>.pdf` 给用户看。`report/build/` 由根 `.gitignore` 忽略。用户也可用 VS Code 的 LaTeX Workshop（需 MacTeX）。
- 临时预览（如阶段蒸馏）：写成 `sections/` 下的临时章节文件单独编译，不加入 `main.tex`、不记 log，用户看完即删。
