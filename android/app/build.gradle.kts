plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "it.sanpietro.menu"
    compileSdk = 34

    defaultConfig {
        applicationId = "it.sanpietro.menu"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        // Cambiare qui se un giorno cambia l'hosting degli snapshot.
        buildConfigField(
            "String",
            "UPDATE_BASE_URL",
            "\"${project.findProperty("updateBaseUrl") ?: "https://REPLACE_ME/"}\""
        )
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    // Android rifiuta un aggiornamento firmato con una chiave diversa dalla
    // precedente. Il runner di GitHub e' usa e getta e si generava una chiave
    // di debug nuova a ogni compilazione: due APK di due giorni diversi non si
    // sovrascrivevano, e sul tablet usciva "App non installata". Adesso la
    // chiave e' sempre la stessa e arriva da un secret del repository.
    val chiave: String? = System.getenv("ANDROID_KEYSTORE_FILE")

    signingConfigs {
        create("stabile") {
            if (chiave != null) {
                storeFile = file(chiave)
                storeType = "PKCS12"
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                // In un PKCS12 la chiave non ha una password propria.
                keyPassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Senza chiave l'APK esce non firmato: si compila lo stesso per
            // provare, ma il passo di rinomina nel workflow non lo trova e la
            // compilazione fallisce invece di pubblicare un file inservibile.
            signingConfig = if (chiave != null) signingConfigs.getByName("stabile") else null
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
