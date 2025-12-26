# 📤 INSTRUCCIONES - Subir a GitHub

## 🎯 PASO 1: Preparar el Repositorio

Ya tienes el repositorio creado en:
```
https://github.com/HCTop/almansa-eventos
```

## 🎯 PASO 2: Subir los Archivos Actualizados

### Opción A: Desde la Terminal (Recomendado)

```bash
cd /ruta/donde/clonaste/el/repo

# Copiar nuevos archivos
cp /ruta/almansa-eventos-estructura/scripts/extractor_eventos_v3.py scripts/
cp /ruta/almansa-eventos-estructura/requirements.txt .
cp /ruta/almansa-eventos-estructura/.github/workflows/actualizar-eventos.yml .github/workflows/
cp /ruta/almansa-eventos-estructura/README.md .

# Añadir cambios
git add .
git commit -m "✨ Extractor multi-fuente v3.0 con deduplicación"
git push origin main
```

### Opción B: Desde GitHub Web

1. Ve a https://github.com/HCTop/almansa-eventos
2. Click en "Add file" → "Upload files"
3. Arrastra estos archivos:
   - `scripts/extractor_eventos_v3.py`
   - `requirements.txt`
   - `.github/workflows/actualizar-eventos.yml`
   - `README.md`
4. Commit message: "✨ Extractor multi-fuente v3.0"
5. Click "Commit changes"

## 🎯 PASO 3: Probar GitHub Actions

1. Ve a https://github.com/HCTop/almansa-eventos/actions
2. Selecciona "Actualizar Eventos Almansa"
3. Click en "Run workflow" → "Run workflow"
4. Espera 1-2 minutos
5. Verás el resultado:
   - ✅ Verde = Éxito
   - ❌ Rojo = Error (ver logs)

## 🎯 PASO 4: Verificar el JSON Generado

Accede a:
```
https://hctop.github.io/almansa-eventos/eventos_agenda.json
```

Debería mostrar los eventos extraídos en formato JSON.

## 🎯 PASO 5: Integrar en Android

En tu proyecto Android:

```kotlin
// EventoDto.kt (ya creado en sesiones anteriores)
data class EventoDto(
    val id: String,
    val titulo: String,
    val descripcion: String,
    val fecha: String,
    val hora: String,
    val lugar: String,
    val categoria: String,
    val precio: String,
    val urlCompra: String,
    val esGratuito: Boolean,
    val fuente: String
)

// ApiEventos.kt
interface ApiEventos {
    @GET("eventos_agenda.json")
    suspend fun obtenerEventos(): Response<List<EventoDto>>
    
    companion object {
        const val BASE_URL = "https://hctop.github.io/almansa-eventos/"
    }
}
```

## 📊 RESUMEN DE MEJORAS v3.0

### ✅ 8 Fuentes Activas
1. **La Tinta - Programaciones Trimestrales** (15-20 eventos/trimestre)
2. **Almansa Cultura** - Eventos oficiales (5-10 eventos/trimestre)
3. **Ayuntamiento - RSS Actualidad** (2-5 eventos/mes)
4. **Ayuntamiento - RSS Cultura** (2-5 eventos/mes)
5. **TomaTicket - Teatro Regio** (eventos con entradas online)
6. **TomaTicket - Teatro Principal** (eventos con entradas online)
7. **DeAlmansa.com - Agenda** (agregador local)
8. **La Tinta RSS** - Backup (eventos en noticias)

### ✅ Deduplicación Inteligente
- Elimina eventos repetidos por título + fecha + lugar
- Genera ID único MD5 por evento
- Tasa típica: 15-25% duplicados eliminados

### ✅ Datos Enriquecidos
- Extracción automática de hora, lugar y precio
- Detección automática de categorías (8 categorías)
- Campo "fuente" para rastreabilidad
- Manejo inteligente de fechas en lenguaje natural

### ✅ Cobertura Completa
- Eventos culturales (teatro, música, exposiciones)
- Eventos deportivos (carreras, campeonatos)
- Fiestas y celebraciones locales
- Eventos infantiles y familiares

### ❌ Giglon Descartado
- Bloqueado por sistema anti-bot
- No viable sin servicios de pago ($$$)

## 🐛 Solución de Problemas

### Error: "No events found"
- Normal si no hay programaciones recientes publicadas
- Esperar a que publiquen nueva programación trimestral
- Revisar manualmente: https://latintadealmansa.com/cultura/

### Error: "HTTP 403"
- Revisa que las URLs sean correctas
- Puede ser un bloqueo temporal del servidor

### Error: "Parse error"
- La estructura HTML de la fuente cambió
- Revisar selectores CSS en el código

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en GitHub Actions
2. Comprueba que las URLs de las fuentes siguen funcionando
3. Abre un issue en el repositorio
