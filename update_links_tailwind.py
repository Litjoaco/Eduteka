import glob
import os
import re

files = glob.glob('templates/dashboard_superadmin*.html')
count = 0
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # regex for Módulos ERP link matching <a href="#" ... Módulos ERP </a>
    # Note: re.DOTALL to allow matching across newlines
    pattern = r'<a\s+href="#"\s+class="([^"]*)"[^>]*>(.*?)Módulos ERP(.*?)<\/a>'
    
    def repl(m):
        return f'<a href="{{% url \'dashboard_superadmin_modulos_erp\' %}}" class="{m.group(1)}">{m.group(2)}Módulos ERP{m.group(3)}</a>'
        
    new_content = re.sub(pattern, repl, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count += 1
        print(f"Updated {filepath}")

print(f"Total files updated: {count}")
