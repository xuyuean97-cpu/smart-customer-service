"""
批量修复 ruff lint 问题：E701, B904, E722, F401 (__init__.py)
"""
import os
import re
import subprocess

WORKTREE = r"C:\Users\xu\PycharmProjects\smart-customer-service-system\.claude\worktrees\cranky-nobel-0a1b01"

def run_ruff():
    """运行 ruff check 获取所有问题"""
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "--output-format=concise"],
        cwd=WORKTREE, capture_output=True, text=True
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def parse_issues(lines):
    """解析 ruff 输出，按文件分组"""
    issues = []
    for line in lines:
        # 格式: path:line:col: CODE Description
        m = re.match(r'(.+?):(\d+):(\d+):\s+(\w+)\s+(.+)', line)
        if m:
            issues.append({
                'file': m.group(1),
                'line': int(m.group(2)),
                'col': int(m.group(3)),
                'code': m.group(4),
                'desc': m.group(5),
            })
    return issues


def fix_e701(issues):
    """修复 E701: 拆分单行多语句 (if cond: stmt → 两行)"""
    e701_issues = [i for i in issues if i['code'] == 'E701']
    by_file = {}
    for i in e701_issues:
        by_file.setdefault(i['file'], []).append(i['line'])

    for fpath, lines_set in by_file.items():
        full_path = os.path.join(WORKTREE, fpath)
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            file_lines = content.splitlines(keepends=True)

        # 重新读取文件，逐行处理
        for line_no in sorted(set(lines_set), reverse=True):
            idx = line_no - 1
            if idx >= len(file_lines):
                continue
            raw = file_lines[idx]
            # 找冒号后跟语句的模式: "if x: return y" 或 "else: return y" 或 "elif x: return y"
            # 匹配模式: 关键字 + 条件 + : + 语句
            new_line = re.sub(
                r'^(\s*)(if\s+.+?|elif\s+.+?|else)\s*:\s+(.+)$',
                r'\1\2:\n\1    \3',
                raw
            )
            if new_line != raw:
                file_lines[idx] = new_line

        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(file_lines)

    print(f"  E701: fixed {len(e701_issues)} issues in {len(by_file)} files")


def fix_e722(issues):
    """修复 E722: bare except → except Exception"""
    e722_issues = [i for i in issues if i['code'] == 'E722']
    by_file = {}
    for i in e722_issues:
        by_file.setdefault(i['file'], []).append(i['line'])

    for fpath, lines_set in by_file.items():
        full_path = os.path.join(WORKTREE, fpath)
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            file_lines = content.splitlines(keepends=True)

        for line_no in sorted(set(lines_set), reverse=True):
            idx = line_no - 1
            if idx >= len(file_lines):
                continue
            raw = file_lines[idx]
            if re.match(r'^(\s*)except\s*:\s*$', raw):
                indent = re.match(r'^(\s*)', raw).group(1)
                file_lines[idx] = f'{indent}except Exception:\n'

        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(file_lines)

    print(f"  E722: fixed {len(e722_issues)} issues in {len(by_file)} files")


def fix_b904(issues):
    """修复 B904: raise X(...) → raise X(...) from err"""
    b904_issues = [i for i in issues if i['code'] == 'B904']
    by_file = {}
    for i in b904_issues:
        by_file.setdefault(i['file'], []).append(i['line'])

    for fpath, lines_set in by_file.items():
        full_path = os.path.join(WORKTREE, fpath)
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            file_lines = content.splitlines(keepends=True)

        for line_no in sorted(set(lines_set), reverse=True):
            idx = line_no - 1
            if idx >= len(file_lines):
                continue
            raw = file_lines[idx]
            # 匹配 raise ... 且不在已有 'from' 的情况
            if re.search(r'\braise\b', raw) and ' from ' not in raw:
                # 在 except 块中的 raise，添加 from err
                # 需要找到 except 子句中绑定的异常变量名
                # 向上查找最近的 except 行
                exc_name = 'err'
                for j in range(idx - 1, max(idx - 15, -1), -1):
                    prev = file_lines[j].strip()
                    m_exc = re.match(r'except\s+\w+\s+as\s+(\w+)', prev)
                    if m_exc:
                        exc_name = m_exc.group(1)
                        break
                    if re.match(r'except\b', prev):
                        exc_name = 'exc'
                        break

                # 在行尾或换行前插入 from exc_name
                raw_stripped = raw.rstrip()
                # 去掉行尾注释和换行
                m_trailing = re.match(r'^(.*?)(\s*#.*)?(\s*)$', raw_stripped)
                code_part = m_trailing.group(1) if m_trailing else raw_stripped
                comment_part = m_trailing.group(2) if m_trailing and m_trailing.group(2) else ''
                eol = '\n' if raw.endswith('\n') else ''

                if not code_part.rstrip().endswith(f' from {exc_name}'):
                    new_raw = f'{code_part.rstrip()} from {exc_name}{comment_part}{eol}'
                    file_lines[idx] = new_raw

        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(file_lines)

    print(f"  B904: fixed {len(b904_issues)} issues in {len(by_file)} files")


def fix_f401_init_py(issues):
    """修复 F401 in __init__.py: 添加 __all__ 声明"""
    f401_issues = [i for i in issues if i['code'] == 'F401' and i['file'].endswith('__init__.py')]
    by_file = {}
    for i in f401_issues:
        by_file.setdefault(i['file'], []).append(i)

    for fpath, items in by_file.items():
        full_path = os.path.join(WORKTREE, fpath)
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取被导入的模块名
        names = []
        for item in items:
            m = re.search(r"`([^`]+)`", item['desc'])
            if m:
                names.append(m.group(1))

        if not names:
            continue

        # 在文件末尾添加 __all__
        if '__all__' not in content:
            all_line = f"__all__ = {names!r}\n"
            content = content.rstrip() + '\n' + all_line

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

    print(f"  F401 (__init__.py): fixed {len(f401_issues)} issues in {len(by_file)} files")


def fix_f401_other(issues):
    """修复 F401 in 非 __init__.py: 移除未使用的导入"""
    f401_issues = [i for i in issues if i['code'] == 'F401' and not i['file'].endswith('__init__.py')]
    by_file = {}
    for i in f401_issues:
        by_file.setdefault(i['file'], []).append(i)

    for fpath, items in by_file.items():
        full_path = os.path.join(WORKTREE, fpath)
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            file_lines = content.splitlines(keepends=True)

        for item in sorted(items, key=lambda x: x['line'], reverse=True):
            idx = item['line'] - 1
            if idx >= len(file_lines):
                continue

            # 提取导入的符号名
            m = re.search(r"`([^`]+)`", item['desc'])
            if not m:
                continue
            name = m.group(1)

            raw = file_lines[idx]
            # 从导入行中移除该符号
            # 处理 from X import a, b 的情况
            if 'import' in raw:
                # 看看是否是多行导入的一部分
                # 简单处理: 注释掉整行或删除
                # 更安全的方式是注释掉
                if name in raw:
                    file_lines[idx] = raw.replace(name, '').replace(' ,', '').replace(',,', ',').replace('(,', '(').replace(', )', ')')
                    # 如果变成空的 import，注释掉整行
                    if re.search(r'from\s+\S+\s+import\s*\(\s*\)', file_lines[idx]) or re.search(r'from\s+\S+\s+import\s*$', file_lines[idx].strip()):
                        file_lines[idx] = f'# {file_lines[idx].strip()}\n'
                    # 如果行尾变成 import (,
                    if file_lines[idx].strip().endswith('import ('):
                        continue  # 保持原样，多行导入比较复杂

        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(file_lines)

    print(f"  F401 (other): fixed {len(f401_issues)} issues in {len(by_file)} files")


def fix_b027(issues):
    """修复 B027: 空方法添加 @abstractmethod 或放个 docstring"""
    b027_issues = [i for i in issues if i['code'] == 'B027']
    for item in b027_issues:
        full_path = os.path.join(WORKTREE, item['file'])
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            file_lines = content.splitlines(keepends=True)

        # 在 def 前一行添加 @abstractmethod
        idx = item['line'] - 1
        indent = re.match(r'^(\s*)', file_lines[idx]).group(1)
        file_lines.insert(idx, f'{indent}@abstractmethod\n')

        # 确保文件顶部有 from abc import abstractmethod
        if 'from abc import' not in content and 'abstractmethod' not in content:
            # 找到最后一个 import 行之后插入
            last_import = 0
            for i, line in enumerate(file_lines):
                if line.startswith('from ') or line.startswith('import '):
                    last_import = i
            file_lines.insert(last_import + 1, 'from abc import abstractmethod\n')

        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(file_lines)

    print(f"  B027: fixed {len(b027_issues)} issues")


def main():
    os.chdir(WORKTREE)
    print("Running ruff check...")
    lines = run_ruff()
    issues = parse_issues(lines)

    print(f"\nTotal issues: {len(issues)}")
    codes = {}
    for i in issues:
        codes[i['code']] = codes.get(i['code'], 0) + 1
    for code, count in sorted(codes.items()):
        print(f"  {code}: {count}")

    print("\nFixing E701 (multiple statements on one line)...")
    fix_e701(issues)

    print("\nFixing E722 (bare except)...")
    fix_e722(issues)

    print("\nFixing B904 (raise without from)...")
    fix_b904(issues)

    print("\nFixing F401 __init__.py (add __all__)...")
    fix_f401_init_py(issues)

    print("\nFixing B027 (empty abstract method)...")
    fix_b027(issues)

    # Re-run to check remaining
    print("\nRe-running ruff check...")
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "--statistics"],
        cwd=WORKTREE, capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)


if __name__ == '__main__':
    main()
