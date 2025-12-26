# 🎭 Extractor de Eventos - Almansa Informa

Sistema automatizado para extraer eventos culturales de múltiples fuentes en Almansa y publicarlos en un JSON accesible vía GitHub Pages.

## 📡 Fuentes de Datos

### ✅ Activas

1. **La Tinta de Almansa - Programaciones Trimestrales** ⭐ PRINCIPAL
   - URL: `https://latintadealmansa.com/cultura/`
   - Contenido: Programaciones culturales completas (20-30 eventos/trimestre)
   - Frecuencia: Trimestral
   - Categorías: Teatro, música, cine, circo, zarzuelas

2. **Almansa Cultura** ⭐ PRINCIPAL
   - URL: `https://almansacultura.es/index.php/inicio/eventos`
   - Contenido: Eventos oficiales de los teatros municipales
   - Frecuencia: Trimestral
   - Categorías: Teatro, conciertos, exposiciones

3. **Ayuntamiento de Almansa - RSS Actualidad**
   - URL: `https://almansa.es/category/actualidad/feed/`
   - Contenido: Anuncios oficiales de eventos
   - Frecuencia: Semanal/Mensual
   - Categorías: Eventos oficiales, cultura, deporte

4. **Ayuntamiento de Almansa - RSS Cultura**
   - URL: `https://almansa.es/category/cultura/feed/`
   - Contenido: Eventos culturales específicos
   - Frecuencia: Mensual
   - Categorías: Cultura, exposiciones

5. **TomaTicket - Teatro Regio**
   - URL: `https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa`
   - Contenido: Eventos con venta de entradas online
   - Frecuencia: Por evento
   - Categorías: Teatro, conciertos

6. **TomaTicket - Teatro Principal**
   - URL: `https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa`
   - Contenido: Eventos con venta de entradas online
   - Frecuencia: Por evento
   - Categorías: Teatro, cine, talleres

7. **DeAlmansa.com - Agenda**
   - URL: `https://dealmansa.com/agenda/`
   - Contenido: Agregador de eventos locales
   - Frecuencia: Continua
   - Categorías: General

8. **La Tinta RSS** (Backup)
   - URL: `https://latintadealmansa.com/feed/`
   - Contenido: Anuncios de eventos en noticias recientes
   - Frecuencia: Semanal
   - Categorías: Eventos anunciados en prensa

### ❌ Bloqueadas

- **Giglon**: Sistema anti-bot activo (403 Forbidden) - Requiere servicios de pago

## 🔄 Deduplicación

El sistema elimina eventos duplicados usando:
- Mismo título + fecha + lugar = Duplicado exacto
- Firma MD5 única por evento

## 🚀 Uso

### API Pública

```
https://hctop.github.io/almansa-eventos/eventos_agenda.json
```

### Estructura del JSON

```json
[
  {
    "id": "evt_abc123def456",
    "titulo": "Concierto de Santa Cecilia",
    "descripcion": "Actuación de la Coral Unión Musical...",
    "fecha": "2025-11-17",
    "hora": "19:00",
    "lugar": "Teatro Regio",
    "categoria": "MUSICA",
    "precio": "5 €",
    "urlCompra": "https://almansacultura.es/evento/...",
    "esGratuito": false,
    "fuente": "Almansa Cultura"
  }
]
```

### Categorías

- `MUSICA`: Conciertos, corales, bandas
- `TEATRO`: Obras, comedias, dramas
- `INFANTIL`: Eventos para niños y familias
- `DEPORTE`: Carreras, eventos deportivos
- `FIESTA`: Fiestas Mayores, Feria, Batalla de Almansa
- `EXPOSICION`: Arte, museos
- `CINE`: Proyecciones
- `CULTURA`: Otros eventos culturales

## ⚙️ Configuración Técnica

### Dependencias

```bash
pip install -r requirements.txt
```

### Ejecución Manual

```bash
cd scripts
python3 extractor_eventos_v3.py
```

### GitHub Actions

- **Frecuencia**: Cada domingo a las 12:00 UTC
- **Trigger manual**: Disponible desde la pestaña "Actions"

## 📊 Estadísticas Típicas

- **Fuentes activas**: 8 fuentes diferentes
- **Eventos extraídos**: 20-40 por ejecución
- **Rango temporal**: 1-6 meses hacia adelante
- **Tiempo de ejecución**: 30-60 segundos
- **Tasa de deduplicación**: ~15-25% (eventos repetidos entre fuentes)

## 🛠️ Desarrollo

### Añadir Nueva Fuente

1. Crear función `extraer_nueva_fuente()` en `extractor_eventos_v3.py`
2. Añadir llamada en `main()`
3. Actualizar este README

### Formato de Evento

Cada función de extracción debe retornar:

```python
{
    "id": generar_id(titulo, fecha, lugar),
    "titulo": str,
    "descripcion": str (max 300 caracteres),
    "fecha": "YYYY-MM-DD",
    "hora": "HH:MM" o "Por confirmar",
    "lugar": str,
    "categoria": str (ver categorías arriba),
    "precio": str,
    "urlCompra": str,
    "esGratuito": bool,
    "fuente": str
}
```

## 📜 Licencia

MIT License - Proyecto de código abierto

## 👤 Autor

Desarrollado para **Almansa Informa** - App Android de información local

---

**Última actualización**: Diciembre 2024  
**Repositorio**: https://github.com/HCTop/almansa-eventos
