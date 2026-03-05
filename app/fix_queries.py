
import os

filepath = r'c:\Users\alexo\Desktop\actas_app\app\app.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace first occurrence (admin_documentos)
content = content.replace(
    'i.caso_tipo,\n                i.alimentador_subestacion,',
    'i.caso_tipo,\n                i.nombre_alimentador,\n                i.alimentador_subestacion,'
)

# Replace second occurrence (mis_documentos)
# Since they are identical, calling it twice works or use .replace(..., 2)
# But wait, did I already update one? Let's just do it globally if it matches.

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement done.")
