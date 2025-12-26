#!/usr/bin/env python3
"""
Extractor Multi-Fuente de Eventos - Almansa Informa v3.0
Con sistema de deduplicación inteligente
"""

import json
import re
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import sys
from typing import List, Dict, Set

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

OUTPUT_FILE = "eventos_agenda.json"

# URLs de las fuentes
LA_TINTA_RSS = "https://latintadealmansa.com/feed/"
LA_TINTA_PROGRAMACION = "https://latintadealmansa.com/cultura/"
ALMANSA_CULTURA_EVENTOS = "https://www.almansacultura.es/index.php/eventos"
AYUNTAMIENTO_RSS = "https://almansa.es/category/actualidad/feed/"
AYUNTAMIENTO_CULTURA = "https://almansa.es/category/cultura/feed/"
TOMATICKET_REGIO = "https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa"
TOMATICKET_PRINCIPAL = "https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa"
DEALMANSA_AGENDA = "https://dealmansa.com/agenda/"

# Headers comunes
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ============================================================================
# 1. EXTRACTOR LA TINTA - PROGRAMACIONES TRIMESTRALES
# ============================================================================

def extraer_la_tinta_programaciones():
    """
    Extrae eventos de las programaciones culturales trimestrales de La Tinta.
    Estas son artículos largos con 20-30 eventos por temporada.
    """
    print("🔍 Extrayendo programaciones de La Tinta...")
    eventos = []
    
    try:
        # Primero buscamos artículos con "programación" en el título
        response = requests.get(LA_TINTA_RSS, timeout=15, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"⚠️ Error HTTP {response.status_code}")
            return eventos
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        # Buscar artículos de programación
        urls_programacion = []
        for item in items[:20]:  # Últimos 20 artículos
            try:
                titulo = item.find('title').get_text(strip=True).lower()
                link = item.find('link').get_text(strip=True)
                
                # Detectar artículos de programación cultural
                if any(palabra in titulo for palabra in ['programación', 'programa', 'agenda cultural']):
                    urls_programacion.append(link)
                    print(f"  📄 Encontrada programación: {link}")
            except:
                continue
        
        # Extraer eventos de cada programación
        for url in urls_programacion[:3]:  # Máximo 3 programaciones recientes
            eventos_temp = extraer_eventos_de_articulo(url)
            eventos.extend(eventos_temp)
            print(f"  ✅ {len(eventos_temp)} eventos de: {url}")
        
    except Exception as e:
        print(f"❌ Error en La Tinta Programaciones: {e}")
    
    print(f"✅ La Tinta Programaciones: {len(eventos)} eventos\n")
    return eventos


def extraer_eventos_de_articulo(url: str) -> List[Dict]:
    """
    Extrae eventos individuales de un artículo de programación.
    
    Estructura típica:
    - Título del evento
    - "Fecha: 27 de septiembre, 19:30"
    - "Lugar: Teatro Regio"
    - "Precio: 10 euros"
    - Descripción
    """
    eventos = []
    
    try:
        response = requests.get(url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar el contenido del artículo
        contenido = (
            soup.find('div', class_=re.compile(r'entry-content|post-content|article-content', re.I)) or
            soup.find('article') or
            soup.find('main')
        )
        
        if not contenido:
            return eventos
        
        # Dividir por títulos (h2, h3, strong)
        bloques = []
        elementos = contenido.find_all(['h2', 'h3', 'h4', 'strong', 'p'])
        
        bloque_actual = {'titulo': '', 'texto': ''}
        
        for elem in elementos:
            texto = elem.get_text(strip=True)
            
            # Si es un posible título de evento
            if elem.name in ['h2', 'h3', 'h4'] or (elem.name == 'strong' and len(texto) > 10):
                # Guardar bloque anterior
                if bloque_actual['titulo'] and bloque_actual['texto']:
                    bloques.append(bloque_actual)
                
                # Nuevo bloque
                bloque_actual = {'titulo': texto, 'texto': ''}
            else:
                # Acumular texto
                bloque_actual['texto'] += ' ' + texto
        
        # Guardar último bloque
        if bloque_actual['titulo'] and bloque_actual['texto']:
            bloques.append(bloque_actual)
        
        # Procesar cada bloque como posible evento
        for bloque in bloques:
            evento = procesar_bloque_evento(bloque, url)
            if evento:
                eventos.append(evento)
        
    except Exception as e:
        print(f"  ⚠️ Error extrayendo de {url}: {e}")
    
    return eventos


def procesar_bloque_evento(bloque: Dict, url: str) -> Dict | None:
    """Convierte un bloque de texto en un evento estructurado"""
    
    titulo = bloque['titulo']
    texto = bloque['texto']
    
    # Validar que sea un evento real
    if len(titulo) < 5 or len(texto) < 20:
        return None
    
    # Extraer fecha
    fecha = extraer_fecha_de_texto(texto)
    if not fecha:
        return None
    
    # Solo eventos futuros
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        if fecha_obj < datetime.now() - timedelta(days=1):
            return None
    except:
        return None
    
    # Extraer hora
    hora = extraer_hora(texto)
    
    # Extraer lugar
    lugar = extraer_lugar(texto)
    
    # Extraer precio
    precio = extraer_precio(texto)
    
    # Categoría
    categoria = detectar_categoria(titulo + " " + texto)
    
    # Descripción limpia
    descripcion = limpiar_descripcion(texto)
    
    # Generar ID único
    evento_id = generar_id(titulo, fecha, lugar)
    
    return {
        "id": evento_id,
        "titulo": titulo.strip(),
        "descripcion": descripcion[:300],
        "fecha": fecha,
        "hora": hora,
        "lugar": lugar,
        "categoria": categoria,
        "precio": precio,
        "urlCompra": url,
        "esGratuito": 'gratis' in precio.lower() or 'gratuito' in precio.lower(),
        "fuente": "La Tinta de Almansa"
    }


# ============================================================================
# 2. EXTRACTOR ALMANSA CULTURA
# ============================================================================

def extraer_almansa_cultura():
    """
    Extrae eventos de AlmansaCultura.es
    Intentamos scraping directo aunque use JavaScript
    """
    print("🔍 Extrayendo eventos de Almansa Cultura...")
    eventos = []
    
    try:
        response = requests.get(ALMANSA_CULTURA_EVENTOS, timeout=15, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"⚠️ Error HTTP {response.status_code}")
            return eventos
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Intentar múltiples selectores para K2
        tarjetas = (
            soup.find_all('div', class_=re.compile(r'itemContainer|item-container|event', re.I)) or
            soup.find_all('article', class_=re.compile(r'event|item', re.I)) or
            soup.find_all('div', class_='k2-content')
        )
        
        print(f"  📋 Encontradas {len(tarjetas)} posibles tarjetas")
        
        for tarjeta in tarjetas[:50]:
            try:
                # Título
                titulo_elem = (
                    tarjeta.find('h2') or tarjeta.find('h3') or
                    tarjeta.find('a', class_=re.compile(r'title|itemTitle', re.I))
                )
                
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                if len(titulo) < 5:
                    continue
                
                # Enlace
                link_elem = titulo_elem if titulo_elem.name == 'a' else tarjeta.find('a')
                url = ''
                if link_elem and link_elem.get('href'):
                    url = link_elem['href']
                    if not url.startswith('http'):
                        url = 'https://almansacultura.es' + url
                
                # Fecha - buscar en múltiples lugares
                fecha_elem = (
                    tarjeta.find('time') or
                    tarjeta.find('span', class_=re.compile(r'date|fecha', re.I)) or
                    tarjeta.find('div', class_=re.compile(r'date|fecha', re.I))
                )
                
                fecha_texto = ''
                if fecha_elem:
                    fecha_texto = fecha_elem.get('datetime', '') or fecha_elem.get_text(strip=True)
                
                fecha = parsear_fecha(fecha_texto) or extraer_fecha_de_texto(fecha_texto)
                
                if not fecha:
                    continue
                
                # Solo futuros
                try:
                    if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now() - timedelta(days=1):
                        continue
                except:
                    continue
                
                # Descripción
                desc_elem = tarjeta.find('p') or tarjeta.find('div', class_=re.compile(r'intro|description', re.I))
                descripcion = desc_elem.get_text(strip=True) if desc_elem else titulo
                
                # Lugar (por defecto Teatro Regio)
                lugar = "Teatro Regio / Teatro Principal"
                
                # Hora
                hora = extraer_hora(fecha_texto)
                
                # Precio
                precio = "Consultar en taquilla"
                
                # Categoría
                categoria = detectar_categoria(titulo + " " + descripcion)
                
                evento_id = generar_id(titulo, fecha, lugar)
                
                evento = {
                    "id": evento_id,
                    "titulo": titulo,
                    "descripcion": limpiar_descripcion(descripcion)[:300],
                    "fecha": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "categoria": categoria,
                    "precio": precio,
                    "urlCompra": url or ALMANSA_CULTURA_EVENTOS,
                    "esGratuito": False,
                    "fuente": "Almansa Cultura"
                }
                
                eventos.append(evento)
                print(f"  ✅ {titulo} - {fecha}")
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Error en Almansa Cultura: {e}")
    
    print(f"✅ Almansa Cultura: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# 3. EXTRACTOR LA TINTA RSS (Backup)
# ============================================================================

def extraer_la_tinta_rss():
    """Extrae eventos del RSS de La Tinta como backup"""
    print("🔍 Extrayendo eventos de RSS La Tinta (backup)...")
    eventos = []
    
    try:
        response = requests.get(LA_TINTA_RSS, timeout=15, headers=HEADERS)
        
        if response.status_code != 200:
            return eventos
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        for item in items[:30]:
            try:
                titulo = item.find('title').get_text(strip=True)
                descripcion = item.find('description').get_text(strip=True)
                link = item.find('link').get_text(strip=True)
                
                # Solo noticias de cultura/eventos
                if not es_evento(titulo, descripcion):
                    continue
                
                # Extraer fecha del contenido
                fecha = extraer_fecha_de_texto(titulo + " " + descripcion)
                if not fecha:
                    continue
                
                # Solo futuros
                try:
                    if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now() - timedelta(days=1):
                        continue
                except:
                    continue
                
                categoria = detectar_categoria(titulo + " " + descripcion)
                lugar = "Por confirmar"
                
                evento_id = generar_id(titulo, fecha, lugar)
                
                evento = {
                    "id": evento_id,
                    "titulo": limpiar_titulo(titulo),
                    "descripcion": limpiar_html(descripcion)[:300],
                    "fecha": fecha,
                    "hora": "Por confirmar",
                    "lugar": lugar,
                    "categoria": categoria,
                    "precio": "Consultar",
                    "urlCompra": link,
                    "esGratuito": False,
                    "fuente": "La Tinta RSS"
                }
                
                eventos.append(evento)
                print(f"  ✅ {titulo} - {fecha}")
                
            except:
                continue
        
    except Exception as e:
        print(f"❌ Error en La Tinta RSS: {e}")
    
    print(f"✅ La Tinta RSS: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# 4. EXTRACTOR AYUNTAMIENTO ALMANSA (RSS)
# ============================================================================

def extraer_ayuntamiento_almansa():
    """
    Extrae eventos de los feeds RSS del Ayuntamiento de Almansa.
    Fuentes: Actualidad + Cultura
    """
    print("🔍 Extrayendo eventos del Ayuntamiento de Almansa...")
    eventos = []
    
    feeds = [
        (AYUNTAMIENTO_RSS, "Actualidad"),
        (AYUNTAMIENTO_CULTURA, "Cultura")
    ]
    
    for feed_url, feed_nombre in feeds:
        try:
            response = requests.get(feed_url, timeout=15, headers=HEADERS)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error HTTP {response.status_code} en {feed_nombre}")
                continue
            
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            print(f"  📋 {feed_nombre}: {len(items)} artículos encontrados")
            
            for item in items[:20]:
                try:
                    titulo = item.find('title').get_text(strip=True)
                    descripcion_elem = item.find('description')
                    descripcion = descripcion_elem.get_text(strip=True) if descripcion_elem else ""
                    link = item.find('link').get_text(strip=True)
                    
                    # Buscar contenido completo si existe
                    content_elem = item.find('content:encoded')
                    if content_elem:
                        descripcion = content_elem.get_text(strip=True)
                    
                    # Filtrar: solo si parece evento
                    if not es_evento(titulo, descripcion):
                        continue
                    
                    # Extraer fecha del contenido
                    fecha = extraer_fecha_de_texto(titulo + " " + descripcion)
                    if not fecha:
                        continue
                    
                    # Solo eventos futuros
                    try:
                        if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now() - timedelta(days=1):
                            continue
                    except:
                        continue
                    
                    # Extraer detalles
                    hora = extraer_hora(descripcion)
                    lugar = extraer_lugar(descripcion)
                    precio = extraer_precio(descripcion)
                    categoria = detectar_categoria(titulo + " " + descripcion)
                    
                    evento_id = generar_id(titulo, fecha, lugar)
                    
                    evento = {
                        "id": evento_id,
                        "titulo": limpiar_titulo(titulo),
                        "descripcion": limpiar_descripcion(descripcion)[:300],
                        "fecha": fecha,
                        "hora": hora,
                        "lugar": lugar,
                        "categoria": categoria,
                        "precio": precio,
                        "urlCompra": link,
                        "esGratuito": 'gratis' in precio.lower() or 'gratuito' in precio.lower(),
                        "fuente": f"Ayuntamiento - {feed_nombre}"
                    }
                    
                    eventos.append(evento)
                    print(f"  ✅ {titulo} - {fecha}")
                    
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"  ❌ Error en {feed_nombre}: {e}")
            continue
    
    print(f"✅ Ayuntamiento: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# 5. EXTRACTOR TOMATICKET
# ============================================================================

def extraer_tomaticket():
    """
    Extrae eventos de TomaTicket para Teatro Regio y Teatro Principal.
    Aunque tiene poco contenido, intentamos extraer lo que haya.
    """
    print("🔍 Extrayendo eventos de TomaTicket...")
    eventos = []
    
    urls = [
        (TOMATICKET_REGIO, "Teatro Regio"),
        (TOMATICKET_PRINCIPAL, "Teatro Principal")
    ]
    
    for url, lugar_nombre in urls:
        try:
            response = requests.get(url, timeout=15, headers=HEADERS)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error HTTP {response.status_code} en {lugar_nombre}")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar tarjetas de eventos
            tarjetas = (
                soup.find_all('div', class_=re.compile(r'event|evento|card', re.I)) or
                soup.find_all('article', class_=re.compile(r'event|evento', re.I)) or
                soup.find_all('a', href=re.compile(r'/event|/evento', re.I))
            )
            
            print(f"  📋 {lugar_nombre}: {len(tarjetas)} posibles eventos")
            
            for tarjeta in tarjetas[:20]:
                try:
                    # Título
                    titulo_elem = (
                        tarjeta.find('h1') or tarjeta.find('h2') or 
                        tarjeta.find('h3') or tarjeta.find('h4') or
                        tarjeta.find(class_=re.compile(r'title|titulo|name', re.I))
                    )
                    
                    if not titulo_elem:
                        continue
                    
                    titulo = titulo_elem.get_text(strip=True)
                    
                    if len(titulo) < 5 or 'cookie' in titulo.lower():
                        continue
                    
                    # Fecha
                    fecha_elem = (
                        tarjeta.find('time') or
                        tarjeta.find(class_=re.compile(r'date|fecha', re.I)) or
                        tarjeta.find('span', class_=re.compile(r'date|fecha', re.I))
                    )
                    
                    fecha_texto = ''
                    if fecha_elem:
                        fecha_texto = fecha_elem.get('datetime', '') or fecha_elem.get_text(strip=True)
                    
                    fecha = parsear_fecha(fecha_texto) or extraer_fecha_de_texto(fecha_texto)
                    
                    if not fecha:
                        continue
                    
                    # Solo futuros
                    try:
                        if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now() - timedelta(days=1):
                            continue
                    except:
                        continue
                    
                    # URL del evento
                    link_elem = tarjeta if tarjeta.name == 'a' else tarjeta.find('a', href=True)
                    url_evento = ''
                    if link_elem and link_elem.get('href'):
                        url_evento = link_elem['href']
                        if not url_evento.startswith('http'):
                            url_evento = 'https://www.tomaticket.es' + url_evento
                    
                    # Descripción
                    desc_elem = tarjeta.find('p') or tarjeta.find(class_=re.compile(r'desc|description', re.I))
                    descripcion = desc_elem.get_text(strip=True) if desc_elem else titulo
                    
                    # Detalles
                    hora = extraer_hora(fecha_texto + " " + descripcion)
                    precio = extraer_precio(descripcion)
                    categoria = detectar_categoria(titulo + " " + descripcion)
                    
                    evento_id = generar_id(titulo, fecha, lugar_nombre)
                    
                    evento = {
                        "id": evento_id,
                        "titulo": titulo,
                        "descripcion": limpiar_descripcion(descripcion)[:300],
                        "fecha": fecha,
                        "hora": hora,
                        "lugar": lugar_nombre,
                        "categoria": categoria,
                        "precio": precio,
                        "urlCompra": url_evento or url,
                        "esGratuito": 'gratis' in precio.lower(),
                        "fuente": "TomaTicket"
                    }
                    
                    eventos.append(evento)
                    print(f"  ✅ {titulo} - {fecha}")
                    
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"  ❌ Error en {lugar_nombre}: {e}")
            continue
    
    print(f"✅ TomaTicket: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# 6. EXTRACTOR DEALMANSA.COM
# ============================================================================

def extraer_dealmansa():
    """
    Extrae eventos de DeAlmansa.com/agenda
    Es un agregador pero puede tener eventos únicos
    """
    print("🔍 Extrayendo eventos de DeAlmansa.com...")
    eventos = []
    
    try:
        response = requests.get(DEALMANSA_AGENDA, timeout=15, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"  ⚠️ Error HTTP {response.status_code}")
            return eventos
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar eventos en la agenda
        tarjetas = (
            soup.find_all('div', class_=re.compile(r'event|evento|agenda-item', re.I)) or
            soup.find_all('article', class_=re.compile(r'event|evento', re.I)) or
            soup.find_all('li', class_=re.compile(r'event|evento', re.I))
        )
        
        print(f"  📋 Encontradas {len(tarjetas)} posibles tarjetas")
        
        for tarjeta in tarjetas[:50]:
            try:
                # Título
                titulo_elem = (
                    tarjeta.find('h2') or tarjeta.find('h3') or tarjeta.find('h4') or
                    tarjeta.find(class_=re.compile(r'title|titulo', re.I))
                )
                
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                if len(titulo) < 5:
                    continue
                
                # Fecha
                fecha_elem = (
                    tarjeta.find('time') or
                    tarjeta.find(class_=re.compile(r'date|fecha', re.I))
                )
                
                fecha_texto = ''
                if fecha_elem:
                    fecha_texto = fecha_elem.get('datetime', '') or fecha_elem.get_text(strip=True)
                
                fecha = parsear_fecha(fecha_texto) or extraer_fecha_de_texto(fecha_texto)
                
                if not fecha:
                    continue
                
                # Solo futuros
                try:
                    if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now() - timedelta(days=1):
                        continue
                except:
                    continue
                
                # URL
                link_elem = tarjeta.find('a', href=True)
                url = ''
                if link_elem:
                    url = link_elem['href']
                    if not url.startswith('http'):
                        url = 'https://dealmansa.com' + url
                
                # Descripción
                desc_elem = tarjeta.find('p') or tarjeta.find(class_=re.compile(r'desc|content', re.I))
                descripcion = desc_elem.get_text(strip=True) if desc_elem else titulo
                
                # Lugar
                lugar_elem = tarjeta.find(class_=re.compile(r'venue|lugar|location', re.I))
                lugar = lugar_elem.get_text(strip=True) if lugar_elem else extraer_lugar(descripcion)
                
                # Detalles
                hora = extraer_hora(fecha_texto + " " + descripcion)
                precio = extraer_precio(descripcion)
                categoria = detectar_categoria(titulo + " " + descripcion)
                
                evento_id = generar_id(titulo, fecha, lugar)
                
                evento = {
                    "id": evento_id,
                    "titulo": titulo,
                    "descripcion": limpiar_descripcion(descripcion)[:300],
                    "fecha": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "categoria": categoria,
                    "precio": precio,
                    "urlCompra": url or DEALMANSA_AGENDA,
                    "esGratuito": 'gratis' in precio.lower(),
                    "fuente": "DeAlmansa.com"
                }
                
                eventos.append(evento)
                print(f"  ✅ {titulo} - {fecha}")
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Error en DeAlmansa: {e}")
    
    print(f"✅ DeAlmansa: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def generar_id(titulo: str, fecha: str, lugar: str) -> str:
    """Genera ID único para un evento"""
    texto = f"{titulo}{fecha}{lugar}".lower()
    return f"evt_{hashlib.md5(texto.encode()).hexdigest()[:12]}"


def parsear_fecha(texto: str) -> str | None:
    """Convierte texto de fecha a formato YYYY-MM-DD"""
    if not texto:
        return None
    
    # Formato DD/MM/YYYY
    match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', texto)
    if match:
        dia, mes, anio = match.groups()
        return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
    
    # Formato YYYY-MM-DD
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
    if match:
        return match.group(0)
    
    return None


def extraer_fecha_de_texto(texto: str) -> str | None:
    """Extrae fecha de texto en lenguaje natural"""
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    texto_lower = texto.lower()
    
    # Patrón: "19 de diciembre" o "Sábado 27 de septiembre"
    for mes_nombre, mes_num in meses.items():
        patterns = [
            rf'(\d{1,2})\s+de\s+{mes_nombre}',
            rf'{mes_nombre}\s+(\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto_lower)
            if match:
                dia = match.group(1).zfill(2)
                anio = datetime.now().year
                
                # Construir fecha
                fecha = f"{anio}-{mes_num}-{dia}"
                
                # Si ya pasó, usar año siguiente
                try:
                    if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now() - timedelta(days=30):
                        anio += 1
                        fecha = f"{anio}-{mes_num}-{dia}"
                except:
                    pass
                
                return fecha
    
    return None


def extraer_hora(texto: str) -> str:
    """Extrae hora HH:MM del texto"""
    if not texto:
        return "Por confirmar"
    
    # Patrón HH:MM
    match = re.search(r'(\d{1,2}):(\d{2})\s*h?', texto.lower())
    if match:
        return f"{match.group(1).zfill(2)}:{match.group(2)}"
    
    # Patrón "a las 19:30"
    match = re.search(r'a las (\d{1,2}):(\d{2})', texto.lower())
    if match:
        return f"{match.group(1).zfill(2)}:{match.group(2)}"
    
    return "Por confirmar"


def extraer_lugar(texto: str) -> str:
    """Extrae lugar del evento"""
    texto_lower = texto.lower()
    
    lugares_conocidos = {
        'teatro regio': 'Teatro Regio',
        'teatro principal': 'Teatro Principal',
        'castillo': 'Castillo de Almansa',
        'auditorio': 'Auditorio de la Unión Musical',
        'recinto ferial': 'Recinto Ferial',
        'plaza': 'Plaza Mayor',
        'parque': 'Parque'
    }
    
    for clave, nombre in lugares_conocidos.items():
        if clave in texto_lower:
            return nombre
    
    return "Por confirmar"


def extraer_precio(texto: str) -> str:
    """Extrae precio del evento"""
    texto_lower = texto.lower()
    
    if 'gratis' in texto_lower or 'gratuito' in texto_lower or 'entrada libre' in texto_lower:
        return "Gratuito"
    
    # Buscar "X euros" o "X €"
    match = re.search(r'(\d+)\s*(?:euros?|€)', texto_lower)
    if match:
        return f"{match.group(1)} €"
    
    # Buscar "Precio: X"
    match = re.search(r'precio:\s*(\d+)', texto_lower)
    if match:
        return f"{match.group(1)} €"
    
    return "Consultar en taquilla"


def es_evento(titulo: str, descripcion: str) -> bool:
    """Determina si la noticia es sobre un evento"""
    keywords = [
        'programa', 'eventos', 'concierto', 'teatro', 'festival',
        'feria', 'fiestas', 'actuación', 'espectáculo', 'exposición',
        'taller', 'charla', 'jornada', 'encuentro', 'celebra'
    ]
    texto = (titulo + " " + descripcion).lower()
    return any(kw in texto for kw in keywords)


def detectar_categoria(texto: str) -> str:
    """Detecta categoría por palabras clave"""
    texto_lower = texto.lower()
    
    if any(kw in texto_lower for kw in ['concierto', 'música', 'coral', 'orquesta', 'banda']):
        return 'MUSICA'
    if any(kw in texto_lower for kw in ['teatro', 'obra', 'comedia', 'drama']):
        return 'TEATRO'
    if any(kw in texto_lower for kw in ['infantil', 'niños', 'niñas', 'familia', 'peque']):
        return 'INFANTIL'
    if any(kw in texto_lower for kw in ['deporte', 'carrera', 'atletismo', 'fútbol', 'media maratón']):
        return 'DEPORTE'
    if any(kw in texto_lower for kw in ['feria', 'fiesta', 'batalla', 'moros', 'procesión']):
        return 'FIESTA'
    if any(kw in texto_lower for kw in ['exposición', 'museo', 'arte', 'galería']):
        return 'EXPOSICION'
    if any(kw in texto_lower for kw in ['cine', 'película', 'documental']):
        return 'CINE'
    
    return 'CULTURA'


def limpiar_html(texto: str) -> str:
    """Elimina etiquetas HTML"""
    return re.sub(r'<[^>]+>', '', texto).strip()


def limpiar_descripcion(texto: str) -> str:
    """Limpia y acorta descripción"""
    texto = limpiar_html(texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def limpiar_titulo(titulo: str) -> str:
    """Limpia entidades HTML del título"""
    return (titulo
        .replace('&#8211;', '-')
        .replace('&#8230;', '...')
        .replace('&nbsp;', ' ')
        .replace('&amp;', '&')
        .strip())


# ============================================================================
# SISTEMA DE DEDUPLICACIÓN
# ============================================================================

def deduplicar_eventos(eventos: List[Dict]) -> List[Dict]:
    """
    Elimina eventos duplicados usando múltiples criterios:
    1. Mismo título + fecha + lugar = duplicado exacto
    2. Títulos muy similares + misma fecha = duplicado probable
    """
    print("🔄 Deduplicando eventos...")
    
    eventos_unicos = []
    firmas_vistas: Set[str] = set()
    
    for evento in eventos:
        # Generar firma única
        firma = f"{evento['titulo'].lower().strip()}|{evento['fecha']}|{evento['lugar'].lower()}"
        
        if firma not in firmas_vistas:
            eventos_unicos.append(evento)
            firmas_vistas.add(firma)
        else:
            print(f"  ⚠️ Duplicado eliminado: {evento['titulo']}")
    
    print(f"✅ Deduplicación: {len(eventos)} → {len(eventos_unicos)} eventos únicos\n")
    return eventos_unicos


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("EXTRACTOR MULTI-FUENTE v3.0 - ALMANSA INFORMA")
    print("=" * 70 + "\n")
    
    # Extraer de todas las fuentes
    print("📡 FASE 1: EXTRACCIÓN DE TODAS LAS FUENTES\n")
    
    eventos_programaciones = extraer_la_tinta_programaciones()
    eventos_almansa_cultura = extraer_almansa_cultura()
    eventos_ayuntamiento = extraer_ayuntamiento_almansa()
    eventos_tomaticket = extraer_tomaticket()
    eventos_dealmansa = extraer_dealmansa()
    eventos_rss_backup = extraer_la_tinta_rss()
    
    # Combinar todos
    todos_eventos = (
        eventos_programaciones + 
        eventos_almansa_cultura + 
        eventos_ayuntamiento +
        eventos_tomaticket +
        eventos_dealmansa +
        eventos_rss_backup
    )
    
    print(f"📊 Total extraído: {len(todos_eventos)} eventos\n")
    
    # Deduplicar
    print("📡 FASE 2: DEDUPLICACIÓN\n")
    eventos_unicos = deduplicar_eventos(todos_eventos)
    
    # Ordenar por fecha
    eventos_unicos.sort(key=lambda x: x['fecha'])
    
    # Guardar JSON
    print("📡 FASE 3: GUARDADO\n")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(eventos_unicos, f, ensure_ascii=False, indent=2)
    
    # Resumen final
    print("=" * 70)
    print(f"✅ COMPLETADO")
    print(f"📊 Eventos únicos: {len(eventos_unicos)}")
    print(f"📁 Archivo: {OUTPUT_FILE}")
    
    if eventos_unicos:
        print(f"📅 Rango: {eventos_unicos[0]['fecha']} → {eventos_unicos[-1]['fecha']}")
    else:
        print(f"📅 Rango: N/A")
    
    print("=" * 70)
    
    # Estadísticas por fuente
    print("\n📊 ESTADÍSTICAS POR FUENTE:")
    fuentes = {}
    for evento in eventos_unicos:
        fuente = evento.get('fuente', 'Desconocida')
        fuentes[fuente] = fuentes.get(fuente, 0) + 1
    
    for fuente, cantidad in sorted(fuentes.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {fuente}: {cantidad} eventos")
    
    # Estadísticas por categoría
    print("\n📊 ESTADÍSTICAS POR CATEGORÍA:")
    categorias = {}
    for evento in eventos_unicos:
        categoria = evento.get('categoria', 'Sin categoría')
        categorias[categoria] = categorias.get(categoria, 0) + 1
    
    for categoria, cantidad in sorted(categorias.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {categoria}: {cantidad} eventos")
    
    # Retornar código de salida
    sys.exit(0 if len(eventos_unicos) > 0 else 1)


if __name__ == "__main__":
    main()
