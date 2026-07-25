package it.sanpietro.menu

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.webkit.WebView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.lifecycleScope
import androidx.work.WorkInfo
import androidx.work.WorkManager
import it.sanpietro.menu.databinding.ActivityMainBinding
import kotlinx.coroutines.launch

/**
 * Mostra sempre e solo la copia locale del menu.
 *
 * E' il punto chiave: la visualizzazione non dipende mai dalla rete, quindi non
 * esiste il caso "pagina bianca perche' non c'e' campo". La rete serve solo,
 * quando c'e', ad aggiornare il file in background.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var lastTouch = 0L

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Un menu al tavolo non deve spegnersi in mano al cliente.
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        goImmersive()

        with(binding.webView) {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.builtInZoomControls = true
            settings.displayZoomControls = false
            settings.textZoom = 100
            overScrollMode = View.OVER_SCROLL_NEVER
            setBackgroundColor(0xFF000000.toInt())
            // Lo snapshot e' autoconsistente: qualunque navigazione esterna
            // fallirebbe offline, meglio non uscire mai dal menu.
            webViewClient = LocalOnlyWebViewClient()
        }

        SyncWorker.schedulePeriodic(this)
        observeSync()
    }

    override fun onResume() {
        super.onResume()
        goImmersive()
        Updater.consumePendingReload(this)
        showMenu()
        // E' il comportamento che conta: riapri l'app e, se c'e' campo,
        // si porta a casa l'ultima versione del menu.
        SyncWorker.syncNow(this)
    }

    override fun dispatchTouchEvent(ev: MotionEvent): Boolean {
        lastTouch = System.currentTimeMillis()
        return super.dispatchTouchEvent(ev)
    }

    private fun showMenu() {
        if (Updater.hasMenu(this)) {
            binding.status.visibility = View.GONE
            binding.webView.visibility = View.VISIBLE
            binding.webView.loadUrl("file://${Updater.menuFile(this).absolutePath}")
        } else {
            binding.webView.visibility = View.GONE
            binding.status.visibility = View.VISIBLE
            binding.status.text = getString(R.string.first_sync)
        }
    }

    private fun observeSync() {
        WorkManager.getInstance(this)
            .getWorkInfosForUniqueWorkLiveData("menu-sync-now")
            .observe(this) { infos ->
                val done = infos?.any { it.state == WorkInfo.State.SUCCEEDED } ?: false
                if (!done) return@observe

                lifecycleScope.launch {
                    if (!Updater.consumePendingReload(this@MainActivity)) return@launch

                    val idle = System.currentTimeMillis() - lastTouch > 60_000
                    if (idle || !Updater.hasMenu(this@MainActivity)) {
                        // Nessuno sta leggendo: si applica subito, in silenzio.
                        showMenu()
                    } else {
                        // Qualcuno ha il tablet in mano: non gli cambiamo il menu
                        // sotto gli occhi, si applichera' alla prossima apertura.
                        binding.banner.visibility = View.VISIBLE
                        binding.banner.postDelayed(
                            { binding.banner.visibility = View.GONE },
                            6_000,
                        )
                    }
                }
            }
    }

    private fun goImmersive() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, binding.root).apply {
            hide(androidx.core.view.WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }

    private class LocalOnlyWebViewClient : android.webkit.WebViewClient() {
        override fun shouldOverrideUrlLoading(
            view: WebView,
            request: android.webkit.WebResourceRequest,
        ): Boolean = request.url.scheme != "file"
    }
}
