# Creative Tech Lab · Android library research (2026)

A Ukrainian-language Jetpack Compose demo showcasing **five practical external libraries**.

## The five libraries

| Library | Use in this app | Gradle coordinate | Official install guide |
| --- | --- | --- | --- |
| Coil 3 | Network photo and crossfade/cache | io.coil-kt.coil3:coil-compose:3.6.3 + coil-network-okhttp:3.6.3 | https://github.com/coil-kt/coil/blob/main/README.md |
| Lottie | Animated, pausable JSON vector | com.airbnb.android:lottie-compose:6.7.1 | https://github.com/airbnb/lottie/blob/master/android-compose.md |
| SceneView | Real-time 3D sphere and orbit gestures | io.github.sceneview:sceneview:4.62.0 | https://github.com/sceneview/sceneview/blob/main/README.md |
| Vico | Animated interactive chart | com.patrykandpatrick.vico:compose:3.3.1 | https://github.com/patrykandpatrick/vico/blob/master/guide/getting-started.md |
| WaveformSeekBar | Seekable audio-style waveform | com.github.massoudss:waveformSeekBar:5.0.2 | https://github.com/massoudss/waveformSeekBar#how-to-add |

The choices are a curated educational selection, **not** a GitHub ranking or endorsement. Lottie, Coil, SceneView and Vico use Google Maven/Maven Central. WaveformSeekBar is provided through JitPack, declared in settings.gradle.kts. No Amplituda dependency is needed because the demo uses int-array samples instead of reading a music file.

## Running

1. Install recent Android Studio with Android SDK Platform 37, Build Tools 36 and a Java 21 JDK.
2. Open this **android-creative-tech-lab** directory as a Gradle project.
3. Use Gradle 9.6.0 (the wrapper distribution is pinned in gradle/wrapper/gradle-wrapper.properties; a wrapper binary is not included).
4. Sync dependencies and run the app on an Android 7.0+ device/emulator (recommended recent API).
5. Open tabs: Огляд (Coil + Lottie), 3D (SceneView), Аудіо (WaveformSeekBar), Дані (Vico).

You can also run with a preinstalled Gradle: gradle :app:assembleDebug

## How the dependencies are used

- Coil: AsyncImage with ImageRequest, HTTPS image source and crossfade.
- Lottie: rememberLottieComposition from local raw JSON; infinite animation with pause/play.
- SceneView: SceneView 3D viewport with procedural SphereNode; orbit gestures.
- WaveformSeekBar: AndroidView bridge from Compose, setSampleFrom(IntArray), progress, color styling.
- Vico: CartesianChartModelProducer + runTransaction + lineModel, CartesianChartHost.

## Screenshots and verification

The [screenshots](screenshots/) directory contains four **real Pixel emulator captures** created by a successful GitHub Actions workflow. No synthetic mockups are presented as emulator screenshots.

**Verification state (2026-11-06): VERIFIED ON CI.** GitHub Actions [run #42213957654](https://github.com/sunmeat/sunmeat/actions/runs/42213957654) successfully compiled the Android app, installed it, opened it in the Pixel emulator, captured four PNG screenshots and committed them to [screenshots/](screenshots/). This verifies build and screen capture in CI; it is not a substitute for manual interaction testing of every feature.

## AI-assisted research disclosure

Prepared using AI-assisted comparison of upstream GitHub documentation and release notes on 2026-11-06. Always inspect the real Gradle errors and emulator output instead of assuming code generation guarantees build success.

## Licence

Original demo code: MIT. External libraries retain their own upstream licenses. Remote Unsplash photograph is an optional visual example and is not vendored into this repository.
