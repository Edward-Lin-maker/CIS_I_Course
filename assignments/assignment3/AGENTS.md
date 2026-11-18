# AGENTS.md - CIS I Assignment 3

本文件是 assignment3 的唯一规则文件；CLAUDE.md 仅引用本文件。详细资料按需读取，不重复加载旧作业全文。

## 1. 范围与权威
- 当前分支 `assignment3`；当前目录 `assignments/assignment3/`。只修改本作业目录。不得更改 assignment1/、assignment2/、根目录文件或其他作业；用户明确授权的 Git 分支同步除外。
- 任务：tracked pointer 对 femur mesh 的 reference-to-CT registration。先完成理论，再设计、实现和验证，不在 setup 阶段编写解法。
- 题目以 `docs/2026_assignment_3.pdf` 为准；代码接口和行为查本地 A3 README、src、notebook、tests。矛盾分别注明来源，不擅自修正。已发现差异见 `docs/course_reference.md` Part 4.4。
- PDF TRE 目标为 1 mm，README 为 2 mm；不得混写。真实执行上限 10 min；模拟时间无固定上限，需说明临床合理性。未给出的数值写 `not specified`。
- A1 rubric 图片只作经验参考，不是 A3 官方评分标准；遵守 `docs/report_guidelines.md` 中提炼的可迁移要求。

## 2. 交流与第一性原理
- 回答中文；除本文件外，所有文件、日志、代码和注释用英文。Python/numpy，先结论后必要推导。
- 默认只回答；写文件、读代码、运行命令和修改代码需用户授权。例外：题目未给的细节可直接查本地代码。已授权工作持续推进，不重复询问常规步骤。
- 从当前问题与已知关系逐步推导；定义、符号、假设只在用到时引入。减少回看，关键关系就近重述，不只给编号。
- 指代已有数学量必须附符号。优先用已有公式、具体向量/矩阵和前后对照，不写大段解释，不自造名称或无必要的辅助记号。
- 对话独立公式用 `$$...$$`；行内仅单个符号。多步推导可单独编译临时预览。
- 报告只写问题、方法、推导、假设、结果；不写对话问答和讨论历史。

## 3. 记号与资料
- F = Frame(R,p)，F b = Rb+p；F_{x,y} 表示 y 相对 x。R、p 的上下标与 F 一致，不用数字矩阵分块索引。
- * 表示真实量，obs 表示观测，est 表示估计参数；hat 仅用于模型预测，不表示观测。不同来源的历史记法不能直接套用。
- 误差左/右乘必须按当前来源与帧定义推导，不继承 A2 的乘法侧或 robot 假设。
- 主记号首次定义于报告时同步更新 course_reference Part 4.5；临时辅助记号只写 LaTeX。
- 发现疑似笔误：先在对话指出原文、来源与建议，确认后才登记正式更正；Part 4.4 可先记录未解决的来源差异。
- 阶段澄清经用户确认后记 Part 4.6，先依据后结论，不记猜测或显而易见内容。
- 先查 `docs/course_reference.md`；只读当前所需章节。A1 完整格式参考为 `docs/a1_report.tex`；A2 蒸馏见 Part 3，完整内容保留在 assignment2 分支。
- 团队目录说明和与课程 main 的差异见 `docs/workspace_guide.md`；安装运行仍以原 README 为入口。
- A3 文件索引：`src/mesh.py`、`src/session.py`、`src/student/{closest_point,icp,uncertainty,workflow,report}.py`，`notebooks/assignment3_template.ipynb`，`tests/`，`data/`，`docs/`，`report/`。

## 4. 代码、来源与验证
- 保留课程提供的 mesh、session、report 接口和评分入口；不要更改 supplied 文件，除非用户明确授权且报告解释原因。新增学生算法写 src/student/，测试写 tests/。
- 只通过 Session 接口访问模拟器。不得调用真实参数、隐藏 server 数据或 practice-only evaluate_tre/true_outliers 来完成标定、选点或调参；仅验证、调试和报告可使用真值。
- A3 显式导入 A1 tracker/types 时，只追踪实际导入的部分并注明来源。不能把 A1/A2 常量当 A3 行为。
- 函数有 purpose、输入类型/形状、输出 docstring；单一职责、清晰命名、常量有依据、避免重复计算和中文注释；不要过度注释显然代码。
- 完成时验证干净安装、主要函数独立/边界/退化/失败测试及完整 notebook。测试数据不能仅用被测函数自身生成答案。
- 报告结果必须对应保存的 notebook/实验数据，标明 seed、环境、统计定义、失败和时间范围。不得将未运行结果写成实测。
- 远程课程仓库只在用户明确要求时查询；不得发送消息或提交服务器任务，除非当前任务授权。

## 5. Report 与 rubric
- 遵守 `docs/report_guidelines.md`。关键项：可独立理解的目标/指标/人体工学；适当的设计草图、定量表格及理由（尺寸/坐标标注按表达需要，是建议而非额外题目硬指标）；定义变量、推导公式、就近引用讲义/来源；算法输入输出、伪代码、边界/停止条件；数据和控制流程图或调用树；各主要模块及整体的验证证据；达标对照及未达标解释。
- A3 专项：patch IDs/counts、valid/outlier samples、残差 mean/std/max/p90、FRE 与 TRE 区别、模拟/真实时间。不能把小残差当作真实 TRE 保证。
- 公式要注明来源；原创推导明确标注其起点和推导。不能虚构引用、页码或实验。
- AI 使用、外部代码来源、prompts/用途及时记 `docs/ai_assistance.md`；最终写入 AI/tools 章节。署名、JHED ID、贡献和双方签名提交前核实；新作业不能复用旧签名。

## 6. 日志与 Git
- 开始已授权工作前 `git pull --ff-only`，检查分支和本地改动；新分支尚无 upstream 时先 fetch 并说明，不猜测跟踪分支。
- 每次允许的源文件修改后，在 `docs/progress_log.md` 的 Pending 追加 `- MM-DD HH:MM | Codex | files | brief change`。build/、临时预览不记。
- 用户要求 commit 时：先补上上个实际 commit 的 TBD；将 Pending 归并到新的 `### TBD | YYYY-MM-DD HH:MM | "message" | not pushed`，清空 Pending，同步本文件 Current phase commits；日志、规则与改动同提交。
- 仅暂存 A3 文件。最后一次工作 commit 后可单独 `log: fill hash for <hash>` 补号；log commit 不再记日志。只改精确的 TBD 条目，不全局替换示例或历史。
- 未要求 commit/push 时保留可审查工作改动；不擅自提交或发布 assignment3。

## 7. 工具与报告框架
- 开始检查 `which pdftoppm tectonic`。缺失请用户安装，不自行安装系统工具。
- 文件名小写下划线；保持 main.tex、sections/、figures/ 相对位置。每次只读改必要章节。
- 章节固定 subfiles 包装；修改后在 report/ 编译 `tectonic --keep-logs --outdir build main.tex` 或单章，修错误与 Overfull，检查渲染后展示 PDF。build/ 本地忽略。
- 临时预览不加入 main.tex、不记日志，看完删除。旧签名 PDF 只保存在原作业，不覆盖。

## 8. Progress
- [x] Phase 0: upstream sync, A3 branch, migrated sources, A1/A2 distilled reference, rubric guidance, empty report skeleton and fresh log.
- [ ] Phase 1: line-by-line A3 reading and source discrepancy clarification.
- [ ] Phase 2: notation and theory.
- [ ] Phase 3: design and implementation.
- [ ] Phase 4: validation, results and final report.

### Current phase commits
- fb6ca0f | 2026-11-18 | Setup: initialize Assignment 3 references and report skeleton
- 6ee2f0a | 2026-11-18 | docs: add workspace guide and clarify design requirements
