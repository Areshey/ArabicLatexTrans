import ast

BASE = "/content/LaTeXTrans"  # change to "." when testing locally

# ============================================================
# STEP 1: parser_agent.py -- needs a FRESH import (no existing progress import)
# ============================================================
path = f"{BASE}/src/agents/tool_agents/parser_agent.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "from src.utils.progress import status" not in content:
    marker = "from src.agents.tool_agents.base_tool_agent import BaseToolAgent"
    assert marker in content, "parser_agent.py: import anchor not found -- paste file content back to me"
    content = content.replace(marker, marker + "\nfrom src.utils.progress import status")

old = 'self.log(f"✅ Successfully parsed {os.path.basename(self.project_dir)}.")'
new = 'self.log(status(f"✅ Successfully parsed {os.path.basename(self.project_dir)}.", f"✅ تم تحليل {os.path.basename(self.project_dir)} بنجاح."))'
assert old in content, "parser_agent.py: expected line not found -- paste file content back to me"
content = content.replace(old, new)

ast.parse(content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ parser_agent.py patched")


# ============================================================
# STEP 2: translator_agent.py -- needs a FRESH import
# (its existing "import streamlit as st" is the REAL streamlit module,
#  unrelated to our progress.py proxy -- status must be imported separately)
# ============================================================
path = f"{BASE}/src/agents/tool_agents/translator_agent.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "from src.utils.progress import status" not in content:
    marker = "import streamlit as st"
    assert marker in content, "translator_agent.py: import anchor not found -- paste file content back to me"
    content = content.replace(marker, marker + "\nfrom src.utils.progress import status")

replacements = [
    (
        'self.log(f"✅ Successfully translated sections!")',
        'self.log(status("✅ Successfully translated sections!", "✅ تمت ترجمة الأقسام بنجاح!"))'
    ),
    (
        'status_text.text("✅ Successfully translated sections!")',
        'status_text.text(status("✅ Successfully translated sections!", "✅ تمت ترجمة الأقسام بنجاح!"))'
    ),
    (
        'st.success("✅ Successfully translated sections!")',
        'st.success(status("✅ Successfully translated sections!", "✅ تمت ترجمة الأقسام بنجاح!"))'
    ),
    (
        'self.log(f"✅ Successfully retranslated error parts!")',
        'self.log(status("✅ Successfully retranslated error parts!", "✅ تمت إعادة ترجمة الأجزاء الخاطئة بنجاح!"))'
    ),
    (
        'status_text.text(f"✅ Successfully retranslated error parts!")',
        'status_text.text(status("✅ Successfully retranslated error parts!", "✅ تمت إعادة ترجمة الأجزاء الخاطئة بنجاح!"))'
    ),
    (
        'st.error(f"❌ Failed to translate {fail_parts}")',
        'st.error(status(f"❌ Failed to translate {fail_parts}", f"❌ فشلت ترجمة {fail_parts}"))'
    ),
]

for old, new in replacements:
    assert old in content, f"translator_agent.py: expected line not found: {old!r} -- paste file content back to me"
    content = content.replace(old, new)

ast.parse(content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ translator_agent.py patched")


# ============================================================
# STEP 3: generator_agent.py -- EXTEND existing import
# ============================================================
path = f"{BASE}/src/agents/tool_agents/generator_agent.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_import = "from src.utils.progress import st"
new_import = "from src.utils.progress import st, status"
if old_import in content and new_import not in content:
    content = content.replace(old_import, new_import)
elif new_import in content:
    pass  # already patched
else:
    raise AssertionError("generator_agent.py: import line not found -- paste file content back to me")

replacements = [
    (
        'self.status_text.text("✅ Successfully compiled PDF document.")',
        'self.status_text.text(status("✅ Successfully compiled PDF document.", "✅ تم تجميع مستند PDF بنجاح."))'
    ),
    (
        'st.success(f"✅ Successfully generated for {os.path.basename(self.project_dir)}.")',
        'st.success(status(f"✅ Successfully generated for {os.path.basename(self.project_dir)}.", f"✅ تم الإنشاء بنجاح لـ {os.path.basename(self.project_dir)}."))'
    ),
    (
        'self.log(f"✅ Successfully generated for {os.path.basename(self.project_dir)}.")',
        'self.log(status(f"✅ Successfully generated for {os.path.basename(self.project_dir)}.", f"✅ تم الإنشاء بنجاح لـ {os.path.basename(self.project_dir)}."))'
    ),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)

ast.parse(content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ generator_agent.py patched")


# ============================================================
# STEP 4: coordinator_agent.py -- needs a FRESH import
# ============================================================
path = f"{BASE}/src/agents/coordinator_agent.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "from src.utils.progress import status" not in content:
    marker = "from .tool_agents.base_tool_agent import BaseToolAgent"
    assert marker in content, "coordinator_agent.py: import anchor not found -- paste file content back to me"
    content = content.replace(marker, marker + "\nfrom src.utils.progress import status")

old = 'print(f"🤖🎉 {self.name}: Successfully translated {os.path.basename(self.project_dir)} to {new_PDF_path}.")'
new = 'print(status(f"🤖🎉 {self.name}: Successfully translated {os.path.basename(self.project_dir)} to {new_PDF_path}.", f"🤖🎉 {self.name}: تمت ترجمة {os.path.basename(self.project_dir)} بنجاح إلى {new_PDF_path}."))'
assert old in content, "coordinator_agent.py: expected line not found -- paste file content back to me"
content = content.replace(old, new)

ast.parse(content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ coordinator_agent.py patched")


# ============================================================
# STEP 5: formats/latex/parser.py -- EXTEND existing import
# ============================================================
path = f"{BASE}/src/formats/latex/parser.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_import = "from src.utils.progress import st"
new_import = "from src.utils.progress import st, status"
if old_import in content and new_import not in content:
    content = content.replace(old_import, new_import)
elif new_import in content:
    pass
else:
    raise AssertionError("parser.py: import line not found -- paste file content back to me")

replacements = [
    (
        'process_bar.progress(100, text="Finish Parse Sections")',
        'process_bar.progress(100, text=status("Finish Parse Sections", "اكتمل تحليل الأقسام"))'
    ),
    (
        'st.success("Finish Parse Sections")',
        'st.success(status("Finish Parse Sections", "اكتمل تحليل الأقسام"))'
    ),
]

for old, new in replacements:
    assert old in content, f"parser.py: expected line not found: {old!r} -- paste file content back to me"
    content = content.replace(old, new)

ast.parse(content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ formats/latex/parser.py patched")


# ============================================================
# STEP 6: formats/latex/compile.py -- needs a FRESH import
# ============================================================
path = f"{BASE}/src/formats/latex/compile.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

if "from src.utils.progress import status" not in content:
    marker = "from .utils import *"
    assert marker in content, "compile.py: import anchor not found -- paste file content back to me"
    content = content.replace(marker, marker + "\nfrom src.utils.progress import status")

en_variant_a = 'f"✅  Successfully generated PDF file !"'
ar_variant_a = 'f"✅ تم إنشاء ملف PDF بنجاح !"'
count_a = content.count(f'print({en_variant_a})')
content = content.replace(f'print({en_variant_a})', f'print(status({en_variant_a}, {ar_variant_a}))')

en_variant_b = '"✅ Successfully generated PDF file!"'
ar_variant_b = '"✅ تم إنشاء ملف PDF بنجاح!"'
count_b = content.count(f'print({en_variant_b})')
content = content.replace(f'print({en_variant_b})', f'print(status({en_variant_b}, {ar_variant_b}))')

en_variant_c = 'f"✅ Successfully generated PDF at: {pdf_path}"'
ar_variant_c = 'f"✅ تم إنشاء ملف PDF في: {pdf_path}"'
count_c = content.count(f'print({en_variant_c})')
content = content.replace(f'print({en_variant_c})', f'print(status({en_variant_c}, {ar_variant_c}))')

total = count_a + count_b + count_c
print(f"compile.py: replaced {count_a} + {count_b} + {count_c} = {total} occurrences")
assert total > 0, "compile.py: none of the expected variants were found -- paste file content back to me"

ast.parse(content)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("✅ formats/latex/compile.py patched")

print("\n🎉 All 6 files patched successfully -- everything is now wired end to end.")
