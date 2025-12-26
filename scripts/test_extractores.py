#!/usr/bin/env python3
"""
Script de prueba para verificar cada fuente individualmente
"""

import sys
sys.path.append('.')

# Importar funciones del extractor
from extractor_eventos_v3 import (
    extraer_la_tinta_programaciones,
    extraer_almansa_cultura,
    extraer_ayuntamiento_almansa,
    extraer_tomaticket,
    extraer_dealmansa,
    extraer_la_tinta_rss,
    deduplicar_eventos
)

def probar_fuente(nombre, funcion):
    """Prueba una fuente individual y muestra resultados"""
    print("\n" + "="*70)
    print(f"PROBANDO: {nombre}")
    print("="*70)
    
    try:
        eventos = funcion()
        print(f"\n✅ RESULTADO: {len(eventos)} eventos extraídos")
        
        if eventos:
            print("\n📋 PRIMEROS 3 EVENTOS:")
            for i, evento in enumerate(eventos[:3], 1):
                print(f"\n{i}. {evento['titulo']}")
                print(f"   📅 {evento['fecha']} a las {evento['hora']}")
                print(f"   📍 {evento['lugar']}")
                print(f"   💰 {evento['precio']}")
                print(f"   🏷️ {evento['categoria']}")
        
        return eventos
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return []

def main():
    print("="*70)
    print("PRUEBA DE EXTRACTORES - ALMANSA INFORMA")
    print("="*70)
    
    todas_fuentes = [
        ("La Tinta - Programaciones", extraer_la_tinta_programaciones),
        ("Almansa Cultura", extraer_almansa_cultura),
        ("Ayuntamiento Almansa", extraer_ayuntamiento_almansa),
        ("TomaTicket", extraer_tomaticket),
        ("DeAlmansa.com", extraer_dealmansa),
        ("La Tinta RSS (Backup)", extraer_la_tinta_rss)
    ]
    
    todos_eventos = []
    
    for nombre, funcion in todas_fuentes:
        eventos = probar_fuente(nombre, funcion)
        todos_eventos.extend(eventos)
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"\n📊 Total extraído: {len(todos_eventos)} eventos")
    
    if todos_eventos:
        eventos_unicos = deduplicar_eventos(todos_eventos)
        print(f"📊 Eventos únicos: {len(eventos_unicos)}")
        print(f"🔄 Duplicados eliminados: {len(todos_eventos) - len(eventos_unicos)}")
        
        # Estadísticas por fuente
        print("\n📊 POR FUENTE:")
        fuentes = {}
        for evento in eventos_unicos:
            fuente = evento.get('fuente', 'Desconocida')
            fuentes[fuente] = fuentes.get(fuente, 0) + 1
        
        for fuente, cantidad in sorted(fuentes.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {fuente}: {cantidad}")
        
        # Estadísticas por categoría
        print("\n📊 POR CATEGORÍA:")
        categorias = {}
        for evento in eventos_unicos:
            cat = evento.get('categoria', 'Sin categoría')
            categorias[cat] = categorias.get(cat, 0) + 1
        
        for cat, cantidad in sorted(categorias.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {cat}: {cantidad}")

if __name__ == "__main__":
    main()
