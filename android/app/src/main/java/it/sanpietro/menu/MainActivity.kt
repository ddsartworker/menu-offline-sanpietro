package it.sanpietro.menu

import android.annotation.SuppressLint
import android.os.Bundle
import android.os.SystemClock
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.animation.Animation
import android.view.animation.LinearInterpolator
import android.view.animation.RotateAnimation
import android.webkit.WebView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.lifecycleScope
import androidx.work.WorkInfo
import androidx.work.WorkManager
import it.sanpietro.menu.databinding.ActivityMainBinding
import kotlinx.coroutines.delay
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
    private var controlloInCorso = false
    private val nascondiAvviso = Runnable { binding.banner.visibility = View.GONE }

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

        binding.aggiorna.setOnClickListener { controllaAdesso() }

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

    /**
     * Il pulsante in sala: "guarda adesso se c'e' un menu nuovo".
     *
     * Il controllo automatico c'e' gia' - a ogni apertura e una volta all'ora -
     * ma quando il proprietario cambia un prezzo su Menumal e vuole vederlo sul
     * tablet subito, aspettare un'ora e' inaccettabile e non c'e' modo di sapere
     * se sta funzionando. Qui la risposta arriva in due secondi e dice sempre
     * *quanto e' vecchia la copia online*, non solo se il tablet e' allineato:
     * ad agosto 2026 il tablet era perfettamente allineato a un menu fermo da
     * sei giorni, e nessuno poteva accorgersene guardando lo schermo.
     */
    private fun controllaAdesso() {
        if (controlloInCorso) return
        controlloInCorso = true

        with(binding.aggiorna) {
            isEnabled = false
            alpha = 1f
            startAnimation(
                RotateAnimation(
                    0f, 360f,
                    Animation.RELATIVE_TO_SELF, 0.5f,
                    Animation.RELATIVE_TO_SELF, 0.5f,
                ).apply {
                    duration = 900
                    repeatCount = Animation.INFINITE
                    interpolator = LinearInterpolator()
                },
            )
        }
        avviso(getString(R.string.aggiorno), resta = true)

        lifecycleScope.launch {
            val inizio = SystemClock.elapsedRealtime()
            val esito = Updater.sync(this@MainActivity)

            // Con la fibra la risposta torna in 200 ms: un lampo cosi' non si
            // legge e sembra che il pulsante non abbia fatto niente.
            val trascorso = SystemClock.elapsedRealtime() - inizio
            if (trascorso < 700) delay(700 - trascorso)

            with(binding.aggiorna) {
                clearAnimation()
                alpha = 0.35f
                isEnabled = true
            }
            controlloInCorso = false

            when (esito) {
                is Updater.Result.Updated -> {
                    // L'ha chiesto una persona, adesso. Non si rimanda alla
                    // prossima apertura come fa il controllo di fondo: chi ha
                    // premuto vuole vedere il menu nuovo.
                    Updater.consumePendingReload(this@MainActivity)
                    showMenu()
                    avviso(getString(R.string.aggiornato_adesso))
                }

                is Updater.Result.UpToDate -> avviso(
                    Updater.etaPubblicazione(esito.pubblicato)
                        ?.let { getString(R.string.gia_aggiornato, it) }
                        ?: getString(R.string.gia_aggiornato_senza_data),
                )

                is Updater.Result.Failed -> avviso(
                    Updater.etaPubblicazione(Updater.lastUpdated(this@MainActivity))
                        ?.let { getString(R.string.senza_rete, it) }
                        ?: getString(R.string.senza_rete_senza_data),
                )
            }
        }
    }

    /** Il cartellino nero in basso: compare, dice una cosa sola, sparisce. */
    private fun avviso(testo: String, resta: Boolean = false) {
        binding.banner.removeCallbacks(nascondiAvviso)
        binding.banner.text = testo
        binding.banner.visibility = View.VISIBLE
        if (!resta) binding.banner.postDelayed(nascondiAvviso, 6_000)
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
                        avviso(getString(R.string.updated_banner))
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
