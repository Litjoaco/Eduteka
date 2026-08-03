import glob
import os

files = glob.glob('templates/dashboard_superadmin*.html')
count = 0
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the inactive link
    old_str_1 = 'href="#"><i class="bi bi-tools"></i> Módulos ERP'
    new_str_1 = 'href="{% url \'dashboard_superadmin_modulos_erp\' %}"><i class="bi bi-tools"></i> Módulos ERP'
    
    # Replace the active link
    old_str_2 = 'href="#" class="active"><i class="bi bi-tools"></i> Módulos ERP'
    new_str_2 = 'href="{% url \'dashboard_superadmin_modulos_erp\' %}" class="active"><i class="bi bi-tools"></i> Módulos ERP'

    new_content = content.replace(old_str_1, new_str_1)
    new_content = new_content.replace(old_str_2, new_str_2)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count += 1
        print(f"Updated {filepath}")

print(f"Total files updated: {count}")
