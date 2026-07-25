package it.sanpietro.menu

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/**
 * Controlla gli aggiornamenti quando c'e' rete.
 *
 * WorkManager sa aspettare da solo il ritorno della connessione e riprovare con
 * backoff: e' quello che serve in un locale dove il 4G va e viene.
 */
class SyncWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result = when (Updater.sync(applicationContext)) {
        is Updater.Result.Failed -> Result.retry()
        else -> Result.success()
    }

    companion object {
        private const val PERIODIC = "menu-sync-periodic"
        private const val NOW = "menu-sync-now"

        private val onlyWhenOnline = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        /** Controllo di fondo mentre il tablet resta acceso tutto il giorno. */
        fun schedulePeriodic(ctx: Context) {
            val request = PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
                .setConstraints(onlyWhenOnline)
                .setBackoffCriteria(androidx.work.BackoffPolicy.EXPONENTIAL, 5, TimeUnit.MINUTES)
                .build()

            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                PERIODIC,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }

        /** Controllo immediato: e' quello che scatta riaprendo l'app. */
        fun syncNow(ctx: Context) {
            val request = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(onlyWhenOnline)
                .setBackoffCriteria(androidx.work.BackoffPolicy.LINEAR, 30, TimeUnit.SECONDS)
                .build()

            WorkManager.getInstance(ctx).enqueueUniqueWork(
                NOW,
                ExistingWorkPolicy.REPLACE,
                request,
            )
        }
    }
}
