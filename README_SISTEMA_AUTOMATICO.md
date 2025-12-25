# 🚀 SISTEMA AUTOMÁTICO DE EVENTOS - RESUMEN EJECUTIVO

## ¿QUÉ ES ESTO?

Un sistema **100% automático y GRATIS** que actualiza los eventos de tu app cada semana extrayendo datos reales de Giglon y La Tinta de Almansa.

---

## ✨ CÓMO FUNCIONA EN 3 PASOS

```
1️⃣ GITHUB ACTIONS (Automático)
   └─ Cada lunes a las 9:00 AM
   └─ Ejecuta script Python con Selenium
   └─ Extrae eventos de Giglon + La Tinta

2️⃣ GITHUB PAGES (API Gratis)
   └─ Guarda eventos_agenda.json
   └─ Sirve como API: https://tu-usuario.github.io/almansa-eventos/eventos_agenda.json

3️⃣ TU APP ANDROID
   └─ Descarga el JSON al abrir
   └─ Lo guarda en Room (caché)
   └─ Muestra eventos actualizados
```

---

## 📦 ARCHIVOS QUE TE ENTREGO

### 🔧 Sistema Automático (GitHub):

```
.github/workflows/actualizar-eventos.yml  ← Workflow automático
scripts/extractor_eventos.py             ← Script de extracción
GUIA_COMPLETA_AUTOMATIZACION.md          ← Instrucciones paso a paso
```

### 📱 Integración Android:

```
ApiEventos.kt  ← Retrofit API para descargar JSON
```

### 🆘 Backup Manual:

```
extractor_manual_mejorado.html  ← Por si falla el automático
```

---

## ⚡ INSTALACIÓN RÁPIDA (15 minutos)

### 1. Crear repositorio GitHub

```bash
# Ir a: https://github.com/new
# Nombre: almansa-eventos
# Público ✅
```

### 2. Subir archivos

```bash
git clone https://github.com/TU-USUARIO/almansa-eventos.git
cd almansa-eventos

# Copiar los archivos que te di:
# - .github/workflows/actualizar-eventos.yml
# - scripts/extractor_eventos.py

git add .
git commit -m "🎉 Sistema automático"
git push
```

### 3. Activar GitHub Pages

```
Settings → Pages → Branch: main → Save
```

### 4. Ejecutar primera vez

```
Actions → "Actualizar Eventos" → Run workflow
```

### 5. Integrar en tu app

```kotlin
// En ApiEventos.kt cambiar:
const val BASE_URL = "https://TU-USUARIO.github.io/almansa-eventos/"

// En ModuloApp.kt añadir Retrofit para eventos
// En ViewModelAgenda.kt cargar desde API en lugar de assets
```

---

## ✅ VENTAJAS

| Característica | Descripción |
|---------------|-------------|
| ⏰ **Automático** | Se ejecuta solo cada lunes |
| 💰 **Gratis** | GitHub Actions + Pages = $0 |
| 🔄 **Actualizado** | Siempre datos reales de Giglon |
| 📡 **Sin servidor** | No necesitas hosting |
| 💾 **Offline** | Caché en Room si no hay internet |
| 🔧 **Manual** | Puedes forzar actualización |

---

## 📊 COMPARATIVA DE OPCIONES

| Método | Automático | Gratis | Datos Reales | Dificultad |
|--------|-----------|--------|--------------|-----------|
| **GitHub Actions** ✅ | ✅ Sí | ✅ Sí | ✅ Sí | ⭐⭐ Media |
| Script Python local | ❌ No | ✅ Sí | ✅ Sí | ⭐⭐⭐ Alta |
| Extractor manual HTML | ❌ No | ✅ Sí | ✅ Sí | ⭐ Fácil |
| Assets estático | ❌ No | ✅ Sí | ❌ No | ⭐ Fácil |

---

## 🎯 SIGUIENTE PASO

1. **Leer:** `GUIA_COMPLETA_AUTOMATIZACION.md`
2. **Crear:** Repositorio en GitHub
3. **Copiar:** Los 2 archivos del sistema
4. **Probar:** Ejecutar workflow
5. **Integrar:** En tu app Android

---

## 🆘 SI ALGO FALLA

### Plan A: Sistema automático no funciona

→ Usa `extractor_manual_mejorado.html` temporalmente

### Plan B: Giglon bloquea el scraping

→ El script ya incluye User-Agent real y delays

### Plan C: Quieres añadir más fuentes

→ Edita `extractor_eventos.py` sección EXTRACTOR LA TINTA

---

## 📞 ARCHIVOS IMPORTANTES

| Archivo | Para qué sirve |
|---------|---------------|
| `actualizar-eventos.yml` | Configuración de GitHub Actions |
| `extractor_eventos.py` | Lógica de extracción |
| `ApiEventos.kt` | Cliente Retrofit en Android |
| `GUIA_COMPLETA_AUTOMATIZACION.md` | Instrucciones detalladas |
| `extractor_manual_mejorado.html` | Backup manual |

---

## 💡 TIP PRO

Una vez configurado, **NO TIENES QUE HACER NADA MÁS**.

El sistema:
- ✅ Extrae eventos automáticamente
- ✅ Actualiza el JSON en GitHub
- ✅ Tu app lo descarga al abrir
- ✅ Todo funciona solo

**Solo necesitas configurarlo UNA VEZ** ⚡

---

¿Listo para empezar? 🚀

👉 Abre: `GUIA_COMPLETA_AUTOMATIZACION.md`
