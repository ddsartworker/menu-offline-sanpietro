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

    buildTypes {
        release {
            isMinifyEnabled = false
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
