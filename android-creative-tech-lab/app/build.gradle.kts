plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.example.creativetechlab"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.example.creativetechlab"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    buildFeatures {
        compose = true
    }
    packaging {
        resources.excludes.add("META-INF/DEPENDENCIES")
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // 1. Image loading and caching
    implementation("io.coil-kt.coil3:coil-compose:3.6.3")
    implementation("io.coil-kt.coil3:coil-network-okhttp:3.6.3")

    // 2. JSON motion graphics
    implementation("com.airbnb.android:lottie-compose:6.7.1")

    // 3. 3D scene powered by Filament
    implementation("io.github.sceneview:sceneview:4.62.0")

    // 4. Interactive data visualizations
    implementation("com.patrykandpatrick.vico:compose:3.3.1")

    // 5. Audio waveform
    implementation("com.github.massoudss:waveformSeekBar:5.0.2")
}
