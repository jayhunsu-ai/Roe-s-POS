# Fix indentation of methods in admin_app.py
with open('admin_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
in_problem_section = False

for i, line in enumerate(lines):
    # Check if this line starts a function definition at module level (not indented properly)
    # Functions like "def _page_menu(", "def _menu_form(", etc. that should be class methods
    if line.startswith('def _') and '(self' in line:
        # This should be indented as a class method (4 spaces)
        in_problem_section = True
        fixed_lines.append('    ' + line)
    elif in_problem_section:
        # Keep adding indentation until we reach the next module-level definition
        if line.startswith('def ') and not line.startswith('    def '):
            in_problem_section = False
            fixed_lines.append(line)
        elif line.startswith('# ──') and not line.startswith('    # ──'):
            # Comments at module level should also be indented
            fixed_lines.append('    ' + line)
        elif line.strip() == '' or line == '\n':
            fixed_lines.append(line)
        elif not line.startswith('    '):
            # Add indent
            fixed_lines.append('    ' + line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('admin_app.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Indentation fixed!")
