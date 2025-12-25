package com.puntoyaparte.almansainforma.datos.remoto.api

import com.puntoyaparte.almansainforma.dominio.modelo.Evento
import retrofit2.Response
import retrofit2.http.GET

/**
 * API para obtener eventos desde GitHub Pages.
 * 
 * El archivo JSON se actualiza automáticamente cada lunes mediante GitHub Actions.
 * 
 * URL del repositorio: https://github.com/TU-USUARIO/almansa-eventos
 * URL de la API: https://TU-USUARIO.github.io/almansa-eventos/eventos_agenda.json
 */
interface ApiEventos {

    /**
     * Descarga el JSON de eventos desde GitHub Pages.
     * 
     * Este archivo se actualiza automáticamente mediante:
     * - GitHub Actions (cada lunes 9:00 AM)
     * - Extracción desde Giglon + La Tinta de Almansa
     * 
     * @return Lista de eventos en formato JSON
     */
    @GET("eventos_agenda.json")
    suspend fun obtenerEventos(): Response<List<Evento>>

    companion object {
        /**
         * URL base de tu GitHub Pages.
         * 
         * IMPORTANTE: Reemplaza "TU-USUARIO" con tu usuario de GitHub.
         * 
         * Ejemplo:
         * - Usuario: hectorcorrales
         * - Repo: almansa-eventos
         * - URL: https://hectorcorrales.github.io/almansa-eventos/
         */
        const val BASE_URL = "https://TU-USUARIO.github.io/almansa-eventos/"
        
        /**
         * Tiempo de caché en milisegundos (1 día).
         * Los eventos se actualizan semanalmente, pero permitimos
         * actualización manual desde la app.
         */
        const val CACHE_TIME_MS = 24 * 60 * 60 * 1000L  // 1 día
    }
}
