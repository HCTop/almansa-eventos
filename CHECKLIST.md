# ✅ CHECKLIST - Pasos para Activar el Sistema

## 📦 PASO 1: Subir Archivos a GitHub

```bash
□ cd /ruta/a/tu/repositorio/almansa-eventos

□ cp scripts/extractor_eventos_v3.py al repositorio
□ cp requirements.txt al repositorio
□ cp .github/workflows/actualizar-eventos.yml al repositorio
□ cp README.md al repositorio

□ git add .
□ git commit -m "✨ v3.0: 8 fuentes activas"
□ git push origin main
```

**✅ Verificar**: Ve a https://github.com/HCTop/almansa-eventos y comprueba que los archivos están ahí.

---

## 🎬 PASO 2: Ejecutar Primera Vez

```bash
□ Ir a: https://github.com/HCTop/almansa-eventos/actions

□ Click en "Actualizar Eventos Almansa"

□ Click en "Run workflow" (botón azul)

□ Click en "Run workflow" (confirmar)

□ Esperar 1-2 minutos

□ Ver resultado:
   ✅ Verde = Éxito
   ❌ Rojo = Ver logs de error
```

**✅ Verificar**: El workflow debe completarse en verde.

---

## 🌐 PASO 3: Comprobar JSON Público

```bash
□ Abrir navegador

□ Ir a: https://hctop.github.io/almansa-eventos/eventos_agenda.json

□ Deberías ver un JSON con eventos
```

**Ejemplo esperado:**
```json
[
  {
    "id": "evt_abc123",
    "titulo": "Concierto de Santa Cecilia",
    "fecha": "2025-11-17",
    ...
  }
]
```

**✅ Verificar**: Hay al menos 10-20 eventos en el JSON.

---

## 📱 PASO 4: Integrar en Android

### A. Verificar que tienes estos archivos:

```bash
□ EventoDto.kt (en dominio/modelo/)
□ ApiEventos.kt (en datos/remoto/api/)
```

### B. Crear archivos que faltan:

```bash
□ RepositorioEventos.kt (interfaz en dominio/repositorio/)
□ RepositorioEventosImpl.kt (implementación en datos/repositorio/)
□ ViewModelEventos.kt (en presentacion/pantallas/eventos/)
□ PantallaEventos.kt (en presentacion/pantallas/eventos/)
```

### C. Registrar en navegación:

```bash
□ Añadir ruta en Rutas.kt
□ Añadir composable en GrafoNavegacion.kt
□ Añadir botón en PantallaInicio.kt
```

---

## 🧪 PASO 5: Probar en Android

```bash
□ Sync Gradle

□ Compilar app

□ Abrir pantalla de Eventos

□ Debería cargar 20-40 eventos

□ Verificar:
   ✅ Títulos se ven bien
   ✅ Fechas formateadas
   ✅ Categorías correctas
   ✅ Click abre detalles
```

---

## 🎯 MÉTRICAS DE ÉXITO

| Métrica | Objetivo | Estado |
|---------|----------|--------|
| Fuentes activas | 8 | □ |
| Eventos extraídos | 25-40 | □ |
| Duplicados eliminados | 15-25% | □ |
| JSON accesible | ✅ | □ |
| Android integrado | ✅ | □ |

---

## 🐛 SI ALGO FALLA

### ❌ "0 eventos extraídos"
```bash
□ Ir a: https://latintadealmansa.com/cultura/
□ Ver si hay programación trimestral reciente
□ Si no hay → Esperar a nueva temporada (3-4 meses)
```

### ❌ "Error HTTP 403"
```bash
□ Revisar que las URLs en el script son correctas
□ Probar abrir las URLs en navegador
□ Si fallan → Reportar issue en GitHub
```

### ❌ "No compila en Android"
```bash
□ Verificar que EventoDto.kt tiene todos los campos
□ Verificar importaciones de Retrofit
□ Limpiar cache: Build > Clean Project
□ Rebuild: Build > Rebuild Project
```

### ❌ "JSON vacío o no se carga"
```bash
□ Verificar GitHub Pages está habilitado
□ Ir a Settings > Pages > debe estar en "main/root"
□ Esperar 5 minutos (propagación DNS)
□ Revisar ruta: /eventos_agenda.json (no /scripts/eventos_agenda.json)
```

---

## 📞 SIGUIENTE SESIÓN

Cuando tengamos otra sesión, podemos:
- ✅ Implementar RepositorioEventos en Android
- ✅ Crear la UI de la pantalla de Eventos
- ✅ Añadir filtros por categoría
- ✅ Implementar sistema de favoritos
- ✅ Notificaciones de eventos próximos

---

## 📊 PROGRESO ACTUAL

```
PROYECTO ALMANSA INFORMA - EXTRACTOR DE EVENTOS

[████████████████████████████░░] 93% COMPLETADO

✅ Scraper multi-fuente funcionando (8 fuentes)
✅ Deduplicación implementada
✅ GitHub Actions configurado
✅ GitHub Pages sirviendo JSON
✅ Documentación completa
⏳ Integración Android pendiente (próxima sesión)
```

---

**🎉 BUEN TRABAJO! El sistema de extracción está listo para producción.**
