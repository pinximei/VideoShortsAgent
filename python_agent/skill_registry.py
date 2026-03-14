"""
SkillRegistry - 通用 Skills 发现、加载与执行框架

核心职责：
1. discover()  — 扫描 skills/ 目录，读取所有 SKILL.md 的 frontmatter
2. get_index() — 生成索引文本（注入 system prompt，只含名称和简介）
3. get_full_doc(name)   — 返回完整 SKILL.md 内容（按需加载）
4. execute(name, args, context)  — 调用对应的 executor.py
5. parse_skill_call(text)        — 从 LLM 回复中解析 [USE_SKILL: xxx]

使用方式：
    registry = SkillRegistry("./skills")
    # 注入索引到 system prompt
    prompt += registry.get_index()
    # 解析 LLM 回复
    call = registry.parse_skill_call(llm_reply)
    if call:
        result = registry.execute(call["name"], call["args"], context)
"""
import os
import re
import importlib.util


def _parse_frontmatter(content: str) -> tuple:
    """解析 SKILL.md 的 YAML frontmatter 和 Markdown 正文

    Args:
        content: SKILL.md 的完整文本

    Returns:
        (metadata_dict, body_text)
    """
    # 匹配 --- 包裹的 frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not match:
        return {}, content

    yaml_text = match.group(1)
    body = match.group(2)

    # 简易 YAML 解析（不引入 pyyaml 依赖）
    metadata = {}
    current_key = None
    current_list = None

    for line in yaml_text.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        # 检测列表项: "  - name: xxx"
        list_match = re.match(r'^\s+-\s+(\w+):\s*(.*)', line)
        top_match = re.match(r'^(\w+):\s*(.*)', line)

        if list_match and current_key:
            # 列表项的第一个字段 → 开始新的列表元素
            if current_list is None:
                current_list = []
                metadata[current_key] = current_list
            # 检查是否是新元素的开始
            key, val = list_match.group(1), list_match.group(2).strip()
            if not current_list or key in current_list[-1]:
                current_list.append({})
            current_list[-1][key] = val
        elif re.match(r'^\s+(\w+):\s*(.*)', line) and current_list:
            # 列表项的后续字段
            sub_match = re.match(r'^\s+(\w+):\s*(.*)', line)
            key, val = sub_match.group(1), sub_match.group(2).strip()
            if current_list:
                current_list[-1][key] = val
        elif top_match:
            # 顶级键值对
            key, val = top_match.group(1), top_match.group(2).strip()
            current_key = key
            current_list = None
            if val:
                metadata[key] = val

    return metadata, body


class SkillRegistry:
    """通用 Skills 注册表

    自动发现 skills_dir 下的所有 Skill，提供索引、文档和执行能力。

    目录结构要求：
        skills/
        ├── skill_name_1/
        │   ├── SKILL.md        ← 必需：YAML frontmatter + Markdown 文档
        │   └── executor.py     ← 必需：包含 execute(args, context) 函数
        └── skill_name_2/
            ├── SKILL.md
            └── executor.py
    """

    def __init__(self, skills_dir: str):
        """初始化并发现所有 Skills

        Args:
            skills_dir: skills 目录的路径
        """
        self.skills_dir = os.path.abspath(skills_dir)
        self._skills = {}       # name -> {metadata, body, dir_path}
        self._executors = {}    # name -> executor module (延迟加载)
        self._doc_injected = set()  # 已注入完整文档的 skill 名称

        self.discover()

    def discover(self):
        """扫描 skills 目录，读取所有 SKILL.md"""
        if not os.path.isdir(self.skills_dir):
            print(f"[SkillRegistry] 警告：skills 目录不存在: {self.skills_dir}")
            return

        for entry in os.listdir(self.skills_dir):
            skill_dir = os.path.join(self.skills_dir, entry)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            executor_py = os.path.join(skill_dir, "executor.py")

            if not os.path.isdir(skill_dir):
                continue
            if not os.path.isfile(skill_md):
                continue
            if not os.path.isfile(executor_py):
                print(f"[SkillRegistry] 警告：{entry}/ 缺少 executor.py，跳过")
                continue

            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()

            metadata, body = _parse_frontmatter(content)
            name = metadata.get("name", entry)

            self._skills[name] = {
                "metadata": metadata,
                "body": body,
                "full_content": content,
                "dir_path": skill_dir,
            }
            print(f"[SkillRegistry] 已发现 Skill: {name} - {metadata.get('description', '(无描述)')}")

        print(f"[SkillRegistry] 共发现 {len(self._skills)} 个 Skills ✓")

    def get_index(self) -> str:
        """生成 Skills 索引文本（注入 system prompt）

        只包含名称、描述和调用格式，不包含完整文档。

        Returns:
            适合注入 system prompt 的索引文本
        """
        if not self._skills:
            return ""

        lines = [
            "## 技能（Skills）",
            "除了工具（Tool）之外，你还拥有以下技能。",
            "当需要使用某个技能时，请在回复中按以下格式调用：",
            "```",
            "[USE_SKILL: 技能名]",
            "参数名1: 值1",
            "参数名2: 值2",
            "```",
            "",
            "可用技能列表：",
            "",
            "| 技能名 | 说明 | 参数 |",
            "|--------|------|------|",
        ]

        for name, info in self._skills.items():
            desc = info["metadata"].get("description", "")
            params = info["metadata"].get("parameters", [])
            if isinstance(params, list):
                param_names = ", ".join(p.get("name", "?") for p in params if isinstance(p, dict))
            else:
                param_names = str(params)
            lines.append(f"| {name} | {desc} | {param_names} |")

        lines.append("")
        return "\n".join(lines)

    def get_full_doc(self, name: str) -> str:
        """获取 Skill 的完整文档（按需加载）

        Args:
            name: Skill 名称

        Returns:
            完整的 SKILL.md 内容
        """
        if name not in self._skills:
            return f"错误：未找到 Skill '{name}'"
        return self._skills[name]["full_content"]

    def should_inject_doc(self, name: str) -> bool:
        """检查是否需要注入完整文档（首次使用时注入）"""
        if name in self._doc_injected:
            return False
        self._doc_injected.add(name)
        return True

    def parse_skill_call(self, text: str) -> dict:
        """从 LLM 回复中解析 [USE_SKILL: xxx] 调用

        Args:
            text: LLM 的回复文本

        Returns:
            解析结果字典 {"name": "...", "args": {...}}
            如果没有检测到 Skill 调用，返回 None
        """
        if not text:
            return None

        # 匹配 [USE_SKILL: skill_name]
        match = re.search(r'\[USE_SKILL:\s*(\w+)\]', text)
        if not match:
            return None

        skill_name = match.group(1)
        if skill_name not in self._skills:
            return {"name": skill_name, "args": {}, "error": f"未知 Skill: {skill_name}"}

        # 解析参数（key: value 格式，在 [USE_SKILL] 之后）
        args = {}
        after_marker = text[match.end():]
        for param_match in re.finditer(r'(\w+):\s*(.+)', after_marker):
            key = param_match.group(1)
            val = param_match.group(2).strip()
            # 过滤掉 markdown 代码块标记
            if val == "```" or key in ("type", "function"):
                continue
            args[key] = val

        return {"name": skill_name, "args": args}

    def execute(self, name: str, args: dict, context: dict) -> str:
        """执行指定的 Skill

        延迟加载 executor.py 模块，调用其 execute(args, context) 函数。

        Args:
            name: Skill 名称
            args: 参数字典
            context: Agent 运行时上下文

        Returns:
            执行结果字符串
        """
        if name not in self._skills:
            return f"错误：未知 Skill '{name}'"

        # 延迟加载 executor 模块
        if name not in self._executors:
            skill_dir = self._skills[name]["dir_path"]
            executor_path = os.path.join(skill_dir, "executor.py")

            spec = importlib.util.spec_from_file_location(f"skill_{name}_executor", executor_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "execute"):
                return f"错误：Skill '{name}' 的 executor.py 缺少 execute() 函数"

            self._executors[name] = module
            print(f"[SkillRegistry] 已加载 {name} executor ✓")

        # 执行
        return self._executors[name].execute(args, context)

    @property
    def names(self) -> list:
        """所有已注册的 Skill 名称"""
        return list(self._skills.keys())
