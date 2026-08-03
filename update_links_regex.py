import glob
import os
import re

files = glob.glob('templates/dashboard_superadmin*.html')
count = 0
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to replace href="#" or href="#" class="active" for the Módulos ERP link
    # The structure might be split across lines.
    
    # regex for Módulos ERP link
    # <a href="#"...><i class="bi bi-tools"></i>...Módulos ERP</a>
    
    pattern = r'<a\s+href="[^"]*"(?:\s+class="[^"]*")?\s*>\s*<i\s+class="bi\s+bi-tools"><\/i>\s*Módulos ERP\s*<\/a>'
    
    def repl(m):
        # We need to keep 'class="active"' if it was there
        match_str = m.group(0)
        if 'class="active"' in match_str:
            return '<a href="{% url \'dashboard_superadmin_modulos_erp\' %}" class="active"><i class="bi bi-tools"></i> Módulos ERP</a>'
        else:
            return '<a href="{% url \'dashboard_superadmin_modulos_erp\' %}"><i class="bi bi-tools"></i> Módulos ERP</a>'
            
    new_content = re.sub(pattern, repl, content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count += 1
        print(f"Updated {filepath}")

print(f"Total files updated: {count}")
