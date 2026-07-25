package it.sanpietro.menu

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Tiene allineata la copia locale del menu con quella pubblicata.
 *
 * Il controllo costa ~200 byte (version.json): su 4G debole si puo' fare spesso
 * senza pesare. Lo snapshot vero (~2 MB) si scarica solo quando l'hash cambia,
 * cioe' quando il menu e' stato davvero modificato.
 */
object Updater {

    private const val PREFS = "menu_state"
    private const val KEY_SHA = "sha256"
    private const val KEY_UPDATED = "updated"
    private const val KEY_PENDING_RELOAD = "pending_reload"
    private const val KEY_LAST_CHECK = "last_check"

    sealed class Result {
        object UpToDate : Result()
        data class Updated(val sha: String) : Result()
        data class Failed(val reason: String) : Result()
    }

    fun menuFile(ctx: Context) = File(ctx.filesDir, "menu.html")

    fun hasMenu(ctx: Context) = menuFile(ctx).length() > 0

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun currentSha(ctx: Context): String? = prefs(ctx).getString(KEY_SHA, null)

    fun lastUpdated(ctx: Context): String? = prefs(ctx).getString(KEY_UPDATED, null)

    fun consumePendingReload(ctx: Context): Boolean {
        val p = prefs(ctx)
        val pending = p.getBoolean(KEY_PENDING_RELOAD, false)
        if (pending) p.edit().putBoolean(KEY_PENDING_RELOAD, false).apply()
        return pending
    }

    suspend fun sync(ctx: Context): Result = withContext(Dispatchers.IO) {
        try {
            val base = BuildConfig.UPDATE_BASE_URL.trimEnd('/')
            val meta = JSONObject(fetchText("$base/version.json"))
            val remoteSha = meta.getString("sha256")
            val expectedSize = meta.optLong("size", -1L)

            prefs(ctx).edit().putLong(KEY_LAST_CHECK, System.currentTimeMillis()).apply()

            // Anche se l'hash coincide, un file locale mancante va riscaricato:
            // puo' succedere dopo uno svuotamento dati o un aggiornamento interrotto.
            if (remoteSha == currentSha(ctx) && hasMenu(ctx)) {
                return@withContext Result.UpToDate
            }

            val tmp = File(ctx.filesDir, "menu.download")
            val actualSha = download("$base/menu.html", tmp)

            if (actualSha != remoteSha) {
                tmp.delete()
                return@withContext Result.Failed("hash non corrispondente")
            }
            if (expectedSize > 0 && tmp.length() != expectedSize) {
                tmp.delete()
                return@withContext Result.Failed("dimensione inattesa")
            }

            // Sostituzione atomica: il menu visibile non e' mai un file a meta'.
            val dest = menuFile(ctx)
            if (!tmp.renameTo(dest)) {
                tmp.copyTo(dest, overwrite = true)
                tmp.delete()
            }

            prefs(ctx).edit()
                .putString(KEY_SHA, remoteSha)
                .putString(KEY_UPDATED, meta.optString("updated", ""))
                .putBoolean(KEY_PENDING_RELOAD, true)
                .apply()

            Result.Updated(remoteSha)
        } catch (e: Exception) {
            Result.Failed(e.message ?: e.javaClass.simpleName)
        }
    }

    private fun open(url: String): HttpURLConnection =
        (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 30_000
            readTimeout = 60_000
            // Su 4G scadente una risposta dalla cache di un proxy trasparente
            // farebbe credere al tablet di essere aggiornato quando non lo e'.
            setRequestProperty("Cache-Control", "no-cache")
            instanceFollowRedirects = true
        }

    private fun fetchText(url: String): String {
        val conn = open(url)
        try {
            if (conn.responseCode != 200) error("HTTP ${conn.responseCode} su version.json")
            return conn.inputStream.bufferedReader().readText()
        } finally {
            conn.disconnect()
        }
    }

    /** Scarica su [dest] e restituisce lo sha256 di quanto scritto. */
    private fun download(url: String, dest: File): String {
        val conn = open(url)
        try {
            if (conn.responseCode != 200) error("HTTP ${conn.responseCode} su menu.html")
            val digest = MessageDigest.getInstance("SHA-256")
            conn.inputStream.use { input ->
                dest.outputStream().use { output ->
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buf)
                        if (n <= 0) break
                        digest.update(buf, 0, n)
                        output.write(buf, 0, n)
                    }
                }
            }
            return digest.digest().joinToString("") { "%02x".format(it) }
        } finally {
            conn.disconnect()
        }
    }
}
